import json
import logging
import os
import subprocess


logger = logging.getLogger(__name__)


class BitwardenVault:
    """Secure interface for Bitwarden CLI (bw)."""

    def __init__(self, session_key: str | None = None):
        self.session_key = session_key or os.environ.get("BW_SESSION")
        self.bw_path = os.path.expanduser("~/.local/bin/bw")

    def is_locked(self) -> bool:
        """Check if the vault is locked."""
        try:
            result = subprocess.run(
                [self.bw_path, "status"], capture_output=True, text=True, check=True
            )
            status = json.loads(result.stdout)
            return status.get("status") == "locked"
        except Exception:
            return True

    def get_secret(self, name: str) -> str | None:
        """Retrieve a secret (password) by its item name."""
        if self.is_locked() and not self.session_key:
            logger.warning("Vault is locked and no BW_SESSION provided.")
            return None

        try:
            cmd = [self.bw_path, "get", "item", name]
            env = os.environ.copy()
            if self.session_key:
                env["BW_SESSION"] = self.session_key

            result = subprocess.run(cmd, capture_output=True, text=True, env=env)

            if result.returncode != 0:
                logger.error(f"Failed to get item {name}: {result.stderr}")
                return None

            data = json.loads(result.stdout)
            # Find the password field
            login = data.get("login", {})
            return login.get("password")

        except Exception as e:
            logger.error(f"Bitwarden retrieval error: {e}")
            return None


def get_vault() -> BitwardenVault:
    """Convenience factory."""
    return BitwardenVault()
