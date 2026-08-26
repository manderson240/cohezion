# Expert Competition Architectures & Fine-Tuning Blueprints

**Date:** 2026-08-26 18:22:44 UTC  
**Auditors:** `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`  
**Focus:** ARC-AGI-2/3, Pokémon TCG, RSNA Knee Detection, and Biohub 3D Cell Tracking.

---

# 🏆 ARC Prize 2026 (ARC-AGI-2 & ARC-AGI-3)
**Architect:** `deepseek-v4-pro:cloud` (Generation Time: 29.22s | Status: SUCCESS)

t):
    objs = find_objects(input, connectivity=4, background=0)
    largest = largest_object(objs)
    mask = object_mask(largest)
    filled = flood_fill(input, center(mask), color=most_common(input), connectivity=4)
    return rot90(filled, k=1)
```

Need maybe include "BNF grammar":
```
program := statement*
statement := assignment | return
assignment := var '=' expr
expr := grid_expr | object_expr | int_expr | bool_expr
grid_expr := input | output | make_grid(int, int, color) | rot90(grid_expr, int) | flip_h(grid_expr) | ...
object_expr := find_objects(grid_expr, connectivity, background) | largest_object(object_expr) | ...
...
```

Need maybe include "type system" to prevent invalid programs.

Need maybe include "LLM fine-tuning data format":
```
{"messages": [{"role": "user", "content": "Input: [[...]]\nOutput: [[...]]\nWrite DSL program."}, {"role": "assistant", "content": "def solve(input):\n    ..."}], "task_id": "..."}
```

Need maybe include "DeepSeek-R1 reasoning trace":
```
Reasoning: The output is the input rotated 90 degrees clockwise. The objects are preserved. Program: rot90(input, 1)
```
Need maybe include "Qwen-Coder direct program generation" without reasoning.

Need maybe include "TTPS algorithm pseudocode":
```
def ttps(task, llm, grammar, budget):
    beam = [empty_program]
    for step in range(max_depth):
        candidates = []
        for prog in beam:
            if prog.complete:
                candidates.append(prog)
            else:
                expansions = llm.propose(prog, task, k=8) + grammar.enumerate(prog, k=4)
                for e in expansions:
                    candidates.append(prog.extend(e))
        # verify candidates on training examples
        scored = [(c, verify(c, task)) for c in candidates]
        beam = top_k(scored, beam_width)
    return best(beam)
```

Need maybe include "MCTS":
```
def mcts(task, llm, grammar, simulations):
    root = Node(empty_program)
    for _ in range(simulations):
        node =

---

# 🏆 Pokémon TCG AI Strategy (Game Theory & Incomplete Information)
**Architect:** `qwen3.5:397b-cloud` (Generation Time: 61.76s | Status: SUCCESS)

### **Project: Kanto-Zero (Pokémon TCG SOTA Agent)**
**Target:** Kaggle TCG Strategy Environment (Hypothetical/Private League)
**Constraint:** ~1.0s Inference Time per Turn | Imperfect Information | Stochastic Dynamics
**Architect:** Game Theory & RL Grandmaster

---

### **1. Core Decision Engine: Distilled DeepCFR Policy**
Pure MCTS is too computationally expensive for a 1.0s budget in a high-branching TCG. Pure PPO fails to converge to a Nash Equilibrium in imperfect information settings (exploitable by adversaries). The SOTA approach is a **Teacher-Student Distillation** pipeline.

*   **Teacher (Offline Training):** **Deep Counterfactual Regret Minimization (DeepCFR)**.
    *   **Why:** DeepCFR is the backbone of SOTA Poker AI (e.g., Pluribus variants). It minimizes regret over information sets, ensuring unexploitable play regarding hidden cards (Opponent Hand, Prizes).
    *   **Role:** Generate optimal strategy profiles via self-play. It handles the combinatorial explosion of hidden states during the *training phase* where time is unlimited.
*   **Student (Online Inference):** **Lightweight Transformer Policy Network**.
    *   **Architecture:** 4-Layer Encoder-Only Transformer (Hidden Dim: 256, Heads: 4).
    *   **Input:** Game State + Belief Vector (See Section 2).
    *   **Output:** Probability distribution over valid action masks.
    *   **Training Objective:** Behavior Cloning (KL-Divergence loss) against the Teacher's policy, regularized with PPO loss for robustness against distribution shift.
    *   **Runtime:** Exported to **ONNX Runtime** with FP16 quantization. Inference time target: <50ms.

### **2. Incomplete Information Handling: Public Belief State (PBS)**
Determinization (sampling specific hidden hands during inference) is too slow for 1.0s. Instead, we encode the *probability distribution* of hidden information directly into the network input.

*   **Belief Vector Construction:**
    *   **Deck Probability:** Track remaining card counts based on known decklist (60 cards) - (Visible Hand) - (Board) - (Discard).
    *   **Opponent Hand Inference:** Maintain a Bayesian update vector.
        *   *Prior:* Uniform probability over remaining deck.
        *   *Update:* If opponent plays "Professor's Research" (Draw 7), update probability of them holding specific combos. If they pass turn without attacking, increase probability of high-energy hands or "dead" hands.
    *   **Prize Card Delta:** Track 6 prize slots as a probability distribution of card types (e.g., 20% chance Prize 1 is an Energy, 10% Supporter).
*   **Input Fusion:**
    *   Concatenate the **Visible State Tensor** with the **Belief Vector**.
    *   The Policy Network learns to value actions based on *expected value* over the belief distribution, effectively performing "implicit" expectation calculation without explicit sampling.

### **3. Turn-Time Budget Allocation (1.0s Limit)**
Kaggle's evaluation harness kills processes exceeding time limits. Strict budgeting is required.

| Phase | Budget | Strategy |
| :--- | :--- | :--- |
| **State Preprocessing** | 10ms | Pre-compute card ID lookups. Use NumPy arrays for board state. Avoid object instantiation during turn loop. |
| **NN Inference** | 50ms | **ONNX Runtime** with CPU execution providers. Batch single-step inference. FP16 quantization. |
| **Action Masking** | 20ms | Hard-coded rule engine to filter illegal moves (e.g., cannot attack without energy). *Crucial:* Do not rely on NN to learn legality. |
| **Stochastic Sampling** | 10ms | Sample action from Policy distribution. Use `numpy.random.choice` with pre-seeded RNG for reproducibility. |
| **Buffer/Safety** | 910ms | Reserve for Python overhead, garbage collection, and network latency in multiplayer handshakes. |

*   **Optimization:** Pre-load the model at initialization (`__init__`). Do not load weights during `act()`.
*   **Fallback:** If inference > 80ms, switch to a **Heuristic Greedy Policy** (Priority: Knockout > Draw > Energy Attach) to prevent timeout.

### **4. Feature Representation: Card2Vec + Board Graph**
Raw card IDs are insufficient. The model must understand card *semantics* (e.g., "Quick Ball" searches Pokémon, "Switch" retreats).

*   **Card Embeddings (Static):**
    *   Pre-train a **Card2Vec** model (Skip-gram) on card text/effects from the full TCG database.
    *   **Dimension:** 64-dim vector per Card ID.
    *   **Semantic Clustering:** Cards with similar effects (e.g., all "Draw 2" Supporters) should have close cosine similarity.
*   **Board State Tensor (Dynamic):**
    *   **Active Pokémon:** `[HP%, Energy Count, Status, Card Embedding]`
    *   **Bench (x5):** `[HP%, Energy Count, Status, Card Embedding]` per slot.
    *   **Hand:** `[Count, Avg CMC, Card Embedding (Mean Pooled)]` (Opponent hand hidden, use Belief Vector).
    *   **Global State:** `[Prizes Remaining, Deck Size, Turn Count, Coin Flip State]`.
*   **Prize Delta Tracking:**
    *   Input a 6-dim vector representing the *remaining* prize cards. As prizes are taken, this vector updates. This allows the agent to play differently when 1 prize remains (aggressive) vs 6 prizes (setup).

---

### **Grandmaster's Advisory & Reality Check**

**1. Competition Status:**
As of my current knowledge cutoff, **there is no official, active "Kaggle Pokémon TCG Strategy" competition.** There have been supervised learning competitions (e.g., "Pokémon Battle Prediction"), but a full TCG RL environment on Kaggle is not a standard public benchmark.
*   **Action:** If you are entering a *private* league or a specific hackathon, verify the API constraints. If this is for a personal project, use the **PokéTGC-Gym** (open-source environments) to test this architecture.

**2. The "1.0s" Trap:**
In Python, 1.0s is extremely tight for complex logic.
*   **Recommendation:** Write the inference engine in **C++** or **Rust** and bind it to Python via `pybind11` if the competition rules allow compiled binaries. If Python-only is mandated, minimize library imports (use `numpy` only, avoid `pandas`/`torch` during inference).

**3

---

# 🏆 Biomedical & Vision Tracks (RSNA Knee & Biohub 3D Cell Tracking)
**Architect:** `glm-5.2:cloud` (Generation Time: 28.19s | Status: SUCCESS)

As a Kaggle Grandmaster in Medical Imaging and 3D Spatiotemporal Computer Vision, I have seen firsthand what separates a top-1% solution from a mid-tier submission. In medical imaging, you must balance computational constraints, varying input dimensions, and severe class imbalance. 

Here is the concrete, highly actionable specification for your two tasks, based on state-of-the-art winning architectures.

---

### 1. RSNA Knee Abnormality Detection (Multi-view MRI)

**Verdict on Architecture:** Pure 3D CNNs (ConvNeXt-3D, ResNet3D) underperform here due to varying slice counts, low inter-slice resolution, and massive memory bottlenecks. The winning architecture is a **2D Slice Feature Extractor + Sequence Transformer (MIL-Attention)**. 

#### A. Architecture Specification
*   **View-Specific 2D Encoders:** Use three separate 2D backbones (e.g., `EfficientNetV2-S` or `ConvNeXt-Tiny`) for Sagittal, Coronal, and Axial planes. Sagittal is critical for ACL/Meniscus; Axial/Coronal for Cartilage/Bone Marrow.
*   **Slice Feature Extraction:** Pass each slice through the backbone up to the final pooling layer to get a `[N_slices, D]` feature vector per volume.
*   **Temporal/Sequence Aggregator (MIL-Transformer):**
    *   Add a learnable `[CLS]` token to the sequence of slice embeddings.
    *   Add 1D positional encodings (slice index).
    *   Pass through a 2-layer Transformer Encoder (4 heads, dim=512).
    *   Extract the `[CLS]` token output as the volume-level representation.
*   **Multi-View Fusion:** Concatenate the `[CLS]` representations from the three planes. Pass through a 2-layer MLP with Dropout(0.3) to output 4 logits (ACL, Meniscus, Cartilage, Bone Marrow).

#### B. Pre-training & Loss Functions
*   **Pre-training:** Initialize backbones with **RadImageNet** weights. If time permits, perform self-supervised pre-training (SimMIM or MAE) on the unlabeled Kaggle MRI slices to adapt to the domain-specific intensity distributions.
*   **Loss Function:** **Asymmetric Loss** or **Multi-label BCE with Focal Weighting**. 
    *   *Formula:* `Loss = BCE(logits, targets) * (1 - p_t)^gamma` where `gamma=2.0`.
    *   *Trick:* Use a positive class weight multiplier of `2.0` to `5.0` depending on the prevalence of the specific abnormality in the training set to combat extreme class imbalance.
*   **Optimizer & Schedule:** AdamW, learning rate `1e-4`, weight decay `1e-2`. Cosine Annealing with a 5-epoch warmup.

#### C. Augmentation Pipeline
*   **2D Slice Augmentations:** Random affine (rotation ±15°, scale ±10%), random brightness/contrast shifts, Gaussian noise, and Cutout.
*   **Volume-level Augmentations:** 
    *   *Random Slice Dropout:* Drop 10-20% of slices randomly to force the Transformer to not rely on a single "smoking gun" slice.
    *   *MixUp:* Blend slice sequences and labels at the volume level with a probability of 0.2.

---

### 2. Biohub Cell Tracking During Development (3D+t)

**Verdict on Architecture:** Embryonic development features dense, tightly packed cells with rapid divisions. Standard 3D U-Nets fail at instance separation. The winning pipeline is **StarDist 3D for Segmentation + Spatiotemporal GNN for Tracking & Division Detection**.

#### A. Cell Segmentation (StarDist 3D)
*   **Why StarDist 3D:** Outperforms Cellpose 3D in dense embryonic tissues because it predicts star-convex polyhedra, which naturally separate touching instances without relying solely on distance maps (which suffer from under-segmentation in dense clusters).
*   **Architecture:** 3D U-Net backbone with two heads:
    1.  *Object Probability Head:* Sigmoid output predicting cell foreground.
    2.  *Ray Head:* Predicts 96 radial distances per voxel to define the 3D polyhedron boundary.
*   **Post-processing:** Non-Maximum Suppression (NMS) in 3D with an IoU threshold of 0.4 to merge overlapping polyhedra into single cell instances.

#### B. Temporal Tracking & Division Detection (Spatiotemporal GNN)
*   **Why GNN over LAP:** While Linear Assignment Problem (LAP) with Hungarian algorithms works for sparse cells, embryonic development involves rapid morphological changes and cell divisions. A GNN can learn motion priors *and* lineage rules simultaneously.
*   **Graph Construction (per time step $t$ to $t+1$):**
    *   *Nodes:* Cell instances from frame $t$ and $t+1$. Node features = 3D centroid $(x,y,z)$, volume, eccentricity, and mean intensity.
    *   *Edges:* Connect all cells in $t$ to all cells in $t+1$ within a spatial radius $R$ (e.g., 30 microns). Edge features = Euclidean distance, delta volume, delta intensity.
*   **GNN Architecture:** 
    *   Use an Edge-Conditioned Graph Convolutional Network (EGCN) or a Graph Attention Network (GAT).
    *   3 message-passing layers.
*   **Edge Classification Head:** Binary classification on edges.
    *   `Class 0`: No link.
    *   `Class 1`: Mother-daughter link (Division).
    *   `Class 2`: Continuation link (Same cell moving).
*   **Lineage Tree Optimization:** 
    *   Extract the maximum spanning tree from the GNN's predicted edge probabilities.
    *   Enforce biological constraints: A cell in $t$ can have at most 2 outgoing edges (division), and a cell in $t+1$ can have at most 1 incoming edge. Use a constrained Hungarian algorithm on the GNN probability matrix to enforce these topological constraints.

#### C. Training Specifications
*   **Segmentation Loss:** `Loss = Dice Loss + (1 * BCE for foreground) + (1 * MAE for radial rays)`.
*   **GNN Training:** Train on synthetic or manually annotated tracks. Use Cross-Entropy loss heavily weighted for the "Continuation" and "Division" classes to prevent the network from defaulting to "No link" due to class imbalance.
*   **Augmentation:** For the 3D U-Net, use elastic deformations in 3D and simulated cell divisions (randomly splitting a cell mask into two adjacent masks in the $t+1$ frame) to train the GNN robustly on mitosis events.

---

