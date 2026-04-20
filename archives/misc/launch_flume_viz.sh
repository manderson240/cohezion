#!/bin/bash
# FLUME Journey Visualizer Launcher

echo "🚀 Launching FLUME Journey Visualizer..."
echo "🌀 Visualizing AI Agent Thought Trajectories Through 256D Latent Space"
echo ""

# Check if we're in the right directory
if [ ! -f "flume_journey_visualizer.py" ]; then
    echo "❌ Error: flume_journey_visualizer.py not found!"
    echo "Please run this script from the directory containing the visualizer."
    exit 1
fi

# Install requirements if needed
echo "📦 Checking dependencies..."
pip install -r requirements_flume_viz.txt --quiet

# Launch the Streamlit app
echo "🌐 Starting web application..."
echo "📱 The app will open in your default browser"
echo "🔗 Or manually navigate to: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the application"
echo ""

streamlit run flume_journey_visualizer.py --server.port=8501 --server.address=localhost