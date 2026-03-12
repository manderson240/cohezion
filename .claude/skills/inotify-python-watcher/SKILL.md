---
name: inotify-python-watcher
description: |
  Real-time Linux filesystem watching via Python ctypes (zero external dependencies).
  Use when: (1) building a file sync daemon for Linux, (2) need <1s latency on file changes,
  (3) can't or don't want to install watchdog/pyinotify packages, (4) need to watch
  deeply nested directory trees for CREATE/MODIFY/DELETE/MOVE events.
  Key patterns: inotify_init → add_watch per dir → select() loop → parse inotify_event structs.
  CRITICAL: Always add watches BEFORE initial sync to avoid missing events during the sync window.
author: Claude Code
version: 1.0.0
---

# Python inotify Watcher (Zero Dependencies)

## Problem

Need real-time file system watching on Linux without external Python packages.
`watchdog` and `pyinotify` work but add dependencies. Python's `ctypes` gives direct
access to the Linux kernel inotify API through glibc.

## Key Insight: Watch Ordering Race Condition

**ALWAYS add inotify watches BEFORE running the initial sync pass.**

If you scan files first and then set up watches, any file changes during the scan
window are missed. The queue for inotify events starts filling the moment watches
are added — events during initial sync are buffered and processed after the scan.

```python
# WRONG — misses events during initial_sync()
initial_sync()
watcher.add_all_watches()  # Too late

# CORRECT — events during sync are buffered and processed after
watcher.add_all_watches()
initial_sync()
watcher.process_queued_events()  # Drain any events that arrived during sync
```

## Complete Implementation

```python
import ctypes
import ctypes.util
import os
import select
import struct
import time
from pathlib import Path

# inotify event mask flags
IN_CLOSE_WRITE = 0x00000008   # File written and closed (use this for MODIFY)
IN_MOVED_FROM  = 0x00000040   # File moved away from watched dir
IN_MOVED_TO    = 0x00000080   # File moved into watched dir
IN_DELETE      = 0x00000200   # File deleted
IN_CREATE      = 0x00000100   # File created (may not be complete yet — wait for CLOSE_WRITE)
IN_ISDIR       = 0x40000000   # Event is on a directory, not a file
IN_DELETE_SELF = 0x00000400   # Watched dir itself deleted

WATCH_MASK = (IN_CLOSE_WRITE | IN_MOVED_FROM | IN_MOVED_TO | IN_DELETE | IN_CREATE)

# inotify_event header: wd(int) mask(uint) cookie(uint) len(uint) = 16 bytes
EVENT_HEADER = struct.Struct("iIII")
EVENT_HEADER_SIZE = EVENT_HEADER.size  # 16


class InotifyWatcher:
    def __init__(self):
        libc_name = ctypes.util.find_library("c")
        self.libc = ctypes.CDLL(libc_name, use_errno=True)
        self.fd = self.libc.inotify_init()
        if self.fd < 0:
            raise OSError(ctypes.get_errno(), "inotify_init failed")
        self._wd_to_path: dict[int, str] = {}
        self._path_to_wd: dict[str, int] = {}

    def add_watch(self, path: str, mask: int = WATCH_MASK) -> int:
        wd = self.libc.inotify_add_watch(
            self.fd, path.encode("utf-8"), ctypes.c_uint32(mask)
        )
        if wd < 0:
            raise OSError(ctypes.get_errno(), f"inotify_add_watch failed for {path}")
        self._wd_to_path[wd] = path
        self._path_to_wd[path] = wd
        return wd

    def remove_watch(self, path: str) -> None:
        wd = self._path_to_wd.pop(path, None)
        if wd is not None:
            self.libc.inotify_rm_watch(self.fd, wd)
            self._wd_to_path.pop(wd, None)

    def add_tree(self, root: str, skip_dirs: set[str] | None = None) -> int:
        """Add watches for root and all subdirectories recursively."""
        skip = skip_dirs or set()
        count = 0
        for dirpath, dirs, _ in os.walk(root):
            dirs[:] = [d for d in dirs if d not in skip and not d.startswith(".")]
            try:
                self.add_watch(dirpath)
                count += 1
            except OSError:
                pass
        return count

    def read_events(self, timeout_ms: int = 1000) -> list[dict]:
        """Read pending inotify events. Returns list of event dicts."""
        readable, _, _ = select.select([self.fd], [], [], timeout_ms / 1000.0)
        if not readable:
            return []

        buf = os.read(self.fd, 65536)
        events = []
        offset = 0

        while offset < len(buf):
            if offset + EVENT_HEADER_SIZE > len(buf):
                break
            wd, mask, cookie, name_len = EVENT_HEADER.unpack_from(buf, offset)
            offset += EVENT_HEADER_SIZE

            name = ""
            if name_len > 0:
                raw = buf[offset : offset + name_len]
                name = raw.rstrip(b"\x00").decode("utf-8", errors="replace")
                offset += name_len

            dir_path = self._wd_to_path.get(wd, "")
            full_path = os.path.join(dir_path, name) if name else dir_path

            events.append({
                "wd": wd,
                "mask": mask,
                "cookie": cookie,
                "name": name,
                "path": full_path,
                "is_dir": bool(mask & IN_ISDIR),
            })

        return events

    def close(self) -> None:
        os.close(self.fd)
```

## Event Loop with Debounce

```python
DEBOUNCE_SECONDS = 0.5

def watch_loop(watcher: InotifyWatcher, on_create, on_modify, on_delete, on_move):
    pending: dict[str, tuple[str, float]] = {}  # path → (event_type, timestamp)
    cookie_map: dict[int, str] = {}             # cookie → moved_from path

    while True:
        events = watcher.read_events(timeout_ms=200)
        now = time.monotonic()

        for evt in events:
            path = evt["path"]
            mask = evt["mask"]
            if evt["is_dir"]:
                continue  # Handle dir create separately if needed

            if mask & IN_MOVED_FROM:
                cookie_map[evt["cookie"]] = path
            elif mask & IN_MOVED_TO:
                old = cookie_map.pop(evt["cookie"], None)
                if old:
                    on_move(old, path)
            elif mask & IN_CLOSE_WRITE:
                pending[path] = ("modify", now)
            elif mask & IN_CREATE:
                pending[path] = ("create", now)
            elif mask & IN_DELETE:
                pending.setdefault(path, ("delete", now))

        # Flush debounced events
        for path, (event_type, ts) in list(pending.items()):
            if now - ts >= DEBOUNCE_SECONDS:
                del pending[path]
                if event_type == "create":
                    on_create(path)
                elif event_type == "modify":
                    on_modify(path)
                elif event_type == "delete":
                    on_delete(path)
```

## New Directory Handling

When a new directory is created inside a watched tree, add a watch for it immediately:

```python
for evt in events:
    if evt["is_dir"] and (evt["mask"] & IN_CREATE):
        try:
            watcher.add_watch(evt["path"])
            # Also scan it for any files already created before the watch was added
            for f in Path(evt["path"]).iterdir():
                if f.is_file():
                    on_create(str(f))
        except OSError:
            pass
```

## Diagnostic: Verify inotify is Working

```python
import subprocess
result = subprocess.run(
    ["cat", "/proc/sys/fs/inotify/max_user_watches"],
    capture_output=True, text=True
)
print(f"Max inotify watches: {result.stdout.strip()}")

# Increase if needed (requires root or sysctl):
# sudo sysctl fs.inotify.max_user_watches=524288
```

## Common Pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| Watching file instead of dir | `inotify_add_watch` returns -1 | Only watch directories, not files |
| IN_CREATE but file empty | Read 0 bytes on create | Use `IN_CLOSE_WRITE` for write completion |
| Missing events on new subdirs | No events in new dirs | Watch subdirs on `IN_CREATE\|IN_ISDIR` |
| Race on startup | First file write missed | Add watches BEFORE initial scan |
| Stale cookie_map | Move pairs don't match | Set TTL on cookie entries (~5s) |
| EAGAIN on read | No events buffered | Normal — use select() to avoid busy wait |

## Verification

```python
# Quick end-to-end test
import tempfile, threading, time

watcher = InotifyWatcher()
watcher.add_watch("/tmp")
events_seen = []

def read_thread():
    for _ in range(10):
        for e in watcher.read_events(timeout_ms=500):
            events_seen.append(e)

t = threading.Thread(target=read_thread, daemon=True)
t.start()
time.sleep(0.1)

with tempfile.NamedTemporaryFile(dir="/tmp", suffix=".test", delete=False) as f:
    f.write(b"hello")

t.join(timeout=3)
assert any(".test" in e["path"] for e in events_seen), "No events received"
print("inotify working correctly")
watcher.close()
```
