#!/bin/bash
# Dedupe the next-moves list in HANDOFF-2026-06-10-prompt-only.txt
# (we introduced a duplicate "image_tier into CosmoNarrator" entry)
set -e
F="/home/mike-anderson/vaults/cohezion-vault/learnings/HANDOFF-2026-06-10-prompt-only.txt"
python3 - <<'PY'
path = "/home/mike-anderson/vaults/cohezion-vault/learnings/HANDOFF-2026-06-10-prompt-only.txt"
with open(path) as f:
    txt = f.read()

# The current list has:
#   1. image_tier into CosmoNarrator  (from our replacement)
#   2. stt_tier into Telegram
#   3. image_tier into CosmoNarrator  (duplicated from the original list)
#   4. /image <prompt> into Telegram
#   5. VIDEO SPIKE
#   6. self_retrospective
# We need to renumber and drop the duplicate. Build a clean list.

old_list = """NEXT MOVES (priority order, all unblocked):
1. Wire image_tier into CosmoNarrator: for each STAGE_NARRATIONS
   entry, render a 768x768 SD-Turbo image. Persist (text, audio,
   image) tuple to SurrealDB. ~30 lines in audio/narrator.py.
2. Wire stt_tier into the Telegram bot: when a user sends a voice
   message, transcribe locally, feed text to complexity-aware chat
   path, reply with TTS (kokoro) so the user gets an audio reply.
   ~40 lines in telegram_bot.py.
3. Wire image_tier into CosmoNarrator: for each STAGE_NARRATIONS
   entry, render a 768x768 SD-Turbo image. Persist (text, audio,
   image) tuple to SurrealDB. ~30 lines in audio/narrator.py.
4. Wire /image <prompt> into the Telegram bot: parse the /image
   command, call image_tier, send PNG via Telegram sendPhoto.
   ~50 lines in telegram_bot.py.
5. VIDEO SPIKE: lemonade has NO video recipe. Smallest local T2V
   candidates for 35GB unified memory: Wan2.1-T2V-1.3B (best fit),
   LTX-Video 2B, AnimateDiff, CogVideoX-2B. Need a GGUF build for
   llamacpp recipe, OR a comfyui workflow. Document the path in
   VIDEO_RESEARCH-2026-06-10.md and persist to vault.
6. Close the self_retrospective loop: compose fractal_metrics +
   stt_tier + tts_tier + cosmo_narrator + image_tier so cohezion
   narrates its own end-of-session retrospective with full
   audio+image+text round-trip."""

new_list = """NEXT MOVES (priority order, all unblocked):
1. Wire stt_tier into the Telegram bot: when a user sends a voice
   message, transcribe locally, feed text to complexity-aware chat
   path, reply with TTS (kokoro) so the user gets an audio reply.
   ~40 lines in telegram_bot.py.
2. Wire image_tier into CosmoNarrator: for each STAGE_NARRATIONS
   entry, render a 768x768 SD-Turbo image. Persist (text, audio,
   image) tuple to SurrealDB. ~30 lines in audio/narrator.py.
3. Wire /image <prompt> into the Telegram bot: parse the /image
   command, call image_tier, send PNG via Telegram sendPhoto.
   ~50 lines in telegram_bot.py.
4. VIDEO SPIKE: lemonade has NO video recipe. Smallest local T2V
   candidates for 35GB unified memory: Wan2.1-T2V-1.3B (best fit),
   LTX-Video 2B, AnimateDiff, CogVideoX-2B. Need a GGUF build for
   llamacpp recipe, OR a comfyui workflow. Document the path in
   VIDEO_RESEARCH-2026-06-10.md and persist to vault.
5. Close the self_retrospective loop: compose fractal_metrics +
   stt_tier + tts_tier + cosmo_narrator + image_tier so cohezion
   narrates its own end-of-session retrospective with full
   audio+image+text round-trip.
6. Port-13305 audit: sweep src/cohezion/ for any new references to
   per-lane ports (8002-8013, 13306-13309) and replace with 13305 or
   the documented per-recipe port (8008 for TTS, :8003 for FLM only).
   User flagged 2026-06-10."""

if old_list in txt:
    txt = txt.replace(old_list, new_list)
    with open(path, "w") as f:
        f.write(txt)
    print("deduped + bumped #1 to stt_tier (telegram)")
else:
    print("OLD LIST not found -- listing current next-moves block")
    idx = txt.find("NEXT MOVES")
    if idx >= 0:
        print(txt[idx:idx+2000])
PY
echo "---"
sed -n '/NEXT MOVES/,/SKILLS TO LOAD/p' "$F" | head -30
