import logging
import httpx
from pathlib import Path
from cohezion.reliability import get_circuit
from cohezion.reliability.pool import get_pool

logger = logging.getLogger(__name__)

class KaggleAPI:
    """
    Kaggle API Integration for downloading datasets and pushing notebooks.
    
    Implements circuit breaker and connection pooling for reliability.
    """
    
    def __init__(
        self, 
        username: str, 
        key: str, 
        base_url: str = "https://www.kaggle.com/api/v1",
        failure_threshold: int = 5
    ):
        self.username = username
        self.key = key
        self.base_url = base_url
        self.circuit = get_circuit("kaggle_api", failure_threshold=failure_threshold)
        self.pool = get_pool("kaggle_api", base_url=base_url)
        self.auth = (username, key)

    async def _handle_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Helper to handle requests with circuit breaker logic."""
        if not self.circuit.allow_request():
            raise Exception(f"Circuit {self.circuit.name} is OPEN. Rejecting request.")
            
        try:
            if method == "GET":
                response = await self.pool.get(path, auth=self.auth, **kwargs)
            elif method == "POST":
                response = await self.pool.post(path, auth=self.auth, **kwargs)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            if response.status_code >= 400:
                logger.error(f"Kaggle API error: {response.status_code} - {response.text}")
                # Don't record failure here yet, let raise_for_status trigger the except block
                response.raise_for_status()
                
            self.circuit.record_success()
            return response
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Kaggle API status error: {e}")
            self.circuit.record_failure()
            raise
        except Exception as e:
            logger.error(f"Kaggle API request failed: {e}")
            self.circuit.record_failure()
            raise

    async def download_dataset(self, dataset_name: str) -> bytes:
        """Download a dataset from Kaggle."""
        path = f"/datasets/download/{dataset_name}"
        response = await self._handle_request("GET", path)
        return response.content

    async def push_notebook(self, notebook_id: str, code: str) -> dict:
        """Push a notebook to Kaggle."""
        path = f"/kernels/push/{notebook_id}"
        payload = {
            "id": notebook_id,
            "code": code,
            "language": "python",
            "kernel_type": "notebook"
        }
        response = await self._handle_request("POST", path, json=payload)
        return response.json()

    async def submit_adapter(self, competition_id: str, adapter_path: Path, message: str) -> dict:
        """Submit a LoRA adapter to a Kaggle competition."""
        path = f"/competitions/submissions/submit/{competition_id}"
        # In a real implementation, this would involve a multi-part file upload.
        # For this baseline, we'll mock the submission payload.
        payload = {
            "fileName": adapter_path.name,
            "submissionDescription": message
        }
        response = await self._handle_request("POST", path, json=payload)
        return response.json()
