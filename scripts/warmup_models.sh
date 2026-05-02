#!/bin/bash
# Warm up Gemma 4 models for Symphony Max benchmarks
echo "🔥 Starting detached model warmup..."

# Warm up E4B (NPU/GPU)
ollama run gemma4:e4b "warmup" > /dev/null 2>&1 &
echo "Loding gemma4:e4b..."

# Warm up 26B (GPU)
ollama run gemma4:26b "warmup" > /dev/null 2>&1 &
echo "Loading gemma4:26b..."

# Warm up 31B-Cloud (Cloud)
ollama run gemma4:31b-cloud "warmup" > /dev/null 2>&1 &
echo "Loading gemma4:31b-cloud..."

echo "🚀 All warmup requests sent. Check 'ollama ps' to verify residency."
