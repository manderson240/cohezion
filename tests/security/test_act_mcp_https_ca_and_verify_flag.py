"""MCPHTTPSClient: a missing CA must fail loudly, and verify_ssl must be a real bool.

Work-queue 9df53f... (security review LOW, 2026-09-21). Two defects:
  1. ``get_ssl_context`` with a ``ca_cert_path`` that does not exist logs a warning and
     returns a context trusting the SYSTEM CA bundle, while the httpx path given the same
     client raises ``FileNotFoundError``. The same misconfiguration must fail the same way.
  2. ``__init__`` guards with ``if not verify_ssl``, so the STRING ``"false"`` (e.g. from an
     env var) is truthy and accepted. Only the bool ``True`` is a valid value.
Positive controls: a real CA file and no CA at all must keep working.
"""

from __future__ import annotations

import ssl

import certifi
import httpx
import pytest

from cohezion.security.mcp_https_client import MCPHTTPSClient


def test_missing_ca_raises_like_httpx(tmp_path) -> None:
    missing = str(tmp_path / "missing-ca.pem")
    with pytest.raises(FileNotFoundError):  # control: the httpx path already fails this way
        httpx.Client(verify=missing)
    with pytest.raises(FileNotFoundError):
        MCPHTTPSClient(use_https=True, ca_cert_path=missing).get_ssl_context()


def test_existing_ca_still_loads() -> None:
    ctx = MCPHTTPSClient(use_https=True, ca_cert_path=certifi.where()).get_ssl_context()
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True


def test_no_ca_uses_system_bundle() -> None:
    ctx = MCPHTTPSClient(use_https=True).get_ssl_context()
    assert isinstance(ctx, ssl.SSLContext)
    assert ctx.verify_mode == ssl.CERT_REQUIRED


def test_http_client_needs_no_context() -> None:
    assert MCPHTTPSClient(use_https=False, ca_cert_path="/nonexistent.pem").get_ssl_context() is None


@pytest.mark.parametrize("bad", ["false", "False", "0", "no", "true", 0, 1, None])
def test_verify_ssl_must_be_bool_true(bad) -> None:
    with pytest.raises(ValueError):
        MCPHTTPSClient(use_https=True, verify_ssl=bad)


def test_verify_ssl_true_accepted() -> None:
    assert MCPHTTPSClient(use_https=True, verify_ssl=True).verify_ssl is True
