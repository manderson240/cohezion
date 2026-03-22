import logging
import os

from cohezion.security.vault import get_vault


logger = logging.getLogger(__name__)


class CredentialManager:
    """Centralized credential retrieval with Bitwarden priority and ENV fallback."""

    def __init__(self):
        self.vault = get_vault()

    def get_secret(self, name: str, env_var: str | None = None) -> str | None:
        """
        Get a secret.
        1. Try Bitwarden (name)
        2. Try os.environ (env_var or name)
        """
        # 1. Try Bitwarden
        secret = self.vault.get_secret(name)
        if secret:
            logger.info(f"Retrieved secret '{name}' from Bitwarden.")
            return secret

        # 2. Try Fallback
        fallback_key = env_var or name
        secret = os.environ.get(fallback_key)
        if secret:
            logger.debug(f"Retrieved secret '{fallback_key}' from Environment.")
            return secret

        return None


# Singleton
_manager = None


def get_credentials() -> CredentialManager:
    global _manager
    if _manager is None:
        _manager = CredentialManager()
    return _manager
