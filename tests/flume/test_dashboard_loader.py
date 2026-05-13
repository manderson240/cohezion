import pandas as pd
import pytest

from cohezion.storage.surreal_client import SurrealDBClient


@pytest.mark.asyncio
async def test_holographic_dashboard_data_loader():
    """
    RED PHASE: Verify that the dashboard can load and process correlated data.
    """
    client = SurrealDBClient()
    client.connected = True

    # Mock a correlated response
    mock_data = {
        "journey": [{"evo_id": "j1", "dimension_state": [0.1] * 12, "coherence": 0.5, "timestamp": "1"}],
        "universe_shifts": [{"universe_id": "j1", "state_12d": [0.2] * 12, "coherence": 0.4, "stability_shift": 0.1}],
        "correlations": [{"journey_step": 0, "universe_event": 0}],
    }

    with patch.object(client, "query_holographic_record", return_value=mock_data):
        result = await client.query_holographic_record("j1")

        # Dashboard logic would then convert to DataFrame
        df_j = pd.DataFrame(result["journey"])
        df_u = pd.DataFrame(result["universe_shifts"])

        assert not df_j.empty
        assert not df_u.empty
        assert df_u.iloc[0]["stability_shift"] == 0.1


from unittest.mock import patch
