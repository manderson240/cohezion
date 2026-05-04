#!/bin/bash
# E89.b — Parallel Lemonade embedding lane on port 13308.
#
# Why parallel: the running Lemonade @ 13307 is in use by overnight_evo_loop.py
# (1700+ cycles, do not disturb). This script brings up a SECOND llama-server
# on port 13308 with --embeddings flag, dedicated to Lemonade-style embeddings.
#
# Required env: LLAMA_SERVER_BIN=path/to/llama-server (Lemonade's bundled binary)
#               LEMONADE_MODELS_DIR=path/to/.lemonade/models
#
# Default: tries the typical Lemonade install paths.
#
# Usage:
#   ./scripts/start_lemonade_embed_lane.sh [port]   # default port 13308

set -euo pipefail
PORT="${1:-13308}"
HOST="127.0.0.1"

# Find a small embedding-capable GGUF model in the user's model store.
# Order: prefer purpose-built embedders, fall back to small generative models
# that can produce embeddings via mean-pooling.
CANDIDATES=(
  "$HOME/.cache/lm-studio/models/nomic-ai/nomic-embed-text-v1.5-GGUF/nomic-embed-text-v1.5.Q4_K_M.gguf"
  "$HOME/.cache/lm-studio/models/mxbai-embed-large/mxbai-embed-large-v1.Q4_K_M.gguf"
  "$HOME/.cache/llama/Qwen3-0.6B-Q4_K_M.gguf"
)

MODEL=""
for c in "${CANDIDATES[@]}"; do
  if [ -f "$c" ]; then
    MODEL="$c"; break
  fi
done

if [ -z "$MODEL" ]; then
  echo "[lemonade-embed] no candidate GGUF found in default paths."
  echo "[lemonade-embed] Status: skipping startup."
  echo "[lemonade-embed] Action: ollama pull nomic-embed-text:v1.5 already provides this lane."
  echo "[lemonade-embed] To enable Lemonade-side embeddings, download a GGUF and re-run."
  exit 0
fi

# Find llama-server binary
LLAMA_BIN="${LLAMA_SERVER_BIN:-}"
if [ -z "$LLAMA_BIN" ]; then
  for cand in "$HOME/.lemonade/bin/llama-server" \
             "/opt/lemonade/llama-server" \
             "$(command -v llama-server 2>/dev/null || true)"; do
    if [ -x "$cand" ]; then LLAMA_BIN="$cand"; break; fi
  done
fi

if [ -z "$LLAMA_BIN" ] || [ ! -x "$LLAMA_BIN" ]; then
  echo "[lemonade-embed] llama-server binary not found."
  echo "[lemonade-embed] Set LLAMA_SERVER_BIN env or install Lemonade with bundled binary."
  exit 0
fi

LOG="/tmp/lemonade-embed-${PORT}.log"
echo "[lemonade-embed] Starting on ${HOST}:${PORT} with ${MODEL}"
echo "[lemonade-embed] Log: $LOG"
nohup "$LLAMA_BIN" \
  --host "$HOST" --port "$PORT" \
  --model "$MODEL" \
  --embeddings \
  --pooling mean \
  --ctx-size 4096 \
  > "$LOG" 2>&1 &

PID=$!
echo "[lemonade-embed] PID=$PID  port=$PORT"
sleep 2
if curl -sf "http://${HOST}:${PORT}/v1/models" > /dev/null 2>&1; then
  echo "[lemonade-embed] /v1/models responsive ✓"
else
  echo "[lemonade-embed] not yet responsive; tail $LOG to check progress"
fi
