"""Control queries for the research sources — run BEFORE recording any negative result.

`~/.claude/rules/systematic-debugging.md` Phase 0 mandates this and nothing implemented it:
"An empty result and a broken instrument are indistinguishable. Before recording ANY negative
-- 'no such paper', 'not published', 'no hits' -- run a control query that MUST return results."

The cost of not having it is documented, not hypothetical. In one session an HTTP 429 was read as
"no such book", an arXiv 301 as "no preprint", an unauthenticated GitHub code search as "no hits",
and a broken search endpoint as "phrase absent" — four capability conclusions drawn from four
broken instruments, none detectable from inside the result.

Each source below is probed with a query whose answer CANNOT legitimately be empty (a paper that
certainly exists, a repo that certainly exists). So:

    control returns results  -> the instrument works; a later empty result is a REAL negative
    control returns nothing  -> the instrument is broken; a later empty result is UNKNOWN

The distinction this exists to preserve is ABSENT vs UNKNOWN. Reporting UNKNOWN as ABSENT is how
a throttle becomes "this does not exist", and it is not recoverable downstream — nothing in the
empty response records that it was empty for the wrong reason.

HTTP status is mapped to a CAUSE rather than a boolean, because the causes have different
remedies and each has burned us at least once:
    429 -> throttled; retry later, do NOT conclude absence  (arxiv API, per memory)
    3xx -> redirect; the endpoint moved                     (arxiv abs pages)
    401/403 -> auth required; the query was never run      (GitHub code search)
    406 -> refused; the query was not answered              (arxiv API, 2026-09-25)
    404 / other 4xx -> request rejected; the query never ran
    5xx -> upstream broken

A redirect that urllib FOLLOWS is also a break: the body then describes some other page, so a
200 after a redirect is reported as REDIRECTED, not live.

A non-zero count is not enough either. Each control names the answer it must contain (the
paper id, the repo), and a 200 without it is WRONG ANSWER. An error object served as 200
(`{"error": ...}`) is a shape break, never "one result".

Transient refusals (406/429/502/503/504) get ONE retry after RETRY_DELAY seconds. The
2026-09-25 arxiv 406 was intermittent and client-independent: the same URL answered 406 and
then 200 to urllib seconds apart, curl never differed at the same moment, and the responder was
Google Frontend. A persistent refusal still reports DEAD, with `attempts` recorded, and every
HTTP error carries `evidence` (an allowlist of response headers + the first body bytes) so the
next one can be diagnosed instead of guessed at.

The transport is deliberately urllib: most arxiv consumers in this repo fetch with
urllib.request, and a control that probes with a different client certifies that client, not
the one the research code actually uses. For the same reason the default opener honours the
proxy environment; only the self-test bypasses it, since it talks to 127.0.0.1.

Usage:
    python scripts/ops/research_source_control.py            # all sources
    python scripts/ops/research_source_control.py --json     # machine-readable
    python scripts/ops/research_source_control.py --self-test
Exit code is 0 only when EVERY source is verified live, so this can gate a research run.
"""

from __future__ import annotations

import contextlib
import http.server
import json
import sys
import threading
import time
import urllib.error
import urllib.request


UA = {"User-Agent": "cohezion-research-control/1.0"}
TIMEOUT = 20
RETRY_STATUSES = frozenset({406, 429, 502, 503, 504})
RETRY_DELAY = 3.5  # arxiv asks for at most one request per 3 seconds
EVIDENCE_HEADERS = (
    "Server",
    "Content-Type",
    "Retry-After",
    "Location",
    "Via",
    "X-RateLimit-Limit",
    "X-RateLimit-Remaining",
    "X-RateLimit-Reset",
)


class WrongAnswerError(ValueError):
    """The control query answered, but without the result it is known to contain."""


def _cause(status: int) -> str:
    """Map an HTTP status to the reason a result would be empty. Never returns 'absent'."""
    if status == 429:
        return "THROTTLED — retry later; an empty result here means UNKNOWN, not absent"
    if 300 <= status < 400:
        return "REDIRECT — the endpoint moved; the query never ran"
    if status in (401, 403):
        return "AUTH REQUIRED — the query never ran; add credentials before concluding anything"
    if status == 406:
        return "REFUSED (406) — server rejected the request; the query was not answered, UNKNOWN"
    if status == 404:
        return "NOT FOUND — the endpoint moved or was removed; the query never ran"
    if 400 <= status < 500:
        return f"CLIENT ERROR {status} — request rejected; the query never ran, UNKNOWN"
    if status >= 500:
        return f"UPSTREAM ERROR {status} — the source is broken, not empty"
    return f"HTTP {status}"


def _evidence(err: urllib.error.HTTPError) -> dict:
    """What the server said when it refused. Allowlisted headers only: no cookies in reports."""
    try:
        body = err.read(300).decode("utf-8", "replace")
    except Exception as exc:  # best-effort: an unreadable body must not mask the status
        body = f"<unreadable: {type(exc).__name__}>"
    headers = {}
    if err.headers is not None:
        for name in EVIDENCE_HEADERS:
            if values := err.headers.get_all(name):
                headers[name] = ", ".join(values)
    return {"headers": headers, "body_head": body}


def _dead(name: str, cause: str, status: int | None, attempts: int, **extra) -> dict:
    return {
        "source": name,
        "live": False,
        "n": 0,
        "cause": cause,
        "status": status,
        "attempts": attempts,
        **extra,
    }


def probe(
    name: str,
    url: str,
    extract,
    *,
    headers: dict | None = None,
    opener: urllib.request.OpenerDirector | None = None,
    retry_delay: float = RETRY_DELAY,
) -> dict:
    """Run one control query. `extract(payload) -> int` returns the number of results found."""
    opener = opener or urllib.request.build_opener()
    req = urllib.request.Request(  # noqa: S310 (fixed https research endpoints)
        url, headers={**UA, **(headers or {})}
    )
    attempts = 0
    while True:
        attempts += 1
        try:
            resp = opener.open(req, timeout=TIMEOUT)
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUSES and attempts == 1:
                e.close()
                time.sleep(retry_delay)
                continue
            return _dead(name, _cause(e.code), e.code, attempts, evidence=_evidence(e))
        except Exception as exc:
            cause = f"UNREACHABLE ({type(exc).__name__}) — network or DNS, not absence"
            return _dead(name, cause, None, attempts)
        break

    with resp:
        status = resp.status
        final_url = resp.geturl()
        try:
            body = resp.read()
        except Exception as exc:
            cause = f"STALLED BODY after HTTP {status} ({type(exc).__name__}) — UNKNOWN"
            return _dead(name, cause, status, attempts)

    if final_url != url:
        cause = "REDIRECTED — the body describes a different page; the query never ran"
        return _dead(name, cause, status, attempts, redirected_to=final_url)
    try:
        n = extract(body)
    except WrongAnswerError as exc:
        cause = f"WRONG ANSWER ({exc}) — the control's known result is missing; treat as broken"
        return _dead(name, cause, status, attempts)
    except Exception as exc:
        # A 200 that cannot be parsed is a broken instrument, not an empty result. SurrealDB
        # taught this the expensive way: HTTP 200 carrying a statement error.
        cause = f"UNPARSEABLE 200 ({type(exc).__name__}: {exc}) — shape changed; treat as broken"
        return _dead(name, cause, status, attempts)
    if n <= 0:
        cause = "CONTROL RETURNED ZERO — instrument broken, negatives are UNKNOWN"
        return _dead(name, cause, status, attempts)
    return {
        "source": name,
        "live": True,
        "n": n,
        "status": status,
        "attempts": attempts,
        "cause": "OK",
    }


def _arxiv_entries(body: bytes) -> int:
    return body.decode("utf-8", "replace").count("<entry>")


def _json_list(key: str | None = None):
    """Count a JSON list: the whole body (key=None) or `body[key]`. Any other shape raises."""

    def f(body: bytes) -> int:
        d = json.loads(body)
        if key is not None:
            if not isinstance(d, dict):
                raise ValueError(f"expected an object with {key!r}, got {type(d).__name__}")
            d = d.get(key)
        if not isinstance(d, list):
            raise ValueError(f"expected a JSON list, got {type(d).__name__}")
        return len(d)

    return f


def _known(marker: str, extract):
    """Require the control's known answer to appear in the body before counting results."""

    def f(body: bytes) -> int:
        if marker not in body.decode("utf-8", "replace"):
            raise WrongAnswerError(f"{marker!r} not in response")
        return extract(body)

    return f


# Control queries chosen so that ZERO results is impossible if the source works: "attention is
# all you need" is arXiv 1706.03762, transformers is huggingface/transformers, and the HF
# endpoints are list endpoints that are only empty (or not lists) when broken.
SOURCES = [
    (
        "arxiv",
        "https://export.arxiv.org/api/query?search_query=all:%22attention+is+all+you+need%22&max_results=3",
        _known("1706.03762", _arxiv_entries),
        None,
    ),
    (
        "huggingface-models",
        "https://huggingface.co/api/models?limit=3",
        _json_list(),
        None,
    ),
    (
        "huggingface-daily-papers",
        "https://huggingface.co/api/daily_papers?limit=3",
        _json_list(),
        None,
    ),
    (
        "github-api",
        "https://api.github.com/search/repositories?q=transformers+org:huggingface&per_page=3",
        _known('"huggingface/transformers"', _json_list("items")),
        {"Accept": "application/vnd.github+json"},
    ),
]


@contextlib.contextmanager
def _local_source():
    """A throwaway HTTP source on 127.0.0.1 serving each failure shape the probe must catch."""
    flaky_calls = {"n": 0}

    class _Handler(http.server.BaseHTTPRequestHandler):
        server_version = "planted-refuser"
        sys_version = ""

        def do_GET(self) -> None:
            extra: dict[str, str] = {}
            if self.path == "/ok":
                code, body = 200, b"[1, 2, 3]"
            elif self.path == "/errdict":
                code, body = 200, b'{"error": "rate limited"}'
            elif self.path == "/redir":
                code, body, extra = 302, b"", {"Location": "/ok"}
            elif self.path == "/flaky":
                flaky_calls["n"] += 1
                code, body = (406, b"transient") if flaky_calls["n"] == 1 else (200, b"[1]")
            elif self.path == "/cookie":
                code, body = 403, b"forbidden"
                extra = {"Set-Cookie": "session=SECRET"}
            else:
                code, body = 406, b"Not Acceptable: planted refusal"
            self.send_response(code)
            for k, v in extra.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A002 (stdlib signature)
            return None

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{srv.server_address[1]}"
    finally:
        srv.shutdown()
        srv.server_close()


# The self-test talks to 127.0.0.1; an http_proxy in the environment must not reroute it.
LOCAL_OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def self_test() -> int:
    """Prove the control can REPORT A BREAK. Without this it is unvalidated.

    A control whose every observed run says OK has never demonstrated it can say anything else,
    and "it always passes" is indistinguishable from "it cannot fail". Each case below plants a
    specific failure and requires the matching CAUSE — a bare "not live" check passes for the
    wrong reason when everything is dead (e.g. a proxy swallowing all traffic), so every case
    asserts the reason, not just the verdict.
    """
    checks: list[tuple[str, bool, str]] = []

    for status, want in (
        (429, "THROTTLED"),
        (403, "AUTH"),
        (301, "REDIRECT"),
        (503, "UPSTREAM"),
        (406, "REFUSED"),
        (404, "NOT FOUND"),
        (418, "CLIENT ERROR"),
    ):
        got = _cause(status)
        checks.append((f"status {status} -> {want}", want in got, got))

    def dead_with(label: str, r: dict, want: str) -> None:
        checks.append((label, not r["live"] and want in r["cause"], r["cause"]))

    # Nothing listens on port 1; deterministic and needs no external network.
    r = probe("unreachable", "http://127.0.0.1:1/", _json_list(), opener=LOCAL_OPENER)
    dead_with("unreachable host -> UNREACHABLE", r, "UNREACHABLE")

    def probe_local(path: str, extract) -> dict:
        return probe(path, f"{base}{path}", extract, opener=LOCAL_OPENER, retry_delay=0)

    # A local server stands in for a live source, so the self-test fails only when the PROBE is
    # wrong, never because an external site is down or the sandbox has no network.
    with _local_source() as base:
        r = probe_local("/ok", _json_list())
        checks.append(("healthy source -> live", r["live"] and r["n"] == 3, r["cause"]))

        def _raises(body: bytes) -> int:
            raise ValueError(f"planted shape change ({len(body)} bytes)")

        dead_with("200 unparseable -> UNPARSEABLE", probe_local("/ok", _raises), "UNPARSEABLE")
        r = probe_local("/ok", lambda body: 0 * len(body))
        dead_with("200 with 0 results -> UNKNOWN", r, "UNKNOWN")
        r = probe_local("/errdict", _json_list())
        dead_with("200 error object -> UNPARSEABLE", r, "UNPARSEABLE")
        r = probe_local("/ok", _known("1706.03762", _json_list()))
        dead_with("known answer missing -> WRONG ANSWER", r, "WRONG ANSWER")
        r = probe_local("/redir", _json_list())
        dead_with("followed redirect -> REDIRECTED", r, "REDIRECTED")

        r = probe_local("/refuse", _json_list())
        dead_with("persistent 406 -> REFUSED", r, "REFUSED")
        checks.append(("persistent 406 retried once", r["attempts"] == 2, str(r["attempts"])))
        ev = r.get("evidence") or {"headers": {}, "body_head": ""}
        server = ev["headers"].get("Server", "")
        checks.append(("406 evidence keeps headers", "planted-refuser" in server, server))
        checks.append(("406 evidence keeps body", "planted" in ev["body_head"], ev["body_head"]))

        r = probe_local("/flaky", _json_list())
        checks.append(
            ("transient 406 then 200 -> live", r["live"] and r["attempts"] == 2, r["cause"])
        )

        r = probe_local("/cookie", _json_list())
        leaked = "SECRET" in json.dumps(r)
        checks.append(("evidence drops Set-Cookie", not leaked, str(r.get("evidence"))))

    print("=== self-test: can this control detect a broken instrument? ===")
    bad = 0
    for label, ok, detail in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<44} {detail[:60]}")
        bad += 0 if ok else 1
    print(f"\n  {len(checks) - bad}/{len(checks)} passed")
    if bad:
        print("  The control cannot reliably report a break — do NOT trust its OK verdicts.")
    return 0 if bad == 0 else 1


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()
    as_json = "--json" in sys.argv
    results = [probe(n, u, e, headers=h) for n, u, e, h in SOURCES]
    if as_json:
        print(json.dumps(results, indent=2))
    else:
        print("=== research source control (a negative is only trustworthy if these are live) ===")
        for r in results:
            mark = "OK  " if r["live"] else "DEAD"
            tries = f" (after {r['attempts']} attempts)" if r["attempts"] > 1 else ""
            print(f"  [{mark}] {r['source']:<26} n={r['n']:<4} {r['cause']}{tries}")
            if ev := r.get("evidence"):
                server = ev["headers"].get("Server", "?")
                print(f"         server={server} body={ev['body_head'][:120]!r}")
            if where := r.get("redirected_to"):
                print(f"         redirected_to={where}")
        dead = [r["source"] for r in results if not r["live"]]
        if dead:
            print(f"\n  {len(dead)} source(s) NOT verified: {', '.join(dead)}")
            print("  Any empty result from these is UNKNOWN, not ABSENT. Do not record absence.")
        else:
            print("\n  All sources verified live — an empty result from them is a real negative.")
    return 0 if all(r["live"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
