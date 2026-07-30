#!/usr/bin/env python3
"""Organize Music Library Script.

Scans /mnt/wd_mybook/downloads for music album folders containing audio files (.flac, .mp3, .m4a, .wav),
parses Artist / Album structure, and moves them into clean /mnt/wd_mybook/media/music/Artist/Album folders.
"""

from __future__ import annotations

import os
import re
import shutil
from pathlib import Path

DOWNLOADS_DIR = Path("/mnt/wd_mybook/downloads")
TARGET_MUSIC_DIR = Path("/mnt/wd_mybook/media/music")

AUDIO_EXTENSIONS = {".flac", ".mp3", ".m4a", ".wav", ".aac", ".ogg", ".opus"}


def parse_artist_album(folder_name: str) -> tuple[str, str]:
    """Parse 'Artist - Album (Year) ...' string into (artist, album)."""
    clean_name = re.sub(r"\[.*?\]|\(.*?FLAC.*?\)|FLAC 88|TEAM EICHBAUM|EICHBAUM|Sc4r3cr0w|Beats⭐", "", folder_name).strip()
    clean_name = re.sub(r"\s+", " ", clean_name)

    if " - " in clean_name:
        parts = clean_name.split(" - ", 1)
        artist = parts[0].strip()
        album = parts[1].strip()
    elif " x " in clean_name:
        parts = clean_name.split(" x ", 1)
        artist = parts[0].strip()
        album = parts[1].strip()
    else:
        artist = "Various Artists"
        album = clean_name.strip()

    return artist, album or folder_name


def main():
    print("==========================================================================")
    print("  COHEZION AUTOMATED MUSIC LIBRARY ORGANIZER")
    print(f"  Source: {DOWNLOADS_DIR}")
    print(f"  Target: {TARGET_MUSIC_DIR}")
    print("==========================================================================\n")

    if not DOWNLOADS_DIR.exists():
        print(f"Error: Downloads directory {DOWNLOADS_DIR} does not exist.")
        return

    TARGET_MUSIC_DIR.mkdir(parents=True, exist_ok=True)

    moved_count = 0
    skipped_count = 0

    for item in DOWNLOADS_DIR.iterdir():
        if not item.is_dir():
            continue

        # Check if directory contains audio files
        audio_files = [f for f in item.rglob("*") if f.suffix.lower() in AUDIO_EXTENSIONS]
        if not audio_files:
            print(f"· Skipping non-music directory: {item.name}")
            skipped_count += 1
            continue

        artist, album = parse_artist_album(item.name)
        target_artist_dir = TARGET_MUSIC_DIR / artist
        target_album_dir = target_artist_dir / item.name

        print(f"➜ Moving: '{item.name}'")
        print(f"   └─ Target: {target_album_dir}")

        target_artist_dir.mkdir(parents=True, exist_ok=True)

        try:
            shutil.move(str(item), str(target_album_dir))
            moved_count += 1
            print("   ✓ Done.")
        except Exception as exc:
            print(f"   x Failed to move: {exc}")

    print("\n==========================================================================")
    print(f"  SUMMARY: Organized {moved_count} music albums into {TARGET_MUSIC_DIR}")
    print(f"           Skipped {skipped_count} non-music items")
    print("==========================================================================")


if __name__ == "__main__":
    main()
