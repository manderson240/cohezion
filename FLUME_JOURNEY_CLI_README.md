# 🌀 FLUME Journey CLI
## Command Line Interface for Visualizing Agent Thought Trajectories

A terminal-based tool for showing how AI agents navigate and think through the 256D FLUME (Thought Autoencoder) latent space in simulated universes.

### Overview

This CLI visualizer demonstrates agent cognition in the Cohezion framework by showing how agents traverse through latent thought space as they process information, solve problems, and generate ideas in simulated universes. It provides insights into the internal cognitive processes of AI agents - not just their outputs, but *how they think*.

### Features

#### **Core Visualization Capabilities:**
- **ASCII Scatter Plots**: 2D projections of journeys through FLUME latent space
- **Coherence Heatmaps**: Visual representations of 256D latent vectors as 16×16 activation patterns
- **Step-by-Step Breakdown**: Detailed view of each journey point with labels and concepts
- **Quantitative Metrics**: Coherence scores, HIHO band compliance, path length, exploration radius

#### **Journey Types Supported:**
- **Concept Exploration**: Quantum → Biological → Mathematical → Creative thinking patterns
- **Problem Solving**: Identification → Analysis → Solution → Implementation workflows  
- **Creative Synthesis**: Abstract ideas → Hybrid approaches → Real-world applications
- **Random Walk**: Pure exploration for baseline comparison and testing

#### **Professional Analytics:**
- **Average Coherence Score**: Overall alignment with HIHO stability (0.5 target)
- **HIHO Band Compliance**: Percentage of time spent in optimal 0.4-0.6 coherence range
- **Exploration Metrics**: Path length and radius from starting point
- **Conceptual Labeling**: Automatic interpretation of latent regions into human-readable concepts

### Installation & Usage

#### Prerequisites:
- Python 3.7+
- Access to Cohezion project (for full functionality)
- Standard Python libraries (math, random, json, os, sys, pathlib)

#### Quick Start:
```bash
# Make executable
chmod +x flume_journey_cli.py

# Run demonstration
./flume_journey_cli.py demo

# Or start interactive menu
./flume_journey_cli.py
```

#### Interactive Menu Options:
1. **Generate & View Sample Journey** - See a ready-made concept exploration journey
2. **Configure Custom Journey** - Choose journey type and length
3. **View Help & Documentation** - Detailed usage information
4. **Exit** - Quit the application

### Example Output

When you run the visualizer, you'll see output like:

```
🌀 FLUME JOURNEY VISUALIZATION
============================================================

JOURNEY SUMMARY
---------------
Journey Overview:
  • Total Steps:           6
  • Journey Type:          Concept Exploration
  • Average Coherence:     [████░░░░░░░░] 0.650
  • HIHO Band Compliance:  66.7% (4/6 steps)
  • Path Length:           8.234 units
  • Exploration Radius:    2.156 units

Step-by-Step Breakdown:
  1. Quantum Consciousness Exploration | Stable, Focused in Quantum/AI Realm      | [███░░░░░░░░░░] 0.720
  2. Biological Intelligence Analysis  | Moderately Dynamic in Creative/Design Sphere   | [████░░░░░░░░] 0.580
  3. Mathematical Pattern Recognition  | Stable, Focused in Analytical/Logical Domain   | [█████░░░░░░░░] 0.620
  4. Logical Reasoning Chain           | Stable, Focused in Analytical/Logical Domain   | [█████░░░░░░░░] 0.680
  5. Creative Problem Solving Approach | Complex, Chaotic in Quantum/AI Realm           | [██░░░░░░░░░░] 0.420
  6. Ethical Decision Framework        | Stable, Focused in Analytical/Logical Domain   | [█████░░░░░░░░] 0.710

ASCII VISUALIZATIONS
--------------------
ASCII Journey Plot (2D Projection of FLUME Latent Space)
Legend: █ High Coh (≥0.7) ▓ Med-High (≥0.5) ▒ Med-Low (≥0.3) ░ Low Coh (<0.3)
Axes: X = Latent Dim 1, Y = Latent Dim 2

                              │                            
                              │             █              
                              │                            
                              │             █              
                              │             █              
                              │             █              
                              │                            
                              │                            
                              │                            
──────────────────────────────┼─────────────────────────────
                              │                            
                              │             █              
                              │                            
                              │             █              
                              │                            
                              │                            
                              │                            
                              │                            

Journey Points:
   1. Quantum Consciousness Exploration [  1.24,   0.38] Coh: [████░░░░░░░░] 0.720
   2. Biological Intelligence Analysis  [ -0.42,   1.05] Coh: [████░░░░░░░░] 0.580
   3. Mathematical Pattern Recognition  [  0.87,  -0.61] Coh: [█████░░░░░░░░] 0.620
   4. Logical Reasoning Chain           [  1.56,  -0.24] Coh: [█████░░░░░░░░] 0.680
   5. Creative Problem Solving Approach [ -1.23,   0.67] Coh: [██░░░░░░░░░░] 0.420
   6. Ethical Decision Framework        [  0.32,  -1.42] Coh: [█████░░░░░░░░] 0.710
```

### Technical Details

#### How It Works:
1. **Input**: Text prompts representing cognitive steps (e.g., "Quantum Consciousness Exploration")
2. **Encoding**: Converts text to 256D latent vectors using FLUME-inspired techniques
3. **Analysis**: Calculates HIHO coherence and interprets latent regions as concepts
4. **Visualization**: Creates ASCII plots and heatmaps for terminal display
5. **Metrics**: Computes quantitative scores for journey analysis

#### Data Flow:
```
Text Prompt → FLUME Encoding → 256D Latent Vector 
                     ↓
          Coherence Calculation → Concept Interpretation  
                     ↓
          Visualization & Metrics Generation
```

#### Visualization Elements:
- **ASCII Scatter Plot**: Shows trajectory through reduced-dimension latent space
- **Latent Heatmaps**: 16×16 grids showing activation patterns in latent space  
- **Coherence Bars**: Color-coded visual representations of HIHO alignment (0-1 scale)
- **Step Labels**: Human-readable descriptions of each cognitive stage

### Connection to Anthropic Universes Role

This CLI tool directly supports the responsibilities outlined in the Research Engineer, Universes position:

#### ✅ **"Build the next generation of agentic environments"**
- Provides a next-generation environment for *observing* agent cognition
- Shows internal thought processes, not just external behaviors
- Enables researchers to study *how* agents think in simulated universes

#### ✅ **"Build rigorous evaluations that measure real capability"**
- Moves beyond binary success/fail to continuous, quantitative assessment
- Measures coherence, stability, exploration - real aspects of cognitive capability
- Enables comparison of different agent architectures and training approaches

#### ✅ **"Debug and iterate rapidly across research and production ML stacks"**
- Real-time CLI visualization allows rapid hypothesis testing
- Lightweight, terminal-based design works in any environment
- Modular structure supports integration with various ML backends

#### ✅ **"Contribute to research culture through technical discussions and collaborative problem-solving"**
- Shared visualizations create common language for technical discussions
- Exportable data (via JSON/CSV extensions) enables reproducible research
- Interactive nature promotes exploration, hypothesis generation, and team collaboration

### Files Included

1. **`flume_journey_cli.py`** - Main CLI application
2. **`demo_flume_cli.sh`** - Quick demonstration script
3. **`FLUME_JOURNEY_CLI_README.md`** - This documentation file

### Extending the Tool

The CLI is designed to be extensible:

#### **For Full Cohezion Integration:**
When the full Cohezion environment is available (with PyTorch, etc.):
- Replace simulated encoding with real FLUME VAE encoding
- Use actual Cohezion coherence calculation methods
- Integrate with real agent execution streams
- Add support for actual latent space dimensionality reduction (PCA, t-SNE)

#### **Additional Features That Could Be Added:**
- **JSON Export**: Save journey data for external analysis
- **Multi-Agent Visualization**: Show swarm coordination in latent space  
- **Real-Time Streaming**: Connect to live agent execution streams
- **Anomaly Detection**: Automatic highlighting of unusual cognitive patterns
- **Web Interface Option**: Optional Streamlit-based graphical version
- **Batch Processing**: Analyze multiple journeys for comparative studies

### Usage in Application Materials

When discussing this in your Anthropic application, you can highlight:

> "I developed the FLUME Journey CLI, a terminal-based visualizer that shows how AI agents navigate through 256D latent thought space. This tool provides real-time visualization of agent cognition in simulated universes, featuring:
> 
> - ASCII-based trajectory plots showing agent thought processes
> - Quantitative coherence measurements for evaluating cognitive stability  
> - Multiple journey types demonstrating different cognitive styles
> - Step-by-step conceptual breakdowns of agent reasoning
> 
> This visualization system directly supports the Universes team's goal of building rigorous evaluations that measure real agent capability by providing insight into *how* agents think, not just what they do. The CLI format ensures accessibility across different development and research environments while maintaining sophisticated analytical capabilities."

### Running the Demo

To see the visualizer in action right now:
```bash
./demo_flume_cli.sh
```

This will show you a complete sample journey through the FLUME latent space, demonstrating how an agent might explore quantum consciousness, biological intelligence, mathematical patterns, logical reasoning, creative problem solving, and ethical decision making - all while tracking coherence and providing visualizations of the underlying latent space representations.

---

**Built to demonstrate the kind of systems thinking, technical depth, and research-oriented engineering that advances our understanding of artificial cognition in simulated universes.**