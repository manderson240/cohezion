"""
FLUME Journey Visualizer - Next-Gen Webapp for Showcasing Agent Journeys Through FLUME
A Streamlit application that visualizes how AI agents navigate the FLUME latent space
(thought autoencoder) as they journey through simulated universes.
"""

import json

# Import FLUME components
import sys
import time
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


sys.path.append("src")

from cohezion.api.services.flume import (
    compute_coherence,
    get_vae,
)
from cohezion.flume.dataset import SyntheticFlumeDataset
from cohezion.flume.mnm import ManifoldManager
from cohezion.flume.navigator import FlumeNavigator
from cohezion.flume.predictor import TrajectoryPredictor
from cohezion.flume.training import FlumeVAETrainer, TrainConfig
from cohezion.swarm.hiho_vector_engine import HihoVectorEngine


# Page configuration
st.set_page_config(
    page_title="FLUME Journey Visualizer",
    page_icon="🌀",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
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
    .stButton > button {
        width: 100%;
        border-radius: 20px;
        border: none;
        background: linear-gradient(45deg, #667eea, #764ba2);
        color: white;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }
</style>
""",
    unsafe_allow_html=True,
)


def initialize_flume():
    """Initialize FLUME components with caching"""
    if "flume_initialized" not in st.session_state:
        with st.spinner("Initializing FLUME VAE..."):
            try:
                # Try to load existing VAE
                vae = get_vae()
                st.session_state.vae = vae
                st.session_state.flume_ready = True
                st.success("✅ FLUME VAE loaded successfully!")
            except Exception as e:
                st.warning(f"⚠️ No pre-trained VAE found: {e}")
                st.info("🔄 Training a new FLUME VAE for demonstration...")

                # Train a quick VAE for demo
                config = TrainConfig(
                    z_dim=256,
                    batch_size=32,
                    epochs=5,  # Quick demo training
                    lr=1e-3,
                    kl_weight=0.1,
                    coherence_weight=0.05,
                )

                dataset = SyntheticFlumeDataset(n_samples=1000, z_dim=256)
                trainer = FlumeVAETrainer(config)

                progress_bar = st.progress(0)
                status_text = st.empty()

                # Simple training loop with progress
                for epoch in range(config.epochs):
                    metrics = trainer.train(dataset=dataset, epochs=1)
                    progress_bar.progress((epoch + 1) / config.epochs)
                    status_text.text(
                        f"Epoch {epoch + 1}/{config.epochs} - Loss: {metrics[-1]['total']:.4f}"
                    )

                st.session_state.vae = trainer
                st.session_state.flume_ready = True
                st.success("✅ FLUME VAE trained and ready!")

            # Initialize other components
            st.session_state.navigator = FlumeNavigator(
                encoder=st.session_state.vae.encoder
                if hasattr(st.session_state.vae, "encoder")
                else st.session_state.vae,
                predictor=TrajectoryPredictor(z_dim=256),
                manifold_mgr=ManifoldManager(z_dim=256),
            )
            st.session_state.hiho = HihoVectorEngine()
            st.session_state.manifold_mgr = ManifoldManager(z_dim=256)
            st.session_state.predictor = TrajectoryPredictor(z_dim=256)

            st.session_state.flume_initialized = True


def encode_text_to_latent(text: str) -> tuple[np.ndarray, float]:
    """Convert text to latent vector using FLUME"""
    # Simple text-to-vector conversion for demo (in reality would use tokenizer)
    # Create a deterministic vector based on text hash
    np.random.seed(hash(text) % 2**32)
    vector = np.random.randn(256).astype(np.float32)
    vector = vector / np.linalg.norm(vector)  # Normalize

    # Use actual FLUME if available
    if st.session_state.flume_ready and hasattr(st.session_state, "vae"):
        try:
            import torch

            # For demo, we'll use a simple approach
            # In reality, this would go through the tokenizer and actual VAE
            vector_tensor = torch.tensor([vector], dtype=torch.float32)

            vae = st.session_state.vae
            if hasattr(vae, "encoder"):  # It's a trainer
                encoder = vae.encoder
                mu_head = vae.mu_head
                logvar_head = vae.logvar_head
            else:  # It's the actual VAE model
                encoder = vae.encoder
                mu_head = vae.mu_head
                logvar_head = vae.logvar_head

            with torch.no_grad():
                h = encoder(vector_tensor)
                mu = mu_head(h)
                log_var = logvar_head(h)
                latent = mu.squeeze(0).numpy()

            coherence = compute_coherence(latent.tolist())
            return latent, coherence
        except (ValueError, RuntimeError):
            pass

    # Fallback: simulate FLUME encoding
    # Apply some structure to make it look more like a real latent space
    t = np.linspace(0, 4 * np.pi, 256)
    latent = 0.3 * np.sin(t) + 0.2 * np.sin(7 * t) * np.exp(-t / 20) + 0.1 * np.random.randn(256)
    latent = latent / np.linalg.norm(latent)

    coherence = compute_coherence(latent.tolist())
    return latent, coherence


def decode_latent_to_text(latent: np.ndarray) -> tuple[str, float]:
    """Convert latent vector back to text concept (simplified)"""
    # In reality, this would go through the VAE decoder and tokenizer
    # For demo, we'll create conceptual labels based on latent space regions

    coherence = compute_coherence(latent.tolist())

    # Analyze latent vector to generate meaningful concept
    latent_mean = np.mean(latent)
    latent_std = np.std(latent)
    latent_skew = np.mean(((latent - latent_mean) / latent_std) ** 3)

    # Map latent properties to conceptual domains
    if latent_mean > 0.5:
        domain = "Quantum"
    elif latent_mean > 0:
        domain = "Biological"
    elif latent_mean > -0.5:
        domain = "Logical"
    else:
        domain = "Mathematical"

    if latent_std > 0.8:
        complexity = "Complex"
    elif latent_std > 0.4:
        complexity = "Moderate"
    else:
        complexity = "Simple"

    if latent_skew > 0.5:
        dynamism = "Dynamic"
    elif latent_skew > -0.5:
        dynamism = "Stable"
    else:
        dynamism = "Static"

    concept = f"{complexity} {dynamism} {domain} Thought"
    return concept, coherence


def create_latent_space_3d_plot(
    latents: list[np.ndarray], labels: list[str], coherences: list[float]
) -> go.Figure:
    """Create 3D visualization of latent space journey"""
    if len(latents) < 1:
        return go.figure()

    # Reduce to 3D for visualization using PCA-like approach
    latents_array = np.array(latents)

    # Simple 3D projection: use first 3 principal components approximation
    if latents_array.shape[1] >= 3:
        # Use dimensions that show most variance
        variances = np.var(latents_array, axis=0)
        top_3_dims = np.argsort(variances)[-3:][::-1]
        points_3d = latents_array[:, top_3_dims]
    else:
        # Pad or truncate to 3D
        if latents_array.shape[1] >= 3:
            points_3d = latents_array[:, :3]
        else:
            padding = np.zeros((latents_array.shape[0], 3 - latents_array.shape[1]))
            points_3d = np.hstack([latents_array, padding])

    # Normalize for better visualization
    points_3d = (points_3d - np.mean(points_3d, axis=0)) / (np.std(points_3d, axis=0) + 1e-8)

    fig = go.Figure()

    # Add trajectory line
    fig.add_trace(
        go.Scatter3d(
            x=points_3d[:, 0],
            y=points_3d[:, 1],
            z=points_3d[:, 2],
            mode="lines+markers",
            line=dict(color="royalblue", width=4),
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
            name="Agent Journey",
        )
    )

    # Add start and end markers
    if len(points_3d) >= 1:
        fig.add_trace(
            go.Scatter3d(
                x=[points_3d[0, 0]],
                y=[points_3d[0, 1]],
                z=[points_3d[0, 2]],
                mode="markers",
                marker=dict(size=12, color="green", symbol="circle"),
                name="Start",
                hoverinfo="text",
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
                hoverinfo="text",
                hovertext=f"End: {labels[-1]}<br>Coherence: {coherences[-1]:.3f}",
            )
        )

    fig.update_layout(
        title="FLUME Latent Space Journey - 3D Projection",
        scene=dict(
            xaxis_title="Latent Dimension 1 (PC1)",
            yaxis_title="Latent Dimension 2 (PC2)",
            zaxis_title="Latent Dimension 3 (PC3)",
            camera=dict(eye=dict(x=1.5, y=1.5, z=1.5)),
        ),
        height=600,
        margin=dict(l=0, r=0, t=50, b=0),
    )

    return fig


def create_coherence_timeline(coherences: list[float], labels: list[str]) -> go.Figure:
    """Create coherence over time visualization"""
    fig = go.Figure()

    steps = list(range(len(coherences)))

    fig.add_trace(
        go.Scatter(
            x=steps,
            y=coherences,
            mode="lines+markers",
            line=dict(color="#667eea", width=3),
            marker=dict(size=8, color="#764ba2"),
            fill="tonexty",
            fillcolor="rgba(102, 126, 234, 0.1)",
            name="HIHO Coherence",
            hovertemplate="Step: %{x}<br>Coherence: %{y:.3f}<br>%{text}<extra></extra>",
            text=labels,
        )
    )

    # Add HIHO band (0.4-0.6)
    fig.add_hrect(
        y0=0.4,
        y1=0.6,
        fillcolor="green",
        opacity=0.1,
        annotation_text="HIHO Stability Band",
        annotation_position="top left",
    )

    # Add target line at 0.5
    fig.add_hline(
        y=0.5,
        line_dash="dash",
        line_color="gold",
        annotation_text="HIHO Target (0.5)",
        annotation_position="bottom right",
    )

    fig.update_layout(
        title="Agent Coherence Over Journey",
        xaxis_title="Journey Step",
        yaxis_title="HIHO Coherence",
        yaxis=dict(range=[0, 1]),
        height=300,
        showlegend=True,
    )

    return fig


def create_latent_heatmap(latent: np.ndarray) -> go.Figure:
    """Create heatmap of latent vector dimensions"""
    # Reshape for better visualization (16x16 grid)
    latent_2d = latent.reshape(16, 16)

    fig = go.Figure(
        data=go.Heatmap(
            z=latent_2d,
            colorscale="RdBu",
            zmid=0,
            showscale=True,
            colorbar=dict(title="Activation"),
        )
    )

    fig.update_layout(
        title="FLUME Thought Vector Heatmap (256D → 16×16)",
        height=400,
        xaxis_title="Latent Dimension",
        yaxis_title="Latent Dimension",
    )

    return fig


def main():
    # Header
    st.markdown('<h1 class="main-header">🌀 FLUME Journey Visualizer</h1>', unsafe_allow_html=True)
    st.markdown("### Visualizing AI Agent Thought Trajectories Through the 256D Latent Space")
    st.markdown("---")

    # Initialize FLUME
    initialize_flume()

    # Sidebar controls
    st.sidebar.header("🎯 Journey Controls")

    # Journey type selection
    journey_type = st.sidebar.selectbox(
        "Journey Type",
        ["Concept Exploration", "Problem Solving", "Creative Interpolation", "Random Walk"],
        help="Select the type of agent journey to visualize",
    )

    # Journey length
    journey_length = st.sidebar.slider("Journey Length (steps)", 3, 10, 5)

    # Initialize journey state
    if "journey_data" not in st.session_state or st.sidebar.button("🔄 Generate New Journey"):
        st.session_state.journey_data = generate_journey(journey_type, journey_length)
        st.session_state.journey_type = journey_type
        st.session_state.journey_length = journey_length

    # Display journey data
    journey_data = st.session_state.journey_data
    latents = journey_data["latents"]
    labels = journey_data["labels"]
    coherences = journey_data["coherences"]
    concepts = journey_data["concepts"]

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "🚀 Journey Visualization",
            "🔬 Latent Space Analysis",
            "📊 Metrics & Coherence",
            "💾 Export & Share",
        ]
    )

    with tab1:
        st.header("Agent Journey Through FLUME Latent Space")

        # 3D Visualization
        st.subheader("3D Latent Space Trajectory")
        fig_3d = create_latent_space_3d_plot(latents, labels, coherences)
        st.plotly_chart(fig_3d, use_container_width=True)

        # Journey steps
        st.subheader("Journey Narrative")
        for i, (label, concept, coherence) in enumerate(zip(labels, concepts, coherences)):
            coherence_class = "high" if coherence > 0.6 else "medium" if coherence > 0.4 else "low"
            st.markdown(
                f"""
            <div class="journey-step">
                <strong>Step {i + 1}: {label}</strong><br>
                <em>{concept}</em><br>
                <span style="float: right; 
                           background: {"#4CAF50" if coherence > 0.6 else "#FF9800" if coherence > 0.4 else "#F44336"}; 
                           color: white; 
                           padding: 2px 8px; 
                           border-radius: 12px; 
                           font-size: 0.8em;">
                    Coherence: {coherence:.3f}
                </span>
            </div>
            """,
                unsafe_allow_html=True,
            )

    with tab2:
        st.header("Deep Dive into FLUME Thought Vectors")

        col1, col2 = st.columns([1, 1])

        with col1:
            st.subheader("Latent Space Heatmap")
            # Show heatmap of current or selected point
            selected_step = st.selectbox(
                "Select Journey Step to Analyze",
                range(len(latents)),
                format_func=lambda x: f"Step {x + 1}: {labels[x]}",
            )
            selected_latent = latents[selected_step]
            fig_heatmap = create_latent_heatmap(selected_latent)
            st.plotly_chart(fig_heatmap, use_container_width=True)

        with col2:
            st.subheader("Vector Statistics")
            stats_df = pd.DataFrame(
                {
                    "Metric": ["Mean", "Std", "Min", "Max", "L1 Norm", "L2 Norm"],
                    "Value": [
                        f"{np.mean(selected_latent):.4f}",
                        f"{np.std(selected_latent):.4f}",
                        f"{np.min(selected_latent):.4f}",
                        f"{np.max(selected_latent):.4f}",
                        f"{np.sum(np.abs(selected_latent)):.4f}",
                        f"{np.linalg.norm(selected_latent):.4f}",
                    ],
                }
            )
            st.dataframe(stats_df, hide_index=True, use_container_width=True)

            # Show coherence breakdown
            st.subheader("Coherence Analysis")
            coherence_breakdown = analyze_coherence_breakdown(selected_latent)
            st.json(coherence_breakdown)

        # Interpolation demo
        st.subheader("Concept Interpolation in Latent Space")
        if len(latents) >= 2:
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                start_idx = st.selectbox(
                    "Start Concept",
                    range(len(latents)),
                    format_func=lambda x: f"Step {x + 1}: {labels[x]}",
                )
            with col2:
                end_idx = st.selectbox(
                    "End Concept",
                    range(len(latents)),
                    format_func=lambda x: f"Step {x + 1}: {labels[x]}",
                    index=min(1, len(latents) - 1),
                )
            with col3:
                ratio = st.slider("Interpolation Ratio", 0.0, 1.0, 0.5, 0.1)

            if start_idx != end_idx:
                # Perform interpolation
                start_latent = latents[start_idx]
                end_latent = latents[end_idx]
                interpolated = (1 - ratio) * start_latent + ratio * end_latent
                interp_label, interp_coherence = decode_latent_to_text(interpolated)

                st.info(f"""
                **Interpolating between:**
                - Start: {labels[start_idx]} 
                - End: {labels[end_idx]}
                - Ratio: {ratio:.1f} ({1 - ratio:.0%} A + {ratio:.0%} B)
                
                **Result:**
                - Concept: {interp_label}
                - Coherence: {interp_coherence:.3f}
                """)

                # Show interpolated vector heatmap
                fig_interp = create_latent_heatmap(interpolated)
                st.plotly_chart(fig_interp, use_container_width=True)

    with tab3:
        st.header("Journey Metrics & Coherence Analysis")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>{len(latents)}</h3>
                <p>Journey Steps</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col2:
            avg_coherence = np.mean(coherences)
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>{avg_coherence:.3f}</h3>
                <p>Avg Coherence</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col3:
            hiho_compliance = (
                np.sum((np.array(coherences) >= 0.4) & (np.array(coherences) <= 0.6))
                / len(coherences)
                * 100
            )
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>{hiho_compliance:.0f}%</h3>
                <p>HIHO Band Compliance</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col4:
            coherence_std = np.std(coherences)
            st.markdown(
                f"""
            <div class="metric-card">
                <h3>{coherence_std:.3f}</h3>
                <p>Coherence Stability</p>
            </div>
            """,
                unsafe_allow_html=True,
            )

        # Coherence timeline
        st.subheader("Coherence Over Time")
        fig_coherence = create_coherence_timeline(coherences, labels)
        st.plotly_chart(fig_coherence, use_container_width=True)

        # Latent space exploration
        st.subheader("Latent Space Exploration")
        exploration_col1, exploration_col2 = st.columns(2)

        with exploration_col1:
            st.write("**Dimensional Analysis**")
            dim_stats = []
            latents_array = np.array(latents)
            for i in range(min(10, latents_array.shape[1])):  # Show first 10 dims
                dim_stats.append(
                    {
                        "Dimension": f"Z[{i:03d}]",
                        "Mean": f"{np.mean(latents_array[:, i]):.4f}",
                        "Std": f"{np.std(latents_array[:, i]):.4f}",
                        "Range": f"{np.max(latents_array[:, i]) - np.min(latents_array[:, i]):.4f}",
                    }
                )
            st.dataframe(pd.DataFrame(dim_stats), hide_index=True, use_container_width=True)

        with exploration_col2:
            st.write("**Journey Statistics**")
            journey_stats = [
                {"Metric": "Path Length", "Value": f"{calculate_path_length(latents):.3f}"},
                {"Metric": "Straightness", "Value": f"{calculate_straightness(latents):.3f}"},
                {"Metric": "Max Deviation", "Value": f"{calculate_max_deviation(latents):.3f}"},
                {"Metric": "Coord Changes", "Value": f"{count_coordinate_changes(latents)}"},
                {
                    "Metric": "Exploration Radius",
                    "Value": f"{calculate_exploration_radius(latents):.3f}",
                },
            ]
            st.dataframe(pd.DataFrame(journey_stats), hide_index=True, use_container_width=True)

    with tab4:
        st.header("Export, Share & Research")

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Export Journey Data")

            # Prepare export data
            export_data = {
                "journey_type": st.session_state.get("journey_type", "Unknown"),
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "steps": len(latents),
                "journey": [
                    {
                        "step": i + 1,
                        "label": labels[i],
                        "concept": concepts[i],
                        "coherence": float(coherences[i]),
                        "latent_vector": latents[i].tolist()
                        if isinstance(latents[i], np.ndarray)
                        else latents[i],
                    }
                    for i in range(len(latents))
                ],
                "metrics": {
                    "avg_coherence": float(np.mean(coherences)),
                    "hiho_compliance": float(
                        np.sum((np.array(coherences) >= 0.4) & (np.array(coherences) <= 0.6))
                        / len(coherences)
                        * 100
                    ),
                    "coherence_std": float(np.std(coherences)),
                    "path_length": float(calculate_path_length(latents)),
                    "straightness": float(calculate_straightness(latents)),
                },
            }

            # JSON export
            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                label="💾 Download Journey Data (JSON)",
                data=json_str,
                file_name=f"flume_journey_{int(time.time())}.json",
                mime="application/json",
            )

            # CSV export for latent vectors
            if len(latents) > 0:
                latent_df = pd.DataFrame(
                    [
                        {"step": i + 1, "label": labels[i]}
                        | {
                            f"z_{j:03d}": latents[i][j] for j in range(min(10, len(latents[i])))
                        }  # First 10 dims
                        for i in range(len(latents))
                    ]
                )
                csv_str = latent_df.to_csv(index=False)
                st.download_button(
                    label="📊 Download Latent Vectors (CSV)",
                    data=csv_str,
                    file_name=f"flume_latents_{int(time.time())}.csv",
                    mime="text/csv",
                )

        with col2:
            st.subheader("Research Insights")

            # Generate insights based on journey
            insights = generate_journey_insights(latents, labels, coherences, concepts)

            for insight in insights:
                st.info(insight)

            st.subheader("Share Your Journey")
            st.markdown("""
            **To share this FLUME journey visualization:**
            1. Export the journey data above
            2. Share with researchers or team members
            3. They can import it into their own FLUME visualizer
            4. Collaborate on interpreting agent thought trajectories
            
            **Citation:**
            ```
            FLUME Journey Visualizer
            Created for demonstrating agent navigation through 
            256D latent thought space in simulated universes.
            Based on the Cohezion framework for agentic AI.
            ```
            """)

        # Real-time demo
        st.subheader("🔴 Live FLUME Demo")
        if st.button("▶️ Start Live Journey Simulation"):
            placeholder = st.empty()
            progress_bar = st.progress(0)

            # Simulate a live journey
            live_steps = 8
            live_latents = []
            live_labels = []
            live_coherences = []

            for i in range(live_steps):
                # Generate next step in journey
                if i == 0:
                    # Start with random concept
                    text_seed = np.random.choice(
                        [
                            "quantum consciousness",
                            "biological intelligence",
                            "mathematical beauty",
                            "logical reasoning",
                            "creative emergence",
                        ]
                    )
                else:
                    # Continue from previous step with small perturbation
                    if live_latents:
                        prev_latent = live_latents[-1]
                        noise = np.random.randn(256) * 0.1
                        text_seed = (
                            prev_latent + noise
                        ).tolist()  # This would be decoded in reality
                    else:
                        text_seed = np.random.randn(256).tolist()

                # Process through FLUME (simplified for demo)
                latent, coherence = encode_text_to_latent(str(text_seed))
                label, concept = decode_latent_to_text(latent)

                live_latents.append(latent)
                live_labels.append(label or f"Step {i + 1}")
                live_coherences.append(coherence)

                # Update visualization
                with placeholder.container():
                    fig_live = create_latent_space_3d_plot(
                        live_latents, live_labels, live_coherences
                    )
                    st.plotly_chart(fig_live, use_container_width=True)

                    # Show latest step
                    st.markdown(
                        f"""
                    <div class="journey-step">
                        <strong>Live Step {i + 1}: {label or f"Step {i + 1}"}</strong><br>
                        <em>{concept or "Processing..."}</em><br>
                        <span style="float: right; 
                                   background: {"#4CAF50" if coherence > 0.6 else "#FF9800" if coherence > 0.4 else "#F44336"}; 
                                   color: white; 
                                   padding: 2px 8px; 
                                   border-radius: 12px; 
                                   font-size: 0.8em;">
                            Coherence: {coherence:.3f}
                        </span>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                progress_bar.progress((i + 1) / live_steps)
                time.sleep(0.8)  # Pause for effect

            st.success("🎉 Live journey simulation complete!")
            st.balloons()


def generate_journey(journey_type: str, length: int) -> dict[str, Any]:
    """Generate a journey based on type"""
    latents = []
    labels = []
    coherences = []
    concepts = []

    # Define journey themes
    themes = {
        "Concept Exploration": [
            "Quantum Consciousness",
            "Biological Intelligence",
            "Mathematical Beauty",
            "Logical Reasoning",
            "Creative Emergence",
            "Ethical Decision Making",
            "Strategic Planning",
            "Scientific Discovery",
        ],
        "Problem Solving": [
            "Problem Identification",
            "Root Cause Analysis",
            "Solution Brainstorming",
            "Option Evaluation",
            "Risk Assessment",
            "Implementation Planning",
            "Resource Allocation",
            "Success Metrics Definition",
        ],
        "Creative Interpolation": [
            "Abstract Concept A",
            "Transition State",
            "Hybrid Concept",
            "Novel Synthesis",
            "Innovative Application",
            "Practical Implementation",
            "Real World Impact",
            "Future Vision",
        ],
        "Random Walk": [f"Exploration Vector {i + 1}" for i in range(length)],
    }

    theme_list = themes.get(journey_type, themes["Concept Exploration"])

    for i in range(length):
        # Get theme for this step
        if journey_type == "Random Walk":
            label = theme_list[i] if i < len(theme_list) else f"Random Step {i + 1}"
        else:
            label = theme_list[i % len(theme_list)]

        # Generate latent vector based on journey type
        if journey_type == "Concept Exploration":
            # Semantically meaningful progression
            base_vector = np.random.randn(256) * 0.5
            # Add theme-specific modulation
            theme_phase = (i / len(theme_list)) * 2 * np.pi
            modulation = np.sin(np.arange(256) * 0.1 + theme_phase) * 0.3
            latent = base_vector + modulation
            latent = latent / np.linalg.norm(latent)

        elif journey_type == "Problem Solving":
            # Structured, goal-oriented progression
            progress = i / (length - 1) if length > 1 else 0.5
            # Start scattered, end focused
            focus_factor = 1.0 - progress * 0.7  # More focused as we progress
            latent = np.random.randn(256) * focus_factor
            # Add directional component toward solution
            solution_vector = np.ones(256) * 0.3  # Simple solution direction
            latent += solution_vector * progress * 0.5
            latent = latent / np.linalg.norm(latent)

        elif journey_type == "Creative Interpolation":
            # Smooth transitions between concepts
            if i == 0:
                # Start point
                latent = np.random.randn(256) * 0.8
            elif i == length - 1:
                # End point - different from start
                latent = np.random.randn(256) * 0.8 + np.array(
                    [1.0] * 128 + [-1.0] * 128
                )  # Opposite corners
            else:
                # Interpolate between start and end
                start_vec = np.random.randn(256) * 0.8
                end_vec = np.random.randn(256) * 0.8 + np.array([1.0] * 128 + [-1.0] * 128)
                ratio = i / (length - 1)
                latent = (1 - ratio) * start_vec + ratio * end_vec
                # Add creative noise
                latent += (
                    np.random.randn(256) * 0.2 * (1 - abs(ratio - 0.5) * 2)
                )  # Most creative in middle
            latent = latent / np.linalg.norm(latent)

        else:  # Random Walk
            # Pure random walk with small steps
            if i == 0:
                latent = np.random.randn(256)
            else:
                prev_latent = latents[-1]
                step = np.random.randn(256) * 0.3  # Small step
                latent = prev_latent + step
            latent = latent / np.linalg.norm(latent)

        # Ensure it's normalized
        latent = latent / (np.linalg.norm(latent) + 1e-8)

        latents.append(latent)
        labels.append(label)

        # Calculate coherence
        coherence = compute_coherence(latent.tolist())
        coherences.append(coherence)

        # Generate conceptual label
        concept, _ = decode_latent_to_text(latent)
        concepts.append(concept)

    return {"latents": latents, "labels": labels, "coherences": coherences, "concepts": concepts}


def analyze_coherence_breakdown(latent: np.ndarray) -> dict[str, Any]:
    """Analyze coherence by latent space regions"""
    # Split latent vector into chunks (simulating the 12D axiomatic breakdown)
    chunk_size = len(latent) // 12
    chunks = []

    for i in range(12):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < 11 else len(latent)
        chunk = latent[start:end]
        chunks.append(
            {
                f"chunk_{i:02d}": {
                    "mean": float(np.mean(chunk)),
                    "std": float(np.std(chunk)),
                    "energy": float(np.sum(chunk**2)),
                }
            }
        )

    # Flatten for easier reading
    flat_breakdown = {}
    for chunk_dict in chunks:
        for key, value in chunk_dict.items():
            flat_breakdown[key] = value

    return flat_breakdown


def calculate_path_length(latents: list[np.ndarray]) -> float:
    """Calculate total path length in latent space"""
    if len(latents) < 2:
        return 0.0

    total_length = 0.0
    for i in range(1, len(latents)):
        diff = latents[i] - latents[i - 1]
        length = np.linalg.norm(diff)
        total_length += length

    return total_length


def calculate_straightness(latents: list[np.ndarray]) -> float:
    """Calculate how straight the path is (ratio of direct distance to path length)"""
    if len(latents) < 2:
        return 1.0

    start = latents[0]
    end = latents[-1]
    direct_distance = np.linalg.norm(end - start)
    path_length = calculate_path_length(latents)

    if path_length == 0:
        return 1.0

    return direct_distance / path_length


def calculate_max_deviation(latents: list[np.ndarray]) -> float:
    """Calculate maximum deviation from the straight line path"""
    if len(latents) < 3:
        return 0.0

    start = latents[0]
    end = latents[-1]
    path_vector = end - start
    path_length = np.linalg.norm(path_vector)

    if path_length < 1e-8:
        return 0.0

    path_unit = path_vector / path_length
    max_dev = 0.0

    for point in latents:
        # Vector from start to point
        to_point = point - start
        # Project onto path
        projection_length = np.dot(to_point, path_unit)
        projection_point = start + projection_length * path_unit
        # Perpendicular distance
        perpendicular = point - projection_point
        deviation = np.linalg.norm(perpendicular)
        max_dev = max(max_dev, deviation)

    return max_dev


def count_coordinate_changes(latents: list[np.ndarray]) -> int:
    """Count significant coordinate direction changes"""
    if len(latents) < 3:
        return 0

    changes = 0
    prev_direction = None

    for i in range(1, len(latents)):
        direction = latents[i] - latents[i - 1]
        direction_norm = np.linalg.norm(direction)

        if direction_norm > 1e-8:
            direction_unit = direction / direction_norm

            if prev_direction is not None:
                # Calculate angle change
                dot_product = np.dot(prev_direction, direction_unit)
                # Clamp to valid range for arccos
                dot_product = np.clip(dot_product, -1.0, 1.0)
                angle_change = np.arccos(dot_product)

                # Count as change if > 30 degrees
                if angle_change > np.pi / 6:  # 30 degrees
                    changes += 1

            prev_direction = direction_unit

    return changes


def calculate_exploration_radius(latents: list[np.ndarray]) -> float:
    """Calculate how far the journey explores from the starting point"""
    if len(latents) < 2:
        return 0.0

    start = latents[0]
    max_distance = 0.0

    for point in latents:
        distance = np.linalg.norm(point - start)
        max_distance = max(max_distance, distance)

    return max_distance


def generate_journey_insights(
    latents: list[np.ndarray], labels: list[str], coherences: list[float], concepts: list[str]
) -> list[str]:
    """Generate research insights from the journey"""
    insights = []

    coherences_array = np.array(coherences)

    # Coherence insights
    avg_coherence = np.mean(coherences_array)
    if avg_coherence > 0.7:
        insights.append(
            "🎯 **High Coherence Journey**: Agent maintained strong alignment with HIHO stability throughout"
        )
    elif avg_coherence > 0.5:
        insights.append(
            "⚖️ **Moderate Coherence**: Agent showed reasonable stability with some exploration"
        )
    else:
        insights.append(
            "🔍 **Exploratory Journey**: Agent ventured into diverse regions of thought space"
        )

    # HIHO band compliance
    hiho_count = np.sum((coherences_array >= 0.4) & (coherences_array <= 0.6))
    hiho_percentage = hiho_count / len(coherences_array) * 100

    if hiho_percentage > 80:
        insights.append(
            f"✅ **Excellent HIHO Compliance**: {hiho_percentage:.0f}% of steps within stability band"
        )
    elif hiho_percentage > 50:
        insights.append(
            f"⚠️ **Moderate HIHO Compliance**: {hiho_percentage:.0f}% of steps within stability band"
        )
    else:
        insights.append(
            f"🔬 **Low HIHO Compliance**: Only {hiho_percentage:.0f}% within stability band - high exploration mode"
        )

    # Coherence variance
    coherence_std = np.std(coherences_array)
    if coherence_std < 0.1:
        insights.append("📏 **Stable Coherence**: Consistent thought process throughout journey")
    elif coherence_std < 0.2:
        insights.append(
            "📊 **Reasonable Variability**: Natural exploration with consistent returns to stability"
        )
    else:
        insights.append(
            "📈 **High Variability**: Dynamic exploration with significant coherence fluctuations"
        )

    # Path characteristics
    path_length = calculate_path_length(latents)
    straightness = calculate_straightness(latents)

    if straightness > 0.8:
        insights.append(
            f"🎯 **Direct Path**: Highly goal-oriented traversal (straightness: {straightness:.2f})"
        )
    elif straightness > 0.5:
        insights.append(
            f"➡️ **Moderately Direct**: Balanced exploration and progression (straightness: {straightness:.2f})"
        )
    else:
        insights.append(
            f"🌀 **Highly Exploratory**: Circuitous path with significant exploration (straightness: {straightness:.2f})"
        )

    # Exploration radius
    radius = calculate_exploration_radius(latents)
    if radius > 2.0:
        insights.append(
            f"🌌 **Wide Exploration**: Agent explored distant regions of thought space (radius: {radius:.2f})"
        )
    elif radius > 1.0:
        insights.append(
            f"🔭 **Moderate Exploration**: Good coverage of latent space neighborhoods (radius: {radius:.2f})"
        )
    else:
        insights.append(
            f"🔍 **Focused Exploration**: Concentrated exploration near starting point (radius: {radius:.2f})"
        )

    # Concept diversity insight
    unique_concepts = len(set(concepts))
    concept_diversity = unique_concepts / len(concepts) if concepts else 0

    if concept_diversity > 0.7:
        insights.append(
            f"💡 **High Concept Diversity**: {unique_concepts} distinct conceptual regions explored"
        )
    elif concept_diversity > 0.4:
        insights.append("🔄 **Moderate Concept Recycling**: Some revisiting of conceptual areas")
    else:
        insights.append(
            f"🔁 **Low Concept Diversity**: Focused exploration of few conceptual regions ({unique_concepts} unique)"
        )

    return insights


# Run the app
if __name__ == "__main__":
    main()
