#!/bin/bash
# Update the HANDOFF prompt-only file to reflect STT tier as SHIPPED
# and bump next-move #1 to the image_tier-into-narrator work.
set -e
F="/home/mike-anderson/vaults/cohezion-vault/learnings/HANDOFF-2026-06-10-prompt-only.txt"
python3 - <<'PY'
path = "/home/mike-anderson/vaults/cohezion-vault/learnings/HANDOFF-2026-06-10-prompt-only.txt"
with open(path) as f:
    txt = f.read()

# Replace the STT "unblocked, no pytest" line + add new entry
old1 = "5. STT unblocked: Whisper-Large-v3-Turbo reachable via :13305/v1/audio/\n   transcriptions (multipart, model=Whisper-Large-v3-Turbo). 1/1 live,\n   NO pytest yet. Next step: write src/cohezion/inference/stt_tier.py\n   mirroring tts_tier.py."
new1 = "5. STT TIER SHIPPED 2026-06-10: src/cohezion/inference/stt_tier.py\n   (NEW) — DirectLemonadeSTTTier on OmniRouter :13305/v1/audio/\n   transcriptions (multipart/form-data, OpenAI-spec). 19/19 pytest\n   (10 logic + 4 mocked + 5 live) in 3.65s. Live TTS->STT round-trip:\n   125KB kokoro MP3 (6.26s of speech) transcribed verbatim in 461ms\n   on iGPU. Sister of tts_tier/image_tier; mirrors build_stt_tier()."

old2 = """9. SurrealDB learnings records: kokoro_tts_validation_2026_06_10,
   cosmo_narrator_kokoro_wire_2026_06_10, multimodal_gap_analysis_
   2026_06_10, telegram_local_first_routing_2026_06_10, image_tier_
   validation_2026_06_10, plus auto-written lemonade_recipe_audit_*
   per cron run"""
new2 = """9. SurrealDB learnings records: kokoro_tts_validation_2026_06_10,
   cosmo_narrator_kokoro_wire_2026_06_10, multimodal_gap_analysis_
   2026_06_10, telegram_local_first_routing_2026_06_10, image_tier_
   validation_2026_06_10, stt_tier_validation_2026_06_10, plus
   auto-written lemonade_recipe_audit_* per cron run"""

old3 = """NEXT MOVES (priority order, all unblocked):
1. WRITE stt_tier.py mirroring tts_tier.py. Whisper STT already
   works via :13305/v1/audio/transcriptions. ~80 lines: typed
   SttRequest/SttResult, async transcribe() method, is_alive() probe.
   Then tests/inference/test_stt_tier.py (live + mocked). Closes the
   inbound voice loop (currently missing).
2. Wire stt_tier into the Telegram bot: when a user sends a voice"""
new3 = """NEXT MOVES (priority order, all unblocked):
1. Wire image_tier into CosmoNarrator: for each STAGE_NARRATIONS
   entry, render a 768x768 SD-Turbo image. Persist (text, audio,
   image) tuple to SurrealDB. ~30 lines in audio/narrator.py.
2. Wire stt_tier into the Telegram bot: when a user sends a voice"""

if old1 in txt:
    txt = txt.replace(old1, new1)
    print("STT line replaced")
else:
    print("OLD1 not found")

if old2 in txt:
    txt = txt.replace(old2, new2)
    print("SurrealDB records list updated")
else:
    print("OLD2 not found")

if old3 in txt:
    txt = txt.replace(old3, new3)
    print("Next-moves list updated")
else:
    print("OLD3 not found")

with open(path, "w") as f:
    f.write(txt)
print(f"file now: {len(txt)} chars / {txt.count(chr(10))+1} lines")
PY
echo "---"
wc -l "$F"
echo "---"
grep -n "STT TIER SHIPPED\|stt_tier_validation\|image_tier into Cosmo" "$F"
