"""surreal_basic_auth goes through the credential gate; it never invents root/root."""

import base64

import pytest

from cohezion.core.persistence import surreal_client as sc


@pytest.fixture
def clean_env(monkeypatch):
    for name in ("SURREAL_USER", "SURREAL_PASSWORD", "COHEZION_ALLOW_INSECURE_SURREAL"):
        monkeypatch.delenv(name, raising=False)
    # Bitwarden is irrelevant here: force the vault branch to fall through to env.
    monkeypatch.setattr("cohezion.security.vault.get_vault", lambda: (_ for _ in ()).throw(OSError))
    return monkeypatch


def test_uses_resolved_credentials(clean_env):
    clean_env.setenv("SURREAL_USER", "svc")
    clean_env.setenv("SURREAL_PASSWORD", "s3cret-not-root")
    header = sc.surreal_basic_auth()
    assert base64.b64decode(header.removeprefix("Basic ")) == b"svc:s3cret-not-root"


def test_refuses_without_credentials(clean_env):
    with pytest.raises(sc.InsecureSurrealCredentialsError):
        sc.surreal_basic_auth()
