import logging
import os

from cohezion.security.gcp_vault import get_gcp_vault
from cohezion.security.vault import get_vault

logger = logging.getLogger(__name__)


class CredentialManager:
    """Centralized credential retrieval.

    Priority order:
    1. Bitwarden vault (local dev, identified by BW_SESSION or unlocked CLI)
    2. GCP Secret Manager (production on Cloud Run; active when GOOGLE_CLOUD_PROJECT is set)
    3. Environment variables (fallback / CI)
    """

    def __init__(self) -> None:
        self.vault = get_vault()
        self.gcp_vault = get_gcp_vault()

    def get_secret(self, name: str, env_var: str | None = None) -> str | None:
        """Get a secret by name.

        Args:
            name: Primary lookup key (Bitwarden item name / GCP secret name).
            env_var: Environment variable to check as final fallback. If omitted,
                     ``name`` is used as the env var key.

        Returns:
            Secret value or ``None`` if not found in any source.
        """
        # 1. Try Bitwarden (local dev)
        secret = self.vault.get_secret(name)
        if secret:
            logger.info("Retrieved secret '%s' from Bitwarden.", name)
            return secret

        # 2. Try GCP Secret Manager (production)
        secret = self.gcp_vault.get_secret(name)
        if secret:
            logger.info("Retrieved secret '%s' from GCP Secret Manager.", name)
            return secret

        # 3. Try environment variable (fallback / CI)
        fallback_key = env_var or name
        secret = os.environ.get(fallback_key)
        if secret:
            logger.debug("Retrieved secret '%s' from environment.", fallback_key)
            return secret

        return None


# Singleton
_manager = None


def get_credentials() -> CredentialManager:
    global _manager
    if _manager is None:
        _manager = CredentialManager()
    return _manager
