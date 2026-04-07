#!/bin/bash
# Simple FLUME Journey Visualizer Launcher
# Uses existing Cohezion environment

echo "🚀 Launching Simple FLUME Journey Visualizer..."
echo "🌀 Visualizing AI Agent Thought Trajectories Through 256D Latent Space"
echo ""

# Check if we're in the right directory
if [ ! -f "flume_viz_simple.py" ]; then
    echo "❌ Error: flume_viz_simple.py not found!"
    echo "Please run this script from the directory containing the visualizer."
    exit 1
fi

# Launch using the Cohezion Python environment
echo "🔧 Using Cohezion's Python environment..."
echo "🌐 Starting web application on http://localhost:8501"
echo ""

# Streamlit command with proper Python path
PYTHONPATH="/home/mike-anderson/dev/cohezion/.venv/lib/python3.11/site-packages:/home/mike-anderson/dev/cohezion/src:$PYTHONPATH" \
streamlit run flume_viz_simple.py --server.port=8501 --server.address=localhost