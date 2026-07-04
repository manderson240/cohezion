#!/bin/bash
# Update the HANDOFF-2026-06-10-multimodal-local.md verification snapshot
# to reflect the STT tier work completed in this session.
set -e
F="/home/mike-anderson/vaults/cohezion-vault/learnings/HANDOFF-2026-06-10-multimodal-local.md"

# Replace the audit count 47 -> 48 (in the snapshot block only, not the audit description)
python3 - <<'PY'
import re
path = "/home/mike-anderson/vaults/cohezion-vault/learnings/HANDOFF-2026-06-10-multimodal-local.md"
with open(path) as f:
    txt = f.read()

# Replace the verification snapshot block (from "## Verification snapshot" to "## Live catalog")
old_block = """## Verification snapshot at handoff time (2026-06-10)

  audit: 16 models / 4 recipes (llamacpp, kokoro, sd-cpp, whispercpp) /
         6 loaded / 47 consumer files / kokoro=alive
  tts:   6/6 live + 6/6 pytest
  image: 5/5 live + 11/11 pytest
  stt:   1/1 live (Whisper-Large-v3-Turbo via :13305/v1/audio/transcriptions,
         3.3s round-trip on a real TTS-generated MP3. NO pytest yet;
         the next-move is to write src/cohezion/inference/stt_tier.py
         mirroring tts_tier.py and add tests/inference/test_stt_tier.py)
  telegram: 29/29 pytest (15 new + 14 legacy)
  vault: 5 new learnings + N auto-audit records"""

new_block = """## Verification snapshot at handoff time (2026-06-10)

  audit: 16 models / 4 recipes (llamacpp, kokoro, sd-cpp, whispercpp) /
         6 loaded / 48 consumer files / kokoro=alive
  tts:   6/6 live + 6/6 pytest
  image: 5/5 live + 11/11 pytest
  stt:   19/19 pytest (10 logic + 4 mocked + 5 live) in 3.65s.
         Live TTS->STT round-trip: 125KB MP3 (kokoro am_michael, 6.26s
         of speech) transcribed verbatim in 461ms via verbose_json on
         iGPU. Whisper-Large-v3-Turbo via OmniRouter :13305 with
         multipart/form-data. See src/cohezion/inference/stt_tier.py.
  telegram: 29/29 pytest (15 new + 14 legacy)
  vault: 6 new learnings (incl. stt_tier_validation_2026_06_10) +
         N auto-audit records"""

if old_block in txt:
    new_txt = txt.replace(old_block, new_block)
    with open(path, "w") as f:
        f.write(new_txt)
    print("snapshot block replaced")
else:
    print("OLD BLOCK NOT FOUND -- snapshot may already be updated or handoff diverged")
    # Show what we have
    idx = txt.find("## Verification snapshot at handoff time")
    if idx >= 0:
        print("---existing block---")
        print(txt[idx:idx+800])
PY
echo "---"
grep -A 2 "audit: 16" "$F" | head -8
