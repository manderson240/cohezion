"""Audio file handling utilities."""

import base64
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def generate_audio_filename(extension: str = "wav") -> str:
    """Generate a unique audio filename."""
    return f"kyutai-audio-{uuid.uuid4()}.{extension}"


def ensure_audio_dir(base_dir: str = "/tmp") -> str:
    """Ensure audio output directory exists."""
    audio_dir = os.path.join(base_dir, "kyutai-audio")
    os.makedirs(audio_dir, exist_ok=True)
    return audio_dir


def save_audio_file(audio_data: bytes, format_ext: str = "wav") -> str:
    """Save audio data to file and return path.

    Args:
        audio_data: Raw audio bytes
        format_ext: File extension (wav, mp3, ogg)

    Returns:
        Full path to saved audio file
    """
    audio_dir = ensure_audio_dir()
    filename = generate_audio_filename(format_ext)
    filepath = os.path.join(audio_dir, filename)

    with open(filepath, "wb") as f:
        f.write(audio_data)

    logger.debug(f"Saved audio to {filepath}")
    return filepath


def audio_to_base64(filepath: str) -> str:
    """Convert audio file to base64 string."""
    with open(filepath, "rb") as f:
        audio_data = f.read()
    return base64.b64encode(audio_data).decode("utf-8")


def get_audio_duration_ms(audio_data: bytes, sample_rate: int = 24000) -> int:
    """Estimate audio duration from sample count.

    Args:
        audio_data: Raw audio bytes
        sample_rate: Samples per second (default: 24000)

    Returns:
        Duration in milliseconds
    """
    # Assuming 16-bit audio (2 bytes per sample)
    num_samples = len(audio_data) // 2
    duration_seconds = num_samples / sample_rate
    return int(duration_seconds * 1000)


def cleanup_old_audio_files(max_age_hours: int = 24, base_dir: str = "/tmp") -> int:
    """Remove audio files older than max_age_hours.

    Args:
        max_age_hours: Maximum age in hours
        base_dir: Base directory for audio files

    Returns:
        Number of files removed
    """
    import time

    audio_dir = os.path.join(base_dir, "kyutai-audio")
    if not os.path.exists(audio_dir):
        return 0

    removed_count = 0
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600

    for filename in os.listdir(audio_dir):
        filepath = os.path.join(audio_dir, filename)
        if not os.path.isfile(filepath):
            continue

        file_age = current_time - os.path.getmtime(filepath)
        if file_age > max_age_seconds:
            try:
                os.remove(filepath)
                removed_count += 1
                logger.debug(f"Removed old audio file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to remove {filepath}: {e}")

    return removed_count
