#!/usr/bin/env python3
"""SurrealDB-Aware Web Server for Marimo WASM Dashboard & Multimodal Assets.

Automatically finds the next available port from SurrealDB Port Registry and launches
the standalone HTTP server.
"""

from __future__ import annotations

import functools
import http.server
import os
import socketserver
import sys
from pathlib import Path


# Add src to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

from cohezion.infra.port_registry import SurrealPortRegistry


def serve_dashboard() -> None:
    registry = SurrealPortRegistry()
    free_port = registry.find_next_available_port(start_port=8082)
    directory = Path("/home/mike-anderson/dev/cohezion/docs/assets/renderings")

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))

    print("=" * 90)
    print("    🌐 COHEZION STANDALONE WASM DASHBOARD & ASSETS SERVER")
    print("=" * 90)
    print(f"📁 Serving Directory: {directory}")
    print(f"🔌 Allocated Port: {free_port} (Tracked in SurrealDB `system_port` table)")
    print(f"🚀 URL: http://localhost:{free_port}/cohezion_master_dashboard_wasm.html")
    print("=" * 90)

    # Register in SurrealDB
    registry.sync_to_surrealdb([
        registry.scan_active_system_ports()[0].__class__(
            port=free_port,
            service_name="Marimo WASM Dashboard",
            protocol="tcp",
            pid=os.getpid(),
            status="active",
            description="Standalone WASM Web Dashboard",
        )
    ])

    with socketserver.TCPServer(("", free_port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


if __name__ == "__main__":
    serve_dashboard()
