# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "matplotlib",
#     "numpy",
#     "pandas",
# ]
# ///
"""
Universe Explorer: Interactive Layperson Physics Journey
=========================================================
Marimo reactive notebook with:
- Interactive universe selection
- Multi-audience presentation
- 12D physics state visualization
- AI Journey narration
- Q&A with guardrails
"""

import marimo


__generated_with = "0.10.17"
app = marimo.App(width="full")


@app.cell
def _():
    from datetime import datetime

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np

    return mo, plt, np, datetime


@app.cell
def _(mo):
    mo.md("""
    # 🌌 The Universe Explorer
    
    **Interactive Physics for Everyone**
    
    Explore cutting-edge physics discoveries explained so anyone can understand.
    Select a universe, choose your audience level, and dive in!
    
    > *"Nature figured out quantum computing billions of years before us."*
    """)
    return


@app.cell
def _(mo):
    # Universe selector
    universe = mo.ui.dropdown(
        options={
            "🎪 The Electron Party (EVOs)": "evo",
            "🧽 Fusion in Your Kitchen (LENR)": "lenr",
            "🌿 Plants Are Quantum Computers": "quantum_bio",
            "📡 Your Brain as Quantum Computer": "consciousness",
            "🤚 The Universe's Favorite Hand": "chirality",
            "🎀 Computers That Can't Make Mistakes": "topological",
            "💬 Cells Text With Light": "biophotonics",
            "🌊 Empty Space Is Full of Energy": "zpe",
        },
        value="🌿 Plants Are Quantum Computers",
        label="Select a Universe:",
    )

    audience = mo.ui.dropdown(
        options={
            "👶 Kids (8-12)": "kids",
            "🧑‍🎓 Teens (13-17)": "teens",
            "👨‍💼 Adults": "adults",
            "💼 Executives": "executives",
            "🔬 Scientists": "scientists",
            "🎨 Artists": "artists",
        },
        value="👨‍💼 Adults",
        label="Choose Audience:",
    )

    mo.hstack([universe, audience], justify="start", gap=2)
    return universe, audience


@app.cell
def _(mo, universe, audience):
    # Universe content database
    UNIVERSES = {
        "evo": {
            "title": "🎪 The Electron Party",
            "tagline": "What if electrons could team up instead of pushing each other away?",
            "analogy": "A crowded subway where everyone suddenly discovers they love the same song and starts dancing together.",
            "discovery": "Scientists found that under certain conditions, billions of electrons form stable clusters. This shouldn't be possible!",
            "implications": [
                "Batteries that never run out",
                "Engines without fuel",
                "Computers millions of times faster",
            ],
            "takeaway": "Electrons CAN work together, defying what we thought was possible.",
        },
        "lenr": {
            "title": "🧽 Fusion in Your Kitchen",
            "tagline": "Nuclear power without the scary reactor - just metal and water.",
            "analogy": "A magic sponge that doesn't just absorb water - it FUSES the molecules together, releasing energy like a tiny sun.",
            "discovery": "In certain metals loaded with hydrogen, fusion seems to happen at room temperature. The crystal structure acts as a catalyst.",
            "implications": [
                "Unlimited clean energy",
                "Cars running for years on water",
                "Zero carbon emissions",
            ],
            "takeaway": "We might be able to make nuclear power safe enough for your home.",
        },
        "quantum_bio": {
            "title": "🌿 Plants Are Quantum Computers",
            "tagline": "Leaves do calculations that would take our computers millions of years.",
            "analogy": "GPS that tests every possible route simultaneously and instantly picks the fastest.",
            "discovery": "Photosynthesis is 95% efficient. Our best solar panels are only 25%. Plants use quantum mechanics!",
            "implications": [
                "Solar panels 4x more efficient",
                "Medicines that work like magic",
                "Computers solving the unsolvable",
            ],
            "takeaway": "Nature figured out quantum computing billions of years before us.",
        },
        "consciousness": {
            "title": "📡 Is Your Brain a Quantum Computer?",
            "tagline": "Consciousness might come from Space itself.",
            "analogy": "Your TV doesn't create the picture - it receives signals. What if your brain is an antenna for thoughts from space-time?",
            "discovery": "Nobel laureate Penrose suggests consciousness involves quantum physics in tiny tubes inside brain cells.",
            "implications": [
                "Consciousness is fundamental to the universe",
                "AI might never be truly conscious",
                "Our minds could be connected",
            ],
            "takeaway": "Your awareness might be the universe experiencing itself.",
        },
        "chirality": {
            "title": "🤚 The Universe Has a Favorite Hand",
            "tagline": "Why life chose 'left' when it could have gone 'right.'",
            "analogy": "Imagine if everyone who ever lived only shook hands with their left hand. ALL life uses only one handedness!",
            "discovery": "When life began, it had a 50/50 choice. But all living things ended up using the same molecular handedness.",
            "implications": [
                "Detect alien life",
                "Better medicines",
                "Understand matter vs antimatter",
            ],
            "takeaway": "Life made a choice 4 billion years ago - and stuck with it.",
        },
        "topological": {
            "title": "🎀 Computers That Can't Make Mistakes",
            "tagline": "Microsoft built a quantum computer that error-corrects itself.",
            "analogy": "Normal computers write in sand. Quantum in fog. Topological computers braid hair - the pattern survives!",
            "discovery": "Microsoft's Majorana 1 uses topological qubits with built-in error correction.",
            "implications": [
                "Crack any code",
                "Design medicines in seconds",
                "Simulate entire universes",
            ],
            "takeaway": "Microsoft is building computers that use the shape of space as memory.",
        },
        "biophotonics": {
            "title": "💬 Your Cells Text Each Other... With Light",
            "tagline": "Every cell in your body glows.",
            "analogy": "Your body is a city where everyone communicates by flashlight. A secret fiber-optic network inside you!",
            "discovery": "Your DNA literally glows in the dark (very faintly). This light carries genetic information between cells.",
            "implications": [
                "Early disease detection",
                "Understanding wound healing",
                "Maybe even explaining consciousness",
            ],
            "takeaway": "You're literally glowing right now - your cells are talking in light.",
        },
        "zpe": {
            "title": "🌊 Empty Space Is Full of Energy",
            "tagline": "Scientists are learning to harvest power from 'nothing.'",
            "analogy": "Space is an ocean that looks calm on the surface but churns wildly beneath. Energy bubbles up constantly.",
            "discovery": "At the quantum level, space is never still. The Casimir effect proves this invisible energy is real.",
            "implications": [
                "Unlimited power from empty space",
                "Spacecraft without fuel",
                "Technology like magic",
            ],
            "takeaway": "The vacuum of space is bursting with energy - we just need to learn to harvest it.",
        },
    }

    # Get selected universe
    selected_key = list(UNIVERSES.keys())[
        list(
            [
                "evo",
                "lenr",
                "quantum_bio",
                "consciousness",
                "chirality",
                "topological",
                "biophotonics",
                "zpe",
            ]
        ).index(
            universe.value.split("(")[0].strip().split()[-1].lower()
            if "(" in universe.value
            else "quantum_bio"
            if "Plants" in universe.value
            else "evo"
            if "Electron" in universe.value
            else "lenr"
            if "Kitchen" in universe.value
            else "consciousness"
            if "Brain" in universe.value
            else "chirality"
            if "Hand" in universe.value
            else "topological"
            if "Mistakes" in universe.value
            else "biophotonics"
            if "Light" in universe.value
            else "zpe"
        )
    ]

    # Simple key extraction
    key_map = {
        "Electron": "evo",
        "Kitchen": "lenr",
        "Plants": "quantum_bio",
        "Brain": "consciousness",
        "Hand": "chirality",
        "Mistakes": "topological",
        "Light": "biophotonics",
        "Energy": "zpe",
    }
    selected_key = "quantum_bio"  # Default
    for k, v in key_map.items():
        if k in universe.value:
            selected_key = v
            break

    u = UNIVERSES[selected_key]
    implications = "\n".join(f"• {imp}" for imp in u["implications"])

    mo.md(f"""
    ## {u["title"]}
    
    *{u["tagline"]}*
    
    ---
    
    ### 🏠 Think of it like...
    {u["analogy"]}
    
    ### 🔬 What Scientists Discovered
    {u["discovery"]}
    
    ### 🌍 Why It Matters
    {implications}
    
    ---
    
    ### 📌 One Thing to Remember
    **👉 {u["takeaway"]}**
    """)
    return UNIVERSES, selected_key, u, implications


@app.cell
def _(mo, np, plt, selected_key):
    # 12D Physics State Evolution for this universe
    mo.md("## 📊 12D Physics State Evolution")

    # Simulate physics based on universe type
    np.random.seed(hash(selected_key) % 1000)
    timesteps = 50

    dimensions = [
        "Energy",
        "Coherence",
        "Complexity",
        "Stability",
        "Novelty",
        "Connectivity",
        "Mass",
        "Sentiment",
        "Factuality",
        "Time",
        "X",
        "Y",
    ]

    trajectory = np.zeros((timesteps, 12))
    trajectory[0] = np.random.randn(12) * 0.5

    for t in range(1, timesteps):
        trajectory[t] = trajectory[t - 1] + np.random.randn(12) * 0.1
        trajectory[t, 1] = min(1.0, trajectory[t, 1] + 0.02)  # Coherence increases

    fig, axes = plt.subplots(3, 4, figsize=(14, 8))
    fig.suptitle(f"12D Agent Physics: Exploring '{selected_key}'", fontsize=14)

    colors = plt.cm.viridis(np.linspace(0, 1, 12))

    for i, (ax, dim) in enumerate(zip(axes.flat, dimensions)):
        ax.plot(trajectory[:, i], linewidth=2, color=colors[i])
        ax.fill_between(range(timesteps), trajectory[:, i], alpha=0.3, color=colors[i])
        ax.set_title(dim)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig
    return timesteps, dimensions, trajectory, fig, axes, colors


@app.cell
def _(mo):
    # Interactive Q&A
    mo.md("""
    ## 💬 Ask a Question
    
    Ask anything about these physics topics! (Within our guardrails for safety and ethics)
    """)

    question = mo.ui.text(
        placeholder="e.g., How do plants compute like quantum computers?",
        label="Your Question:",
        max_length=200,
    )
    question
    return (question,)


@app.cell
def _(mo, question):
    if question.value:
        q = question.value.lower()

        # Simple keyword matching for demo
        if "quantum" in q and "plant" in q:
            answer = """**Great question!**
            
Plants achieve 95% energy efficiency by using quantum mechanical effects called 
"quantum coherence." When light hits a chlorophyll molecule, the energy exists 
in multiple states simultaneously - exploring all possible paths at once and 
choosing the most efficient one.

This is like having GPS that tests every route simultaneously and picks the fastest!

**Fun Fact:** Scientists at TUM discovered in 2025 that a special energy state 
called "Qx" in chlorophyll is crucial for this quantum magic."""
        elif "topological" in q or "microsoft" in q or "majorana" in q:
            answer = """**Topological Quantum Computing Explained:**

Microsoft's Majorana 1 processor uses a new approach where information is 
encoded in the *topology* (shape) of quantum states rather than the states 
themselves.

Think of it like braiding hair - even if individual strands get messy, the 
braid pattern survives. This gives built-in error protection!

**2025 Breakthrough:** Microsoft invented "topoconductors" - a new material 
class that enables topological superconductivity."""
        elif "hack" in q or "weapon" in q or "exploit" in q:
            answer = """⚠️ **I can't help with that topic.**

I'm designed to discuss science, energy, nature, and beneficial technology. 
I'd love to explore the physics topics in this notebook with you instead!

Try asking about quantum biology, consciousness, or clean energy."""
        else:
            answer = f"""**Interesting question!**

I don't have a specific answer prepared for "{question.value[:50]}..."

Here are some topics I can explore in depth:
- 🌿 How plants use quantum mechanics
- 🧠 Is consciousness quantum?
- 🎀 What are topological qubits?
- 💡 How do cells communicate with light?
- 🌊 What is zero-point energy?

Try asking about one of these!"""

        mo.md(answer)
    else:
        mo.md("*Enter a question above to get started!*")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    
    ## 📚 About This Notebook
    
    Built with:
    - **Cohezion Swarm** - AI orchestration platform
    - **FLUME** - Fluid Latent Understanding through Manifold Encoding
    - **CODE_SIMPLIFICATION_PRIME** - Making complexity accessible
    
    *Physics should be for everyone.* 🌌
    
    ---
    *cohezion.duckdns.org | 2026*
    """)
    return


if __name__ == "__main__":
    app.run()
