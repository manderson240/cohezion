"""GCP Secret Manager vault — production-tier secret retrieval.

Used when the service runs on Google Cloud (Cloud Run, GKE, etc.).
Falls back gracefully when not on GCP or when the SDK is not installed.

The vault is detected as active when GOOGLE_CLOUD_PROJECT is set in
the environment (Cloud Run sets this automatically).
"""

from __future__ import annotations

import logging
import os


logger = logging.getLogger(__name__)


class GCPSecretVault:
    """Read secrets from GCP Secret Manager.

    Interface mirrors BitwardenVault so CredentialManager can swap them
    transparently based on environment.
    """

    def __init__(self, project_id: str | None = None) -> None:
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self._client: object | None = None
        self._available: bool | None = None  # None = not yet probed

    def _is_available(self) -> bool:
        """Return True if Secret Manager SDK is installed and project is configured."""
        if self._available is not None:
            return self._available

        if not self.project_id:
            logger.debug("GCPSecretVault: GOOGLE_CLOUD_PROJECT not set — disabled.")
            self._available = False
            return False

        try:
            from google.cloud import secretmanager  # type: ignore[import]

            self._client = secretmanager.SecretManagerServiceClient()
            self._available = True
            logger.debug("GCPSecretVault: Secret Manager client initialised for project '%s'.", self.project_id)
        except ImportError:
            logger.debug(
                "GCPSecretVault: google-cloud-secret-manager not installed — disabled. "
                "Install with: uv pip install 'cohezion[gcp]'"
            )
            self._available = False
        except Exception as exc:
            logger.warning("GCPSecretVault: failed to initialise client: %s", exc)
            self._available = False

        return self._available

    def get_secret(self, name: str, version: str = "latest") -> str | None:
        """Retrieve a secret value from GCP Secret Manager.

        Args:
            name: Secret resource name as stored in GCP Secret Manager.
                  Can be a short name (e.g. ``"cohezion-api-key"``) which is
                  resolved to the full resource path automatically, or a full
                  resource name (``"projects/.../secrets/.../versions/..."``)
            version: Secret version, defaults to ``"latest"``.

        Returns:
            Secret payload as a string, or ``None`` if not found.
        """
        if not self._is_available():
            return None

        try:
            from google.api_core.exceptions import NotFound  # type: ignore[import]
            from google.cloud import secretmanager  # type: ignore[import]

            client: secretmanager.SecretManagerServiceClient = self._client  # type: ignore[assignment]

            # Build full resource name if a short name was given
            if not name.startswith("projects/"):
                resource = f"projects/{self.project_id}/secrets/{name}/versions/{version}"
            else:
                resource = name

            response = client.access_secret_version(request={"name": resource})
            payload = response.payload.data.decode("utf-8")
            logger.debug("GCPSecretVault: retrieved secret '%s'.", name)
            return payload

        except NotFound:
            logger.debug("GCPSecretVault: secret '%s' not found.", name)
            return None
        except Exception as exc:
            logger.warning("GCPSecretVault: error retrieving secret '%s': %s", name, exc)
            return None


def get_gcp_vault() -> GCPSecretVault:
    """Convenience factory."""
    return GCPSecretVault()
