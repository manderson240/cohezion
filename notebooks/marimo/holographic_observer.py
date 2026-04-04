import marimo

__generated_with = "0.1.0"
app = marimo.App()


@app.cell
def __():
    import marimo as mo
    import asyncio
    import matplotlib.pyplot as plt
    import numpy as np
    import base64
    from io import BytesIO
    from PIL import Image
    from cohezion.agents.ecoresilience_agent import EcoResilienceAgent
    
    # Initialize Agent
    try:
        agent = EcoResilienceAgent(model_name="gemma4")
    except Exception as e:
        agent = None
        error_msg = f"Failed to initialize agent: {e}"
        
    return mo, asyncio, plt, np, base64, BytesIO, Image, agent, error_msg, EcoResilienceAgent


@app.cell
def __(mo):
    mo.md(
        """
        # 🌿 The Holographic TEK Observer
        ### Gemma 4 Good Hackathon Entry | Powered by Cohezion
        
        Welcome to the **Multimodal Digital Twin**. This interactive dashboard uses **Gemma 4 (31B)** 
        running entirely on local UMA hardware (AMD Framework 16) to synthesize Traditional Ecological 
        Knowledge (TEK) with Unified Physics.
        
        **Instructions:** Upload an image of an ecosystem, and Gemma 4 will map its current 
        health to a 12D physical manifold, propose a TEK-based intervention, and use a 
        **Causal-JEPA World Model** to simulate its future trajectory toward 0.5 Coherence (Systemic Balance).
        """
    )
    return


@app.cell
def __(mo):
    # UI Elements
    scenario_input = mo.ui.text_area(label="Additional Scenario Details (Optional)", placeholder="e.g., Recent wildfires in the area...")
    image_upload = mo.ui.file(label="Upload Ecosystem Image (PNG/JPG)", filetypes=[".png", ".jpg", ".jpeg"])
    analyze_btn = mo.ui.button(label="Simulate Holographic Trajectory", kind="primary")
    
    mo.vstack([
        scenario_input,
        image_upload,
        analyze_btn
    ])
    return scenario_input, image_upload, analyze_btn


@app.cell
def __(mo, asyncio, plt, np, base64, BytesIO, Image, agent, error_msg, analyze_btn, scenario_input, image_upload):
    if not analyze_btn.value:
        mo.stop()
        
    if not agent:
        mo.md(f"### ❌ Initialization Error\n{error_msg}\n*(Ensure Ollama is running and gemma4 is pulled)*")
        mo.stop()

    mo.md("### 🔄 Analyzing & Simulating...")
    
    scenario = scenario_input.value or "Analyzing uploaded ecosystem image for systemic distress and TEK intervention opportunities."
    
    image_b64 = None
    if image_upload.value:
        try:
            # Get the first uploaded file
            file_data = image_upload.value[0]
            # Ollama expects standard base64 strings for images
            image_b64 = base64.b64encode(file_data.contents).decode('utf-8')
        except Exception as e:
            mo.md(f"**Image processing error:** {e}")
            mo.stop()
            
    # Mocking async run in marimo
    try:
        # In a real marimo notebook with an active loop, we might use asyncio.run
        # or await directly if top-level await is enabled.
        # For this prototype execution, we use asyncio.run
        result = asyncio.run(agent.analyze_and_simulate(scenario, trajectory_id="demo-1", image_base64=image_b64))
    except Exception as e:
        mo.md(f"### ❌ Simulation Error\n{e}\n*(Check Ollama/Gemma4 backend)*")
        mo.stop()
        
    # Build results display
    
    # Plot Trajectory
    trajectory = np.array(result["trajectory"])
    fig, ax = plt.subplots(figsize=(10, 5))
    steps = range(len(trajectory))
    
    # Plot a few key 12D dimensions
    ax.plot(steps, trajectory[:, 0], label="Dim 0 (Energy)", color="red", alpha=0.7)
    ax.plot(steps, trajectory[:, 1], label="Dim 1 (Hydrology)", color="blue", alpha=0.7)
    ax.plot(steps, trajectory[:, 4], label="Dim 4 (Fuel/Carbon)", color="green", alpha=0.7)
    ax.plot(steps, trajectory[:, 10], label="Dim 10 (Mycelial Resonance)", color="purple", alpha=0.7)
    
    # Target 0.5 Coherence Line
    ax.axhline(y=0.5, color='black', linestyle='--', label="0.5 Coherence (HIHO Stability)")
    
    ax.set_title("12D Ecosystem Trajectory (JEPA Prediction)")
    ax.set_xlabel("Simulation Steps (Future)")
    ax.set_ylabel("Normalized State Vector")
    ax.legend()
    
    status_icon = "✅" if result["healing"] else "⚠️"
    status_text = "Ecosystem stabilizing towards 0.5 Coherence." if result["healing"] else "Intervention insufficient; system drifting from stability."
    
    # Output layout
    mo.vstack([
        mo.md("## 🧠 Gemma 4 Sovereign Analysis (31B Thinking Mode)"),
        mo.md(f"*(Gemma's raw, unedited reasoning process is displayed below, demonstrating deep conceptual synthesis before outputting a conclusion.)*"),
        mo.callout(
            mo.md(f"```text\n{result['analysis']}\n```"),
            kind="info"
        ),
        mo.md(f"### 🌿 Proposed TEK Intervention\n**Action Decided by Agent:** `{result['intervention_identified']}`"),
        mo.md(f"### 🔮 JEPA World Model Prediction\n**Coherence Shift:** {result['coherence_shift']:.4f} {status_icon} *{status_text}*"),
        mo.as_html(fig)
    ])
    
    return result, fig, steps, trajectory, status_icon, status_text


if __name__ == "__main__":
    app.run()
