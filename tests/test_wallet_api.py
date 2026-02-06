import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from cohezion.api import app

client = TestClient(app)


def test_get_wallet_success():
    """Test that /wallet returns correct data when file exists."""
    mock_data = {"balance": 500, "history": [{"amount": 500, "reason": "Test"}]}

    with patch("pathlib.Path.read_text", return_value=json.dumps(mock_data)):
        with patch("pathlib.Path.exists", return_value=True):
            response = client.get("/wallet")
            assert response.status_code == 200
            assert response.json() == mock_data


def test_get_wallet_missing():
    """Test that /wallet returns empty state when file missing."""
    with patch("pathlib.Path.exists", return_value=False):
        response = client.get("/wallet")
        assert response.status_code == 200
        assert response.json() == {"balance": 0, "history": []}


def test_wallet_integration():
    """Integration test checking the actual file logic (if file exists)."""
    # This might fail if the file is locked or missing in CI, but good for local
    wallet_path = Path("src/cohezion/knowledge_graph/wallet.json")
    if wallet_path.exists():
        response = client.get("/wallet")
        assert response.status_code == 200
        data = response.json()
        assert "balance" in data
        assert isinstance(data["balance"], int)
