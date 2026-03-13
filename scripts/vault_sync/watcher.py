"""inotify-based vault watcher with event-driven sync loop."""

import ctypes
import ctypes.util
import os
import struct
import sys
import time

from .batch import incremental_sync
from .checkpoint import load_checkpoint, save_checkpoint
from .client import SurrealClient
from .config import (
    VAULT_ROOT, CONTENT_DIRS, DEBOUNCE_SECS,
    IN_CLOSE_WRITE, IN_MOVED_FROM, IN_MOVED_TO, IN_DELETE, IN_CREATE, IN_ISDIR,
    alive,
)
from .reactor import GraphReactor
from .sync import sync_file, delete_file, move_file
from .writeback import NeuralWriteBack


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
    """Event-driven vault watcher using inotify + graph reactor + neural write-back."""
    checkpoint = load_checkpoint()
    reactor = GraphReactor(db)
    writeback = NeuralWriteBack(db)

    watcher = InotifyWatcher()
    watch_mask = IN_CLOSE_WRITE | IN_MOVED_FROM | IN_MOVED_TO | IN_DELETE | IN_CREATE | IN_ISDIR
    watch_count = 0

    for d in CONTENT_DIRS:
        dp = VAULT_ROOT / d
        if not dp.is_dir():
            continue
        for dirpath in [dp] + [p for p in dp.rglob("*") if p.is_dir()]:
            try:
                watcher.add_watch(str(dirpath), watch_mask)
                watch_count += 1
            except OSError as e:
                if not quiet:
                    print(f"  WARN: cannot watch {dirpath}: {e}", file=sys.stderr)

    print(f"Watching {watch_count} directories via inotify", file=sys.stderr)

    count = incremental_sync(db, quiet=True)
    if count > 0:
        print(f"Initial sync: {count} files", file=sys.stderr)
    else:
        print(f"Initial sync: all {len(checkpoint)} files up to date", file=sys.stderr)

    watcher.read_events(timeout_ms=100)

    reactor._last_run = 0
    if reactor.maybe_react():
        print("Graph reactor: alerts written to metabolism/graph-alerts.md", file=sys.stderr)

    pending_moves: dict[int, tuple[str, float]] = {}
    last_event: dict[str, float] = {}

    while alive:
        events = watcher.read_events(timeout_ms=500)

        for wd, mask, cookie, name in events:
            if not name.endswith(".md"):
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

            now = time.time()
            if full_path in last_event and (now - last_event[full_path]) < DEBOUNCE_SECS:
                continue
            last_event[full_path] = now

            if mask & IN_CLOSE_WRITE:
                sync_file(db, full_path, checkpoint=checkpoint, quiet=quiet)
                save_checkpoint(checkpoint)

            elif mask & IN_MOVED_FROM:
                pending_moves[cookie] = (full_path, now)

            elif mask & IN_MOVED_TO:
                if cookie in pending_moves:
                    old_path, _ = pending_moves.pop(cookie)
                    move_file(db, old_path, full_path,
                              checkpoint=checkpoint, quiet=quiet)
                else:
                    sync_file(db, full_path, checkpoint=checkpoint, quiet=quiet)
                save_checkpoint(checkpoint)

            elif mask & IN_DELETE:
                delete_file(db, full_path, checkpoint=checkpoint, quiet=quiet)
                save_checkpoint(checkpoint)

        now = time.time()
        expired = [c for c, (_, t) in pending_moves.items() if now - t > 2.0]
        for cookie in expired:
            old_path, _ = pending_moves.pop(cookie)
            delete_file(db, old_path, checkpoint=checkpoint, quiet=quiet)
            save_checkpoint(checkpoint)

        if len(last_event) > 1000:
            cutoff = now - 10.0
            last_event = {k: v for k, v in last_event.items() if v > cutoff}

        if events:
            if reactor.maybe_react():
                if not quiet:
                    print("Graph reactor: alerts updated", file=sys.stderr)

        if writeback.maybe_run():
            if not quiet:
                print("Neural write-back: frontmatter updated", file=sys.stderr)

    watcher.close()
    save_checkpoint(checkpoint)
    print(f"Stopped. {len(checkpoint)} files in checkpoint.", file=sys.stderr)
