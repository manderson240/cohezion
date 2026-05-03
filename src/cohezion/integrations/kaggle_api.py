import json
import logging
import os
from pathlib import Path

import httpx
import kagglehub
from kaggle.api.kaggle_api_extended import KaggleApi

from cohezion.reliability import CircuitBreaker


logger = logging.getLogger(__name__)

_BASE_URL = "https://www.kaggle.com/api/v1"


class KaggleAPI:
    """Wrapper for official Kaggle API with asynchronous support."""

    def __init__(
        self,
        username: str | None = None,
        key: str | None = None,
        failure_threshold: int = 5,
    ):
        self.api = KaggleApi()
        self.username = username
        self.key = key
        self.circuit = CircuitBreaker(name="kaggle_api", failure_threshold=failure_threshold)
        self.pool = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(connect=10.0, read=60.0, write=60.0, pool=60.0),
        )

        if username and key:
            os.environ["KAGGLE_USERNAME"] = username
            os.environ["KAGGLE_KEY"] = key

        try:
            self.api.authenticate()
            self.username = username or os.environ.get("KAGGLE_USERNAME")
            logger.info("Kaggle API authenticated successfully.")
        except Exception as e:
            logger.warning(f"Kaggle API authentication failed: {e}.")

    async def download_dataset(self, competition_id: str) -> bytes:
        """Download competition data from Kaggle REST API (returns raw bytes)."""
        logger.info(f"Downloading data for competition: {competition_id}")
        response = await self.pool.get(
            f"/datasets/download/{competition_id}",
            auth=(self.username or "", self.key or ""),
        )
        try:
            response.raise_for_status()
            self.circuit.record_success()
        except httpx.HTTPStatusError:
            self.circuit.record_failure()
            raise
        return response.content

    async def download_dataset_path(self, competition_id: str) -> Path:
        """Download competition data from Kaggle using kagglehub (returns Path)."""
        import asyncio

        logger.info(f"Downloading data for competition: {competition_id} via kagglehub")
        try:
            # kagglehub.competition_download is synchronous blocking I/O
            download_path = await asyncio.to_thread(
                kagglehub.competition_download, competition_id
            )
            logger.info(f"Data downloaded to: {download_path}")
            return Path(download_path)
        except Exception as e:
            logger.error(f"Failed to download competition data via kagglehub: {e}")
            raise

    async def push_notebook(
        self,
        notebook_id: str,
        notebook_code: str,
        competition_id: str | None = None,
        model_sources: list[str] | None = None,
        dataset_sources: list[str] | None = None,
    ) -> dict:
        """Push a notebook to Kaggle with the EXACT metadata required for Blackwell G4."""
        logger.info(f"Pushing notebook: {notebook_id}")

        temp_dir = Path(f"data/temp_notebook_{notebook_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Parse or wrap the code
        try:
            nb_json = json.loads(notebook_code)
        except ValueError:
            # Wrap raw python script into notebook format
            nb_json = {
                "cells": [
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {"trusted": True},
                        "outputs": [],
                        "source": [notebook_code],
                    }
                ],
                "metadata": {
                    "kernelspec": {
                        "display_name": "Python 3",
                        "language": "python",
                        "name": "python3",
                    },
                    "language_info": {"name": "python", "version": "3.12.12"},
                },
                "nbformat": 4,
                "nbformat_minor": 4,
            }

        # Inject internal metadata
        nb_json["metadata"]["kaggle"] = {
            "accelerator": "nvidiaRtxPro6000",
            "isInternetEnabled": True,
            "language": "python",
            "sourceType": "notebook",
            "isGpuEnabled": True,
            "dockerImageVersionId": 31287,
        }

        script_path = temp_dir / "notebook.ipynb"
        with open(script_path, "w") as f:
            json.dump(nb_json, f, indent=2)

        # Create kernel-metadata.json using the newly discovered machine_shape field
        metadata = {
            "id": f"{self.username}/{notebook_id}",
            "title": notebook_id,
            "code_file": "notebook.ipynb",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": "true",
            "enable_gpu": "true",
            "enable_tpu": "false",
            "enable_internet": "true",
            "dataset_sources": dataset_sources or [],
            "competition_sources": [competition_id] if competition_id else [],
            "kernel_sources": ["ryanholbrook/nvidia-utility-script"],
            "model_sources": model_sources or [],
            "docker_image_pinning_type": "original",
            "machine_shape": "NvidiaRtxPro6000",
        }

        metadata_path = temp_dir / "kernel-metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        try:
            logger.info(f"Pushing notebook {notebook_id} to Kaggle via REST API...")
            response = await self.pool.post(
                "/kernels/push",
                json={"metadata": metadata, "blob": nb_json},
                auth=(self.username or "", self.key or ""),
            )
            response.raise_for_status()
            self.circuit.record_success()
            result = response.json()
            url = result.get("url", f"https://www.kaggle.com/{self.username}/{notebook_id}")
            logger.info(f"Success! URL: {url}")
            return result
        except httpx.HTTPStatusError as e:
            self.circuit.record_failure()
            logger.error(f"Kaggle push failed (HTTP {e.response.status_code}): {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to push notebook: {e}")
            raise

    async def get_notebook_status(self, notebook_id: str) -> str:
        """Get the status of a Kaggle notebook."""
        kernel_slug = f"{self.username}/{notebook_id}"
        try:
            status_result = self.api.kernels_status(kernel_slug)
            return getattr(status_result, "status", "unknown")
        except Exception as e:
            logger.error(f"Failed to get notebook status: {e}")
            return "error"

    async def get_notebook_output(self, notebook_id: str) -> str:
        """Get the output/logs of a Kaggle notebook."""
        kernel_slug = f"{self.username}/{notebook_id}"
        temp_log_dir = Path(f"data/logs_{notebook_id}")
        temp_log_dir.mkdir(parents=True, exist_ok=True)
        try:
            # kernels_output requires a path to download results
            self.api.kernels_output(kernel_slug, path=str(temp_log_dir))
            # The log might be in a file if it's large
            log_file = temp_log_dir / f"{notebook_id}.log"
            if log_file.exists():
                return log_file.read_text()
            return "Log file not found after download."
        except Exception as e:
            logger.error(f"Failed to get notebook logs: {e}")
            return str(e)

    async def submit_to_competition(
        self, adapter_path: Path, message: str, competition_id: str
    ) -> dict:
        """Submit results to a Kaggle competition."""
        logger.info(f"Submitting {adapter_path} to competition: {competition_id}")
        try:
            self.api.competition_submit(str(adapter_path), message, competition_id)
            return {"status": "submitted"}
        except Exception as e:
            logger.error(f"Failed to submit to Kaggle: {e}")
            raise
