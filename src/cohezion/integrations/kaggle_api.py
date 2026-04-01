import json
import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

import kagglehub
from kaggle.api.kaggle_api_extended import KaggleApi


logger = logging.getLogger(__name__)

class KaggleAPI:
    """Wrapper for official Kaggle API with asynchronous support."""

    def __init__(self, username: Optional[str] = None, key: Optional[str] = None):
        self.api = KaggleApi()
        if username and key:
            os.environ["KAGGLE_USERNAME"] = username
            os.environ["KAGGLE_KEY"] = key

        try:
            self.api.authenticate()
            self.username = username or os.environ.get("KAGGLE_USERNAME")
            logger.info("Kaggle API authenticated successfully.")
        except Exception as e:
            logger.warning(f"Kaggle API authentication failed: {e}.")

    async def download_dataset(self, competition_id: str) -> Path:
        """Download competition data from Kaggle using kagglehub."""
        logger.info(f"Downloading data for competition: {competition_id} via kagglehub")
        try:
            download_path = kagglehub.competition_download(competition_id)
            logger.info(f"Data downloaded to: {download_path}")
            return Path(download_path)
        except Exception as e:
            logger.error(f"Failed to download competition data via kagglehub: {e}")
            raise

    async def push_notebook(self, notebook_id: str, code: str, competition_id: Optional[str] = None, model_sources: Optional[List[str]] = None) -> dict:
        """Push a notebook to Kaggle with the EXACT metadata required for Blackwell G4."""
        logger.info(f"Pushing notebook: {notebook_id}")

        temp_dir = Path(f"data/temp_notebook_{notebook_id}")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Parse or wrap the code
        try:
            nb_json = json.loads(code)
        except ValueError:
            # Wrap raw python script into notebook format
            nb_json = {
                "cells": [{"cell_type": "code", "execution_count": None, "metadata": {"trusted": True}, "outputs": [], "source": [code]}],
                "metadata": {
                    "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                    "language_info": {"name": "python", "version": "3.12.12"}
                },
                "nbformat": 4, "nbformat_minor": 4
            }

        # Inject internal metadata
        nb_json["metadata"]["kaggle"] = {
            "accelerator": "nvidiaRtxPro6000",
            "isInternetEnabled": True,
            "language": "python",
            "sourceType": "notebook",
            "isGpuEnabled": True
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
            "dataset_sources": [],
            "competition_sources": ["nvidia-nemotron-model-reasoning-challenge"],
            "kernel_sources": ["ryanholbrook/nvidia-utility-script"],
            "model_sources": ["metric/nemotron-3-nano-30b-a3b-bf16/transformers/default/1"],
            "docker_image": "gcr.io/kaggle-private-byod/python@sha256:9fa0da194fad2241d3f01a80581cbecbd3a258b4d1b695e2cbbbc62a0fd205ac",
            "machine_shape": "NvidiaRtxPro6000"
        }

        metadata_path = temp_dir / "kernel-metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        try:
            logger.info(f"Executing Kaggle CLI push for {notebook_id} with machine_shape=NvidiaRtxPro6000...")
            cmd = ["kaggle", "kernels", "push", "-p", str(temp_dir)]
            env = os.environ.copy()
            if self.username:
                env["KAGGLE_USERNAME"] = self.username

            result = subprocess.run(cmd, capture_output=True, text=True, env=env)

            if result.returncode != 0:
                logger.error(f"Kaggle push failed: {result.stderr}")
                raise Exception(f"Kaggle push failed: {result.stderr}")

            url = f"https://www.kaggle.com/{self.username}/{notebook_id}"
            logger.info(f"Success! URL: {url}")
            return {"status": "complete", "url": url}
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
        try:
            # We don't want to download files, just get the log
            output_result = self.api.kernels_output(kernel_slug, path=f"data/logs_{notebook_id}")
            return getattr(output_result, "log", "No logs found.")
        except Exception as e:
            logger.error(f"Failed to get notebook logs: {e}")
            return str(e)

    async def submit_to_competition(self, adapter_path: Path, message: str, competition_id: str) -> dict:
        """Submit results to a Kaggle competition."""
        logger.info(f"Submitting {adapter_path} to competition: {competition_id}")
        try:
            self.api.competition_submit(str(adapter_path), message, competition_id)
            return {"status": "submitted"}
        except Exception as e:
            logger.error(f"Failed to submit to Kaggle: {e}")
            raise
