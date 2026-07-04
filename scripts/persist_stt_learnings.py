"""Persist the stt_tier validation learnings record to SurrealDB vault.learnings.

Tested against SurrealDB v3.0.0:
  - POST /signin -> {"code": 200, "details": "...", "token": "..."}
    (token is wrapped, not at top level as v2.x docs say)
  - POST /sql with raw SQL body, headers surreal-ns, surreal-db, Authorization
"""
import json
import time
import urllib.error
import urllib.request as ur


def signin():
    body = json.dumps({"user": "root", "pass": "root"}).encode()
    req = ur.Request(
        "http://localhost:8001/signin",
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with ur.urlopen(req, timeout=10) as r:
        payload = json.loads(r.read())
        return payload["token"]


def sql_query(token: str, query: str):
    req = ur.Request(
        "http://localhost:8001/sql",
        data=query.encode("utf-8"),
        headers={
            "Content-Type": "text/plain",
            "surreal-ns": "cohezion",
            "surreal-db": "vault",
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with ur.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def main():
    token = signin()
    print(f"token len: {len(token)}")

    rec = {
        "id": "stt_tier_validation_2026_06_10",
        "date": "2026-06-10",
        "title": "STT tier shipped: DirectLemonadeSTTTier (Whisper-Large-v3-Turbo on :13305)",
        "category": "multimodal",
        "tags": ["stt", "whisper", "lemonade", "omnirouter", "tier", "local-first", "voice-loop"],
        "summary": (
            "Mirrors tts_tier.py / image_tier.py. Hits :13305/v1/audio/transcriptions "
            "with multipart/form-data (OpenAI-spec). 19/19 pytest (10 logic + 4 mocked + 5 live). "
            "Live TTS->STT round-trip: 125KB MP3 transcribed verbatim in 461ms (verbose_json) on iGPU. "
            "Closes the local voice loop: kokoro outbound, whisper inbound."
        ),
        "measurements": {
            "src_lines": 323,
            "test_lines": 358,
            "pytest_pass": 19,
            "pytest_fail": 0,
            "pytest_seconds": 3.65,
            "live_tts_to_stt_seconds": 0.461,
            "live_silence_seconds": 0.030,
            "live_verbose_segments": 2,
            "live_audio_bytes": 125476,
            "live_duration_seconds": 6.26,
            "endpoint": "http://localhost:13305/v1/audio/transcriptions",
            "model": "Whisper-Large-v3-Turbo",
            "recipe": "whispercpp",
            "device": "gpu",
            "consumer_count_before": 47,
            "consumer_count_after": 48,
        },
        "endpoints": {
            "transcriptions": ":13305/v1/audio/transcriptions",
        },
        "design_rules": [
            "Only port 13305 for chat/image/stt. Only 8008 for TTS.",
            "No per-lane ports in new code. No cloud fallback paths.",
        ],
        "next_moves_unblocked": [
            "Wire stt_tier into Telegram bot _handle_voice: voice notes get transcribed locally before chat",
            "Wire tts_tier into _handle_chat: text replies can optionally become voice notes",
            "Close the self_retrospective loop (compose tts+stt for end-of-session narration)",
        ],
        "created_at": int(time.time() * 1000),
    }

    # Use CREATE with explicit record id
    doc_json = json.dumps(rec, ensure_ascii=False)
    # SurrealDB SQL: INSERT INTO learnings { ... } is easier than parameter binding
    # Build a CREATE statement with full record inline. Escape single quotes.
    rec_inline = doc_json.replace("'", "\\'")
    query = f"CREATE learnings:stt_tier_validation_2026_06_10 CONTENT {rec_inline};"

    status, body = sql_query(token, query)
    print(f"status: {status}")
    print(f"body[:500]: {body[:500]!r}")


if __name__ == "__main__":
    main()
