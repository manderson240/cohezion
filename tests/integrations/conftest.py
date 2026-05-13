"""Integration test configuration.

Sets COHEZION_ALLOW_INSECURE_SURREAL=1 so integration tests can connect to
a local SurrealDB instance with default credentials (root/root) without
needing Bitwarden credentials configured.
"""

import os

os.environ.setdefault("COHEZION_ALLOW_INSECURE_SURREAL", "1")
