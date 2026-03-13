"""SurrealDB HTTP client for vault sync."""

import base64
import json
import urllib.request
from pathlib import Path

from .config import SURREAL_NS, SURREAL_DB, SURREAL_USER, SURREAL_PASS


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
