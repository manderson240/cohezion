#!/usr/bin/env python3
"""
Vault Sync — Event-driven SurrealDB sync for the Cohezion vault.

Watches vault files via Linux inotify and incrementally syncs changes to SurrealDB.
Handles create, update, delete, and move events in real-time (<1s latency).

Usage:
    python3 scripts/vault_sync.py --watch          # Event-driven daemon (inotify)
    python3 scripts/vault_sync.py --full-import    # Full resync (like triune-import)
    python3 scripts/vault_sync.py sync <file>      # Sync a single file
    python3 scripts/vault_sync.py delete <file>    # Remove a deleted file's neuron
    python3 scripts/vault_sync.py move <old> <new> # Handle a rename/move
"""

import base64
import ctypes
import ctypes.util
import hashlib
import json
import os
import re
import signal
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── Configuration ───────────────────────────────────────────────────────────

VAULT_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = VAULT_ROOT / ".vault-journal" / "checkpoint.json"
SURREAL_PORT = int(os.environ.get("SURREAL_PORT", "8001"))

SURREAL_NS = "cohezion"
SURREAL_DB = "vault"
SURREAL_USER = "root"
SURREAL_PASS = "root"

# Content directories to watch and sync
CONTENT_DIRS = [
    "cortex", "sensory", "memory", "genome", "research",
    "prefrontal", "laboratory", "cerebellum", "benchmarks",
    "motor", "hippocampus", "thalamus", "missions", "retrospectives", "Agents",
    "dreaming", "songlines", "subconscious", "metabolism", "visual-cortex",
    "docs", "teleport", "assessments", "meta",
]

# Directories to never sync
SKIP_DIRS = {
    ".git", ".obsidian", ".claude", ".worktrees", ".entire", ".locks",
    ".pytest_cache", ".ruff_cache", ".github", ".vault-journal",
    "node_modules", "htmlcov", "logs", "telemetry", "tools",
    "obsidian-plugin", "mcp-server", "src", "tests", "scripts",
    "attachments", "templates", "skills_index", "checkpoints",
    "archived", "learnings", "data", "skills",
}

DIR_TO_ASPECT = {
    # Knower
    "cortex": "knower", "sensory": "knower", "memory": "knower",
    "genome": "knower", "research": "knower",
    # Thinker
    "prefrontal": "thinker", "laboratory": "thinker",
    "cerebellum": "thinker", "benchmarks": "thinker",
    # Doer
    "motor": "doer", "hippocampus": "doer", "thalamus": "doer",
    "missions": "doer", "retrospectives": "doer", "Agents": "doer",
    # Connective
    "dreaming": "connective", "songlines": "connective",
    "subconscious": "connective", "metabolism": "connective",
    "visual-cortex": "connective", "docs": "connective",
    "meta": "connective", "assessments": "connective",
    "teleport": "connective",
}

WIKI_LINK_RE = re.compile(r"\[\[([^\]|#]+?)(?:[|#][^\]]*?)?\]\]")

# inotify event masks
IN_CLOSE_WRITE = 0x00000008
IN_MOVED_FROM = 0x00000040
IN_MOVED_TO = 0x00000080
IN_DELETE = 0x00000200
IN_CREATE = 0x00000100
IN_ISDIR = 0x40000000

# Debounce: ignore duplicate events within this window (seconds)
DEBOUNCE_SECS = 0.5

alive = True


def stop_handler(signum, frame):
    global alive
    alive = False
    print("\nStopping vault-sync...", file=sys.stderr)


signal.signal(signal.SIGINT, stop_handler)
signal.signal(signal.SIGTERM, stop_handler)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter as dict. Lightweight — no yaml dependency."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    result = {}
    for line in text[3:end].split("\n"):
        if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
            key, _, val = line.partition(":")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if val.startswith("[") and val.endswith("]"):
                val = [x.strip().strip('"').strip("'")
                       for x in val[1:-1].split(",") if x.strip()]
            result[key] = val
    return result


def compute_activation(word_count: int, synapse_count: int,
                       days_since_modified: int) -> float:
    content_score = min(word_count / 2000.0, 1.0) * 0.4
    link_score = min(synapse_count / 20.0, 1.0) * 0.3
    recency = max(0.0, 1.0 - (days_since_modified / 60.0)) * 0.3
    return round(min(content_score + link_score + recency, 1.0), 3)


def compute_stage(synapse_count: int, word_count: int, activation: float,
                  days_since_modified: int) -> str:
    if synapse_count < 3 and word_count < 500:
        return "embryo"
    if activation < 0.2 and days_since_modified > 30:
        return "resting"
    if synapse_count >= 10 and word_count >= 500:
        return "mature"
    return "growing"


def sanitize_id(path: str) -> str:
    return (
        path.replace("/", "_").replace(".", "_").replace(" ", "_")
        .replace("-", "_").replace("(", "").replace(")", "")
        .replace("'", "").replace('"', "").lower()
    )


def is_content_file(rel_path: str) -> bool:
    if not rel_path.endswith(".md"):
        return False
    parts = rel_path.split("/")
    return parts[0] not in SKIP_DIRS and not parts[-1].startswith("_")


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


# ─── SurrealDB Client ───────────────────────────────────────────────────────

import urllib.request


class SurrealClient:
    def __init__(self, port: int = 8001):
        self.url = f"http://localhost:{port}/sql"
        self.auth = "Basic " + base64.b64encode(
            f"{SURREAL_USER}:{SURREAL_PASS}".encode()
        ).decode()
        self._filename_index: dict[str, str] | None = None

    def query(self, sql: str) -> list[dict]:
        headers = {
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "surreal-ns": SURREAL_NS,
            "surreal-db": SURREAL_DB,
            "Authorization": self.auth,
        }
        req = urllib.request.Request(
            self.url, data=sql.encode("utf-8"),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            return [{"status": "ERR", "result": str(e)}]

    def query_result(self, sql: str, idx: int = 0) -> list:
        data = self.query(sql)
        if not data or idx >= len(data):
            return []
        entry = data[idx]
        return entry.get("result", []) if entry.get("status") == "OK" else []

    def get_neuron_id_by_path(self, path: str) -> str | None:
        """Look up existing neuron ID by path field."""
        rows = self.query_result(
            f"SELECT id FROM neuron WHERE path = {json.dumps(path, ensure_ascii=False)} LIMIT 1;"
        )
        if rows:
            return str(rows[0]["id"])
        return None

    def build_filename_index(self) -> dict[str, str]:
        """Build filename→neuron_id lookup. Cached until invalidated."""
        if self._filename_index is not None:
            return self._filename_index
        rows = self.query_result("SELECT id, path FROM neuron;")
        index: dict[str, str] = {}
        for row in rows:
            nid = str(row["id"])
            path = row["path"]
            fname = Path(path).stem.lower()
            index[fname] = nid
            index[fname + ".md"] = nid
        self._filename_index = index
        return index

    def invalidate_cache(self):
        self._filename_index = None


# ─── Incremental Sync ───────────────────────────────────────────────────────

def sync_file(db: SurrealClient, abs_path: str, checkpoint: dict | None = None,
              quiet: bool = False) -> bool:
    """Sync a single vault file to SurrealDB."""
    fpath = Path(abs_path).resolve()
    try:
        rel_path = str(fpath.relative_to(VAULT_ROOT))
    except ValueError:
        return False

    if not is_content_file(rel_path):
        return False

    if not fpath.is_file():
        return False

    try:
        text = fpath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    # Content hash check — skip if unchanged
    chash = content_hash(text)
    if checkpoint is not None:
        ckpt_entry = checkpoint.get(rel_path)
        if isinstance(ckpt_entry, dict) and ckpt_entry.get("hash") == chash:
            return True  # Already synced

    fm = parse_frontmatter(text)
    links = list(set(WIKI_LINK_RE.findall(text)))
    word_count = len(text.split())

    stat = fpath.stat()
    modified_ts = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    days_since = (datetime.now(timezone.utc) - modified_ts).days

    directory = rel_path.split("/")[0] if "/" in rel_path else ""
    aspect = DIR_TO_ASPECT.get(directory, "connective")
    activation = compute_activation(word_count, len(links), days_since)
    stage = compute_stage(len(links), word_count, activation, days_since)

    title = fm.get("title", fpath.stem.replace("-", " ").title())
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    tags_sql = ", ".join(json.dumps(t, ensure_ascii=False) for t in tags)

    # Resolve neuron ID — reuse existing if path is known
    existing_nid = db.get_neuron_id_by_path(rel_path)
    if existing_nid:
        nid = existing_nid
    else:
        nid = f"neuron:`{sanitize_id(rel_path)}`"

    # Check if existing neuron has an older activation we should boost
    if existing_nid:
        old = db.query_result(f"SELECT activation FROM {nid} LIMIT 1;")
        if old:
            old_act = old[0].get("activation", 0)
            # Bump activation on edit: at least +0.05, capped at 1.0
            activation = min(1.0, max(activation, old_act + 0.05))

    # 1. Upsert neuron
    sql = (
        f"UPSERT {nid} SET "
        f"path = {json.dumps(rel_path, ensure_ascii=False)}, "
        f"title = {json.dumps(str(title), ensure_ascii=False)}, "
        f'aspect = "{aspect}", '
        f"activation = {activation:.3f}, "
        f'stage = "{stage}", '
        f"last_fired = time::now(), "
        f"cluster_id = {json.dumps(directory, ensure_ascii=False)}, "
        f"synapse_out = {len(links)}, "
        f"word_count = {word_count}, "
        f"tags = [{tags_sql}], "
        f'content_hash = "{chash}", '
        f"directory = {json.dumps(directory, ensure_ascii=False)}, "
        f"modified = time::now();"
    )
    r = db.query(sql)
    if not r or r[0].get("status") != "OK":
        err = r[0].get("result", "?") if r else "no response"
        if not quiet:
            print(f"  FAIL upsert {rel_path}: {str(err)[:120]}", file=sys.stderr)
        return False

    # 2. Replace outbound synapses
    db.query(f"DELETE synapse WHERE in = {nid};")
    filename_index = db.build_filename_index()
    synapse_ok = 0
    for link_target in links:
        target_key = link_target.strip().lower()
        target_nid = filename_index.get(target_key) or filename_index.get(target_key + ".md")
        if target_nid and target_nid != nid:
            sr = db.query(
                f"RELATE {nid}->synapse->{target_nid} SET "
                f"weight = 1.0, link_type = 'explicit', created = time::now();"
            )
            if sr and sr[0].get("status") == "OK":
                synapse_ok += 1

    # 3. Update inbound count
    ib = db.query_result(f"SELECT count() FROM synapse WHERE out = {nid} GROUP ALL;")
    ic = ib[0]["count"] if ib else 0
    db.query(f"UPDATE {nid} SET synapse_in = {ic};")

    # 4. Akashic history entry
    db.query(
        f"CREATE neuron_history CONTENT {{ "
        f"neuron: {nid}, event_type: 'edited', timestamp: time::now(), "
        f"detail: {json.dumps(f'sync {synapse_ok} links {word_count}w', ensure_ascii=False)} }};"
    )

    # Update checkpoint
    if checkpoint is not None:
        checkpoint[rel_path] = {"hash": chash, "mtime": stat.st_mtime}

    if not existing_nid:
        db.invalidate_cache()

    if not quiet:
        action = "updated" if existing_nid else "created"
        print(f"  {action}: {rel_path} "
              f"(links:{synapse_ok}/{len(links)} stage:{stage} act:{activation:.3f})",
              file=sys.stderr)

    return True


def delete_file(db: SurrealClient, abs_path: str, checkpoint: dict | None = None,
                quiet: bool = False) -> bool:
    """Remove a neuron when its vault file is deleted."""
    fpath = Path(abs_path).resolve()
    try:
        rel_path = str(fpath.relative_to(VAULT_ROOT))
    except ValueError:
        return False

    nid = db.get_neuron_id_by_path(rel_path)
    if not nid:
        if not quiet:
            print(f"  SKIP delete: no neuron for {rel_path}", file=sys.stderr)
        return False

    db.query(f"DELETE synapse WHERE in = {nid} OR out = {nid};")
    db.query(
        f"CREATE neuron_history CONTENT {{ "
        f"neuron: '{nid}', event_type: 'deleted', timestamp: time::now(), "
        f"detail: {json.dumps(f'file removed: {rel_path}', ensure_ascii=False)} }};"
    )
    db.query(f"DELETE {nid};")
    db.invalidate_cache()

    if checkpoint is not None:
        checkpoint.pop(rel_path, None)

    if not quiet:
        print(f"  deleted: {rel_path}", file=sys.stderr)

    return True


def move_file(db: SurrealClient, old_abs: str, new_abs: str,
              checkpoint: dict | None = None, quiet: bool = False) -> bool:
    """Handle a file rename/move."""
    old_path = Path(old_abs).resolve()
    new_path = Path(new_abs).resolve()

    try:
        old_rel = str(old_path.relative_to(VAULT_ROOT))
    except ValueError:
        return False

    nid = db.get_neuron_id_by_path(old_rel)
    if not nid:
        # Not in DB — just sync the new file
        return sync_file(db, str(new_path), checkpoint=checkpoint, quiet=quiet)

    try:
        new_rel = str(new_path.relative_to(VAULT_ROOT))
    except ValueError:
        return False

    new_dir = new_rel.split("/")[0] if "/" in new_rel else ""
    new_aspect = DIR_TO_ASPECT.get(new_dir, "connective")

    db.query(
        f"UPDATE {nid} SET "
        f"path = {json.dumps(new_rel, ensure_ascii=False)}, "
        f"directory = {json.dumps(new_dir, ensure_ascii=False)}, "
        f"cluster_id = {json.dumps(new_dir, ensure_ascii=False)}, "
        f'aspect = "{new_aspect}";'
    )
    db.query(
        f"CREATE neuron_history CONTENT {{ "
        f"neuron: {nid}, event_type: 'moved', timestamp: time::now(), "
        f"detail: {json.dumps(f'{old_rel} -> {new_rel}', ensure_ascii=False)} }};"
    )
    db.invalidate_cache()

    if checkpoint is not None:
        checkpoint.pop(old_rel, None)
        # Sync the new file to pick up any content changes
        sync_file(db, str(new_path), checkpoint=checkpoint, quiet=quiet)

    if not quiet:
        print(f"  moved: {old_rel} -> {new_rel}", file=sys.stderr)

    return True


# ─── Checkpoint ──────────────────────────────────────────────────────────────

def load_checkpoint() -> dict:
    if CHECKPOINT.exists():
        try:
            return json.loads(CHECKPOINT.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_checkpoint(ckpt: dict):
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(ckpt))


# ─── Full Import (batch sync) ───────────────────────────────────────────────

def full_import(db: SurrealClient, quiet: bool = False) -> int:
    """Sync all vault files. Returns count of files synced."""
    checkpoint: dict = {}
    count = 0
    for d in CONTENT_DIRS:
        dp = VAULT_ROOT / d
        if not dp.is_dir():
            continue
        for fpath in dp.rglob("*.md"):
            if fpath.name.startswith("_"):
                continue
            if sync_file(db, str(fpath), checkpoint=checkpoint, quiet=quiet):
                count += 1
    save_checkpoint(checkpoint)
    return count


def incremental_sync(db: SurrealClient, quiet: bool = False) -> int:
    """Sync only changed files (by mtime vs checkpoint). Returns count."""
    checkpoint = load_checkpoint()
    count = 0
    for d in CONTENT_DIRS:
        dp = VAULT_ROOT / d
        if not dp.is_dir():
            continue
        for fpath in dp.rglob("*.md"):
            if fpath.name.startswith("_"):
                continue
            rel_path = str(fpath.relative_to(VAULT_ROOT))
            mtime = fpath.stat().st_mtime
            ckpt_entry = checkpoint.get(rel_path, {})
            if isinstance(ckpt_entry, dict):
                old_mtime = ckpt_entry.get("mtime", 0)
            else:
                old_mtime = ckpt_entry  # backward compat: old format was just mtime
            if mtime > old_mtime:
                if sync_file(db, str(fpath), checkpoint=checkpoint, quiet=quiet):
                    count += 1
    if count > 0:
        save_checkpoint(checkpoint)
    return count


# ─── inotify Watcher ─────────────────────────────────────────────────────────

class InotifyWatcher:
    """Pure Python inotify watcher using ctypes. Zero external dependencies."""

    def __init__(self):
        self.libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)
        self.fd = self.libc.inotify_init()
        if self.fd < 0:
            raise OSError("Failed to initialize inotify")

        self._wd_to_path: dict[int, str] = {}
        self._path_to_wd: dict[str, int] = {}

    def add_watch(self, path: str, mask: int) -> int:
        wd = self.libc.inotify_add_watch(
            self.fd, path.encode("utf-8"), ctypes.c_uint32(mask)
        )
        if wd < 0:
            errno = ctypes.get_errno()
            raise OSError(f"inotify_add_watch failed for {path}: errno={errno}")
        self._wd_to_path[wd] = path
        self._path_to_wd[path] = wd
        return wd

    def read_events(self, timeout_ms: int = 1000) -> list[tuple[int, int, int, str]]:
        """Read inotify events. Returns list of (wd, mask, cookie, name)."""
        import select
        readable, _, _ = select.select([self.fd], [], [], timeout_ms / 1000.0)
        if not readable:
            return []

        buf = os.read(self.fd, 8192)
        events = []
        offset = 0
        while offset < len(buf):
            wd, mask, cookie, name_len = struct.unpack_from("iIII", buf, offset)
            offset += struct.calcsize("iIII")
            name = buf[offset:offset + name_len].rstrip(b"\x00").decode("utf-8", errors="replace")
            offset += name_len
            events.append((wd, mask, cookie, name))
        return events

    def get_path(self, wd: int) -> str | None:
        return self._wd_to_path.get(wd)

    def close(self):
        os.close(self.fd)


def watch_vault(db: SurrealClient, quiet: bool = False):
    """Event-driven vault watcher using inotify."""
    checkpoint = load_checkpoint()

    # Set up inotify watches FIRST — before initial sync, so we don't miss
    # events that occur during the sync window
    watcher = InotifyWatcher()
    watch_mask = IN_CLOSE_WRITE | IN_MOVED_FROM | IN_MOVED_TO | IN_DELETE | IN_CREATE | IN_ISDIR
    watch_count = 0

    for d in CONTENT_DIRS:
        dp = VAULT_ROOT / d
        if not dp.is_dir():
            continue
        # Watch the directory and all subdirectories
        for dirpath in [dp] + [p for p in dp.rglob("*") if p.is_dir()]:
            try:
                watcher.add_watch(str(dirpath), watch_mask)
                watch_count += 1
            except OSError as e:
                if not quiet:
                    print(f"  WARN: cannot watch {dirpath}: {e}", file=sys.stderr)

    print(f"Watching {watch_count} directories via inotify", file=sys.stderr)

    # Initial sync AFTER watches are set up — any events during sync are queued
    count = incremental_sync(db, quiet=True)
    if count > 0:
        print(f"Initial sync: {count} files", file=sys.stderr)
    else:
        print(f"Initial sync: all {len(checkpoint)} files up to date", file=sys.stderr)

    # Drain any events that fired during initial sync (they're already synced)
    watcher.read_events(timeout_ms=100)

    # Track moved files by cookie (MOVED_FROM → MOVED_TO pairs)
    pending_moves: dict[int, tuple[str, float]] = {}  # cookie → (old_path, timestamp)
    # Debounce: track last event time per file
    last_event: dict[str, float] = {}

    while alive:
        events = watcher.read_events(timeout_ms=500)

        for wd, mask, cookie, name in events:
            if not name.endswith(".md"):
                # If it's a new subdirectory, add a watch for it
                if mask & IN_CREATE and mask & IN_ISDIR:
                    parent = watcher.get_path(wd)
                    if parent:
                        new_dir = os.path.join(parent, name)
                        try:
                            watcher.add_watch(new_dir, watch_mask)
                        except OSError:
                            pass
                continue

            parent_dir = watcher.get_path(wd)
            if not parent_dir:
                continue
            full_path = os.path.join(parent_dir, name)

            # Debounce — skip if we just handled this file
            now = time.time()
            if full_path in last_event and (now - last_event[full_path]) < DEBOUNCE_SECS:
                continue
            last_event[full_path] = now

            if mask & IN_CLOSE_WRITE:
                # File saved — sync it
                sync_file(db, full_path, checkpoint=checkpoint, quiet=quiet)
                save_checkpoint(checkpoint)

            elif mask & IN_MOVED_FROM:
                # File moved away — record for pairing with MOVED_TO
                pending_moves[cookie] = (full_path, now)

            elif mask & IN_MOVED_TO:
                # File moved in — check if we have a MOVED_FROM to pair
                if cookie in pending_moves:
                    old_path, _ = pending_moves.pop(cookie)
                    move_file(db, old_path, full_path,
                              checkpoint=checkpoint, quiet=quiet)
                else:
                    # Moved from outside watched area — treat as new
                    sync_file(db, full_path, checkpoint=checkpoint, quiet=quiet)
                save_checkpoint(checkpoint)

            elif mask & IN_DELETE:
                # File deleted
                delete_file(db, full_path, checkpoint=checkpoint, quiet=quiet)
                save_checkpoint(checkpoint)

        # Clean up old pending moves (>2s without a matching MOVED_TO = real delete)
        now = time.time()
        expired = [c for c, (_, t) in pending_moves.items() if now - t > 2.0]
        for cookie in expired:
            old_path, _ = pending_moves.pop(cookie)
            delete_file(db, old_path, checkpoint=checkpoint, quiet=quiet)
            save_checkpoint(checkpoint)

        # Clean up debounce cache every 60s
        if len(last_event) > 1000:
            cutoff = now - 10.0
            last_event = {k: v for k, v in last_event.items() if v > cutoff}

    watcher.close()
    save_checkpoint(checkpoint)
    print(f"Stopped. {len(checkpoint)} files in checkpoint.", file=sys.stderr)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    db = SurrealClient(port=SURREAL_PORT)

    # Quick health check
    r = db.query("INFO FOR DB;")
    if not r or r[0].get("status") != "OK":
        print("ERROR: SurrealDB not reachable on port", SURREAL_PORT, file=sys.stderr)
        sys.exit(1)

    if "--watch" in sys.argv:
        print(f"Vault Sync daemon — watching {VAULT_ROOT}", file=sys.stderr)
        watch_vault(db, quiet="--quiet" in sys.argv)

    elif "--full-import" in sys.argv:
        print(f"Full import from {VAULT_ROOT}", file=sys.stderr)
        count = full_import(db, quiet="--quiet" in sys.argv)
        print(f"Synced {count} files", file=sys.stderr)

    elif len(sys.argv) >= 3 and sys.argv[1] == "sync":
        ok = sync_file(db, sys.argv[2])
        sys.exit(0 if ok else 1)

    elif len(sys.argv) >= 3 and sys.argv[1] == "delete":
        ok = delete_file(db, sys.argv[2])
        sys.exit(0 if ok else 1)

    elif len(sys.argv) >= 4 and sys.argv[1] == "move":
        ok = move_file(db, sys.argv[2], sys.argv[3])
        sys.exit(0 if ok else 1)

    else:
        # Default: incremental sync (no watch)
        checkpoint = load_checkpoint()
        print(f"Vault Sync — {len(checkpoint)} in checkpoint", file=sys.stderr)
        count = incremental_sync(db, quiet="--quiet" in sys.argv)
        print(f"Synced {count} changed files", file=sys.stderr)


if __name__ == "__main__":
    main()
