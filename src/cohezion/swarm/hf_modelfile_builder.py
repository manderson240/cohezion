# ruff: noqa: SIM117  # nested with for clarity
"""Automated HuggingFace GGUF downloading and custom Ollama instance creation."""

import argparse
import asyncio
import logging
import shutil
import subprocess
from pathlib import Path

import aiofiles
import httpx


logger = logging.getLogger(__name__)

# Resolve ollama executable at module load to avoid S607 partial-path warnings.
_OLLAMA = shutil.which("ollama") or "/usr/local/bin/ollama"


class HFModelfileBuilder:
    """Automated HuggingFace GGUF downloading and custom Ollama instance creation."""

    def __init__(self, download_dir: str = "./data/models"):
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

    async def download_gguf(self, repo_id: str, filename: str) -> Path:
        """Download a GGUF file from HuggingFace to the local models directory."""
        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        dest_path = self.download_dir / filename

        if dest_path.exists():
            logger.info(f"File {filename} already exists at {dest_path}")
            return dest_path

        logger.info(f"Downloading {filename} from {url}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(follow_redirects=True, timeout=120.0) as client:
                    async with client.stream("GET", url) as response:
                        response.raise_for_status()
                        async with aiofiles.open(dest_path, "wb") as f:
                            async for chunk in response.aiter_bytes():
                                await f.write(chunk)
                break  # Success, exit retry loop
            except (httpx.RuntimeError, httpx.RequestError) as e:
                logger.error(f"HTTPX error on attempt {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:
                    raise
                import asyncio

                await asyncio.sleep(2)

        logger.info(f"Downloaded {filename} to {dest_path}")
        return dest_path

    def build_modelfile(self, model_name: str, gguf_path: Path, system_prompt: str = "") -> Path:
        """Generate an Ollama Modelfile mapping to a specific file."""
        modelfile_content = f"FROM {gguf_path.absolute()}\n"
        if system_prompt:
            modelfile_content += f'SYSTEM """\n{system_prompt}\n"""\n'

        safe_name = model_name.replace(":", "_")
        modelfile_path = self.download_dir / f"Modelfile.{safe_name}"
        modelfile_path.write_text(modelfile_content)

        logger.info(f"Created Modelfile at {modelfile_path}")
        return modelfile_path

    def create_ollama_model(self, model_name: str, modelfile_path: Path) -> None:
        """Issue an `ollama create` command pointing to the newly built Modelfile."""
        logger.info(f"Creating Ollama model {model_name} from {modelfile_path}")
        result = subprocess.run(  # noqa: S603 - model_name and modelfile_path are internally controlled
            [_OLLAMA, "create", model_name, "-f", str(modelfile_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error(f"Failed to create model: {result.stderr}")
            raise RuntimeError(f"Ollama create failed: {result.stderr}")

        logger.info(f"Successfully created Ollama model: {model_name}")


async def main() -> None:
    """CLI Entrypoint for building an Ollama model from HuggingFace."""
    parser = argparse.ArgumentParser(
        description="Build custom Ollama models from HuggingFace GGUFs"
    )
    parser.add_argument(
        "--repo",
        type=str,
        required=True,
        help="HuggingFace repo ID (e.g. Qwen/Qwen2.5-Coder-7B-Instruct-GGUF)",
    )
    parser.add_argument(
        "--filename",
        type=str,
        required=True,
        help="GGUF filename (e.g. qwen2.5-coder-7b-instruct-q4_k_m.gguf)",
    )
    parser.add_argument(
        "--name",
        type=str,
        required=True,
        help="Ollama model name (e.g. qwen2.5-coder-custom:7b)",
    )
    parser.add_argument("--system", type=str, default="", help="Custom system prompt")

    args = parser.parse_args()

    builder = HFModelfileBuilder()
    gguf_path = await builder.download_gguf(args.repo, args.filename)
    modelfile_path = builder.build_modelfile(args.name, gguf_path, args.system)
    builder.create_ollama_model(args.name, modelfile_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
