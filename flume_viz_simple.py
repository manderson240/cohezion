#!/usr/bin/env python3
"""
Simple FLUME Journey Visualizer
Works with existing Cohezion environment
"""

import sys


# Add the Cohezion environment to Python path
cohezion_venv_path = "/home/mike-anderson/dev/cohezion/.venv/lib/python3.13/site-packages"
if cohezion_venv_path not in sys.path:
    sys.path.insert(0, cohezion_venv_path)

# Also add the src directory
src_path = "/home/mike-anderson/dev/cohezion/src"
if src_path not in sys.path:
    sys.path.insert(0, src_path)

import json
import time

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# Try to import torch from the Cohezion environment
try:
    import torch

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    st.warning("⚠️ Torch not available - using numpy approximations")

# Import FLUME components from Cohezion
try:
    sys.path.insert(0, "/home/mike-anderson/dev/cohezion")
    from cohezion.api.services.flume import compute_coherence, get_vae
    from cohezion.flume.vae import FlumeVAEConfig

    COHEZION_AVAILABLE = True
except ImportError as e:
    COHEZION_AVAILABLE = False
    st.error(f"❌ Could not import Cohezion components: {e}")
    st.stop()

# Page configuration
st.set_page_config(
    page_title="FLUME Journey Visualizer",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
    }
    .journey-step {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-left: 4px solid #667eea;
        background-color: #f8f9ff;
    }
</style>
""",
    unsafe_allow_html=True,
)


def initialize_simple_flume():
    """Initialize FLUME with fallback options"""
    if "flume_initialized" not in st.session_state:
        with st.spinner("Initializing FLUME components..."):
            try:
                # Try to get the actual VAE from Cohezion
                vae = get_vae()
                st.session_state.vae = vae
                st.session_state.using_real_vae = True
                st.success("✅ Using real FLUME VAE from Cohezion!")
            except Exception as e:
                st.warning(f"⚠️ Could not load real VAE: {e}")
                st.info("🔄 Using simulated FLUME for demonstration")
                st.session_state.using_real_vae = False
                st.session_state.vae = None

            st.session_state.flume_initialized = True


def encode_text_simple(text: str) -> tuple[np.ndarray, float]:
    """Simple text encoding - uses real VAE if available, otherwise simulates"""
    if st.session_state.get("using_real_vea", False) and st.session_state.vae and TORCH_AVAILABLE:
        try:
            # Use real FLUME VAE
            import torch

            # Create a simple vector from text hash for demo
            np.random.seed(hash(text) % 2**32)
            vector = np.random.randn(256).astype(np.float32)
            vector = vector / np.linalg.norm(vector)

            # Try to encode with real VAE
            vector_tensor = torch.tensor([vector], dtype=torch.float32)

            # This is simplified - in reality would go through tokenizer
            vae = st.session_state.vae
            if hasattr(vae, "encoder"):
                with torch.no_grad():
                    h = vae.encoder(vector_tensor)
                    mu = vae.mu_head(h)
                    log_var = vae.logvar_head(h)
                    latent = mu.squeeze(0).numpy()

                coherence = compute_coherence(latent.tolist())
                return latent, coherence
        except Exception as e:
            st.info(f"Falling back to simulation: {e}")

    # Simulation fallback
    np.random.seed(hash(text) % 2**32)
    latent = np.random.randn(256).astype(np.float32)
    latent = latent / np.linalg.norm(latent)

    # Add some structure to make it interesting
    t = np.linspace(0, 4 * np.pi, 256)
    latent += 0.3 * np.sin(t) + 0.1 * np.sin(7 * t) * np.exp(-t / 20)
    latent = latent / np.linalg.norm(latent)

    coherence = compute_coherence(latent.tolist())
    return latent, coherence


def decode_latent_simple(latent: np.ndarray) -> tuple[str, float]:
    """Simple latent decoding"""
    coherence = compute_coherence(latent.tolist())

    # Generate conceptual label based on latent properties
    latent_mean = np.mean(latent)
    latent_std = np.std(latent)

    # Map to concepts
    if latent_mean > 0.3:
        domain = "Quantum/AI"
    elif latent_mean > 0:
        domain = "Creative/Design"
    elif latent_mean > -0.3:
        domain = "Analytical/Logical"
    else:
        domain = "Mathematical/Structural"

    if latent_std > 0.6:
        complexity = "Complex"
    elif latent_std > 0.3:
        complexity = "Moderate"
    else:
        complexity = "Simple/Focused"

    concept = f"{complexity} {domain} Pattern"
    return concept, coherence


def create_journey_3d(latents, labels, coherences):
    """Create 3D journey visualization"""
    if len(latents) == 0:
        return go.Figure()

    latents_array = np.array(latents)

    # Simple 3D projection
    if latents_array.shape[1] >= 3:
        # Use dimensions with highest variance
        variances = np.var(latents_array, axis=0)
        top_dims = np.argsort(variances)[-3:][::-1]
        points_3d = latents_array[:, top_dims]
    else:
        # Pad or truncate
        if latents_array.shape[1] >= 3:
            points_3d = latents_array[:, :3]
        else:
            padding = np.zeros((latents_array.shape[0], 3 - latents_array.shape[1]))
            points_3d = np.hstack([latents_array, padding])

    # Normalize
    if np.std(points_3d) > 0:
        points_3d = (points_3d - np.mean(points_3d, axis=0)) / (np.std(points_3d, axis=0) + 1e-8)

    fig = go.Figure()

    # Journey trajectory
    fig.add_trace(
        go.Scatter3d(
            x=points_3d[:, 0],
            y=points_3d[:, 1],
            z=points_3d[:, 2],
            mode="lines+markers",
            line=dict(color="#667eea", width=4),
            marker=dict(
                size=8,
                color=coherences,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="HIHO Coherence"),
                line=dict(width=1, color="DarkSlateGrey"),
            ),
            text=[
                f"Step {i}: {label}<br>Coherence: {coh:.3f}"
                for i, (label, coh) in enumerate(zip(labels, coherences))
            ],
            hoverinfo="text",
            name="Agent Journey Through FLUME",
        )
    )

    # Mark start and end
    if len(points_3d) >= 1:
        fig.add_trace(
            go.Scatter3d(
                x=[points_3d[0, 0]],
                y=[points_3d[0, 1]],
                z=[points_3d[0, 2]],
                mode="markers",
                marker=dict(size=12, color="green", symbol="circle"),
                name="Start",
                hovertext=f"Start: {labels[0]}<br>Coherence: {coherences[0]:.3f}",
            )
        )

    if len(points_3d) >= 2:
        fig.add_trace(
            go.Scatter3d(
                x=[points_3d[-1, 0]],
                y=[points_3d[-1, 1]],
                z=[points_3d[-1, 2]],
                mode="markers",
                marker=dict(size=12, color="red", symbol="diamond"),
                name="End",
                hovertext=f"End: {labels[-1]}<br>Coherence: {coherences[-1]:.3f}",
            )
        )

    fig.update_layout(
        title="🌀 Agent Journey Through FLUME 256D Latent Space (3D Projection)",
        scene=dict(
            xaxis_title="Latent Dimension 1",
            yaxis_title="Latent Dimension 2",
            zaxis_title="Latent Dimension 3",
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
    )

    return fig


def main():
    # Header
    st.markdown('<h1 class="main-header">🌀 FLUME Journey Visualizer</h1>', unsafe_allow_html=True)
    st.markdown("### Visualizing AI Agent Navigation Through 256D Latent Thought Space")
    st.markdown("*Built for demonstrating agent journeys in simulated universes*")
    st.markdown("---")

    # Initialize
    initialize_simple_flume()

    # Sidebar
    st.sidebar.header("🎮 Journey Controls")

    journey_type = st.sidebar.selectbox(
        "Journey Type",
        ["Concept Exploration", "Problem Solving", "Creative Synthesis", "Random Walk"],
        help="Type of agent cognitive journey to visualize",
    )

    journey_length = st.sidebar.slider("Journey Length", 3, 8, 5)

    if st.sidebar.button("🔄 Generate New Journey", type="primary"):
        if "journey_data" in st.session_state:
            del st.session_state.journey_data
        st.rerun()

    # Generate or get journey
    if "journey_data" not in st.session_state:
        # Define journey themes
        themes = {
            "Concept Exploration": [
                "Quantum Consciousness",
                "Biological Intelligence",
                "Mathematical Beauty",
                "Logical Reasoning",
                "Creative Emergence",
            ],
            "Problem Solving": [
                "Problem Identification",
                "Analysis",
                "Solution Design",
                "Implementation",
                "Validation",
            ],
            "Creative Synthesis": [
                "Abstract Idea",
                "Hybrid Concept",
                "Novel Approach",
                "Practical Application",
                "Real World Impact",
            ],
            "Random Walk": [f"Exploration Point {i + 1}" for i in range(journey_length)],
        }

        theme_list = themes.get(journey_type, themes["Concept Exploration"])
        latents = []
        labels = []
        coherences = []
        concepts = []

        for i in range(journey_length):
            # Select theme
            if journey_type == "Random Walk":
                label = theme_list[i]
            else:
                label = theme_list[i % len(theme_list)]

            # Generate latent based on journey type
            text_seed = f"{label} journey step {i + 1}"

            latent, coherence = encode_text_simple(text_seed)
            concept, _ = decode_latent_simple(latent)

            latents.append(latent)
            labels.append(label)
            coherences.append(coherence)
            concepts.append(concept)

        st.session_state.journey_data = {
            "latents": latents,
            "labels": labels,
            "coherences": coherences,
            "concepts": concepts,
            "journey_type": journey_type,
            "journey_length": journey_length,
        }

    # Get journey data
    data = st.session_state.journey_data
    latents = data["latents"]
    labels = data["labels"]
    coherences = data["coherences"]
    concepts = data["concepts"]

    # Main tabs
    tab1, tab2, tab3 = st.tabs(["🚀 3D Journey", "📊 Analysis", "💾 Export"])

    with tab1:
        st.subheader("Agent's Path Through FLUME Latent Space")

        # 3D Visualization
        fig_3d = create_journey_3d(latents, labels, coherences)
        st.plotly_chart(fig_3d, use_container_width=True)

        # Journey narrative
        st.subheader("📖 Journey Narrative")
        for i, (label, concept, coherence) in enumerate(zip(labels, concepts, coherences)):
            # Color based on coherence
            if coherence > 0.6:
                color = "#4CAF50"  # Green - high coherence
            elif coherence > 0.4:
                color = "#FF9800"  # Orange - medium
            else:
                color = "#F44336"  # Red - low coherence (exploration)

            st.markdown(
                f"""
            <div class="journey-step" style="border-left-color: {color};">
                <strong>Step {i + 1}: {label}</strong><br>
                <em>{concept}</em><br>
                <span style="float: right; 
                           background: {color}; 
                           color: white; 
                           padding: 2px 8px; 
                           border-radius: 12px; 
                           font-size: 0.9em;">
                    Coherence: {coherence:.3f}
                </span>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with tab2:
        st.subheader("📈 Journey Analytics")

        # Metrics row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            avg_coherence = np.mean(coherences)
            st.metric("Average Coherence", f"{avg_coherence:.3f}")

        with col2:
            hiho_count = sum(1 for c in coherences if 0.4 <= c <= 0.6)
            hiho_pct = (hiho_count / len(coherences)) * 100
            st.metric("HIHO Band Compliance", f"{hiho_pct:.0f}%")

        with col3:
            coherence_std = np.std(coherences)
            st.metric("Coherence Stability", f"{coherence_std:.3f}")

        with col4:
            # Calculate path length
            if len(latents) > 1:
                total_dist = 0
                for i in range(1, len(latents)):
                    dist = np.linalg.norm(np.array(latents[i]) - np.array(latents[i - 1]))
                    total_dist += dist
                st.metric("Path Length", f"{total_dist:.2f}")
            else:
                st.metric("Path Length", "0.00")

        # Coherence chart
        st.subheader("Coherence Over Journey Steps")
        chart_data = pd.DataFrame(
            {"Step": range(1, len(coherences) + 1), "Coherence": coherences, "Label": labels}
        )

        fig_line = px.line(
            chart_data,
            x="Step",
            y="Coherence",
            hover_data=["Label"],
            title="HIHO Coherence Throughout Agent Journey",
        )
        fig_line.add_hline(
            y=0.5, line_dash="dash", line_color="gold", annotation_text="HIHO Target (0.5)"
        )
        fig_line.add_hrect(
            y0=0.4, y1=0.6, fillcolor="green", opacity=0.1, annotation_text="HIHO Stability Band"
        )
        st.plotly_chart(fig_line, use_container_width=True)

        # Latent space statistics
        st.subheader("🔬 Latent Space Characteristics")
        if len(latents) > 0:
            latent_array = np.array(latents)

            stats_df = pd.DataFrame(
                {
                    "Property": [
                        "Mean Activation",
                        "Std Activation",
                        "Min Value",
                        "Max Value",
                        "L2 Norm (avg)",
                    ],
                    "Value": [
                        f"{np.mean(latent_array):.4f}",
                        f"{np.std(latent_array):.4f}",
                        f"{np.min(latent_array):.4f}",
                        f"{np.max(latent_array):.4f}",
                        f"{np.mean([np.linalg.norm(l) for l in latents]):.4f}",
                    ],
                }
            )
            st.dataframe(stats_df, hide_index=True, use_container_width=True)

    with tab3:
        st.subheader("💾 Export Journey Data")

        # Prepare export
        export_data = {
            "metadata": {
                "journey_type": data["journey_type"],
                "journey_length": data["journey_length"],
                "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "flume_source": "Real Cohezion VAE"
                if st.session_state.get("using_real_vea", False)
                else "Simulated",
            },
            "journey": [],
            "aggregate_metrics": {
                "avg_coherence": float(np.mean(coherences)),
                "hiho_compliance_pct": float(
                    (sum(1 for c in coherences if 0.4 <= c <= 0.6) / len(coherences)) * 100
                ),
                "coherence_std": float(np.std(coherences)),
                "path_length": float(
                    sum(
                        np.linalg.norm(np.array(latents[i]) - np.array(latents[i - 1]))
                        for i in range(1, len(latents))
                    )
                    if len(latents) > 1
                    else 0.0
                ),
            },
        }

        for i in range(len(latents)):
            export_data["journey"].append(
                {
                    "step_number": i + 1,
                    "label": labels[i],
                    "concept": concepts[i],
                    "coherence_float": float(coherences[i]),
                    "latent_vector_256d": latents[i].tolist()
                    if hasattr(latents[i], "tolist")
                    else list(latents[i]),
                }
            )

        # JSON Export
        json_str = json.dumps(export_data, indent=2)
        st.download_button(
            label="📥 Download Complete Journey Data (JSON)",
            data=json_data,
            file_name=f"flume_journey_{int(time.time())}.json",
            mime="application/json",
            help="Export the full journey including all 256D latent vectors",
        )

        # CSV Export ( simplified)
        if len(latents) > 0:
            # Create DataFrame with first 10 dimensions for readability
            latent_df_data = []
            for i, latent in enumerate(latents):
                row = {"step": i + 1, "label": labels[i], "concept": concepts[i]}
                # Add first 10 latent dimensions
                for j in range(min(10, len(latent))):
                    row[f"z_{j:03d}"] = float(latent[j])
                latent_df_data.append(row)

            latent_df = pd.DataFrame(latent_df_data)
            csv_data = latent_df.to_csv(index=False)

            st.download_button(
                label="📊 Download Latent Vectors (CSV - First 10 dims)",
                data=csv_data,
                file_name=f"flume_latents_{int(time.time())}.csv",
                mime="text/csv",
                help="Export latent vectors for external analysis (first 10 dimensions shown)",
            )

        st.subheader("📋 Journey Summary")
        st.json(
            {
                "Journey Type": data["journey_type"],
                "Total Steps": data["journey_length"],
                "Average Coherence": f"{np.mean(coherences):.3f}",
                "HIHO Compliance": f"{(sum(1 for c in coherences if 0.4 <= c <= 0.6) / len(coherences)) * 100:.0f}%",
                "FLUME Source": "Real Cohezion VAE"
                if st.session_state.get("using_real_vae", False)
                else "Simulated Demonstration",
            }
        )

        st.info("""
        💡 **How to Use This Visualization:**
        1. **Explore Different Journey Types** - Try Concept Exploration, Problem Solving, etc.
        2. **Adjust Journey Length** - See how longer journeys affect coherence patterns
        3. **Export & Share** - Download JSON/CSV to share with team members
        4. **Research Applications** - Use for studying agent cognition in latent spaces
        """)


if __name__ == "__main__":
    main()
