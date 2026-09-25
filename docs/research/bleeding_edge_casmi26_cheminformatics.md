# Bleeding-Edge Cheminformatics & Deep Learning for Enveda CASMI26
**Target Challenge**: Enveda CASMI 2026 - Molecule ID From Mass Spectra (Kaggle)
**Deadline**: December 14, 2026 (~80 days remaining)
**Objective**: Bridge the +0.097 gap from 0.328 to 0.425+ (Rank 1 Globally)

---

## 1. Deconstruction of Competition Metric & Physical Domain

### 1.1 Physical Domain: Tandem Mass Spectrometry (LC-MS/MS, MS2)
Tandem mass spectrometry separates and measures ionic fragments resulting from collision-induced dissociation (CID) or higher-energy collisional dissociation (HCD):

1. **Precursor Ionization & Monoisotopic Neutral Mass**:
   In electrospray ionization (ESI), molecules form adducts depending on ionization mode (positive/negative):
   $$M_{\text{neutral}} = z \cdot (m/z)_{\text{precursor}} - \delta_{\text{adduct}}$$
   Common adduct shifts $\delta_{\text{adduct}}$:
   - $[M+H]^+: +1.007276\,\text{Da}$
   - $[M+Na]^+: +22.989218\,\text{Da}$
   - $[M+NH_4]^+: +18.033823\,\text{Da}$
   - $[M+K]^+: +38.963158\,\text{Da}$
   - $[M-H]^-: -1.007276\,\text{Da}$
   - $[M+HCOO]^-: +44.998201\,\text{Da}$
   - $[M-H_2O+H]^+: -17.003289\,\text{Da}$

2. **Precursor Mass Accuracy ($\text{ppm}$)**:
   $$\text{ppm} = \frac{|(m/z)_{\text{obs}} - (m/z)_{\text{theo}}|}{(m/z)_{\text{theo}}} \times 10^6$$
   With high-resolution instruments (Orbitrap / FT-ICR), mass tolerance is within $\le 5\,\text{ppm}$ ($\pm 0.002\,\text{Da}$ at $400\,\text{m/z}$).

3. **Collision Energy & Ergodic Cleavage**:
   Precursors collide with inert gas atoms ($N_2, Ar$). Kinetic energy converts to vibrational energy, causing unimolecular cleavage along the weakest covalent bonds (heterolytic/homolytic cleavages, retro-Diels-Alder, McLafferty rearrangements, and neutral losses of $H_2O, CO, CO_2, NH_3$). Fragment peak lists $(m/z_i, I_i)$ represent the fingerprint of the 2D graph topology.

4. **Retention Time ($t_R$)**:
   LC retention time reflects column-solvent partition kinetics, strongly governed by lipophilicity ($\log P$), topological polar surface area (tPSA), and molecular volume.

### 1.2 Evaluation Metric: Mean Reciprocal Rank @ 25 (MRR@25)
Submissions are evaluated on **MRR@25**:
$$\text{MRR@25} = \frac{1}{U} \sum_{u=1}^U \text{RR}_u, \quad \text{RR}_u = \begin{cases} \frac{1}{\text{rank}_u} & \text{if } 1 \le \text{rank}_u \le 25 \\ 0 & \text{otherwise} \end{cases}$$
- Rank 1 match = $1.000$
- Rank 2 match = $0.500$
- Rank 5 match = $0.200$
- Rank 25 match = $0.040$
- Beyond 25 = $0.000$

**Crucial Evaluation Rule: InChIKey14 Tautomer Canonicalization**:
Matches are evaluated on the **first 14 characters** of the InChIKey (`InChIKey14`), corresponding to the molecular skeleton/connectivity, evaluated after RDKit tautomer canonicalization (`RDKit 2026.03.3`). Stereocenters (chiral $R/S$, geometric $E/Z$) and tautomer protonation states do not affect the score!

**Secondary Structural Similarity Metric**:
Tanimoto similarity on 2048-bit Morgan Fingerprints (radius 2 / ECFP4):
$$T(\mathbf{u}, \mathbf{v}) = \frac{\mathbf{u} \cdot \mathbf{v}}{\|\mathbf{u}\|_1 + \|\mathbf{v}\|_1 - \mathbf{u} \cdot \mathbf{v}}$$

---

## 2. Test Set Tri-Class Decomposition & The Rank 1 Bridge

The test set (~1,500 spectra, ~400 molecules) is partitioned into three distinct classes:
- **Class 1 (Library Match, 16%)**: Reference spectra present in public libraries (MassBank, GNPS, MoNA, HMDB).
- **Class 2 (Database Known, 45%)**: Structure present in PubChem / COCONUT / ChEMBL, but **no reference spectrum exists**.
- **Class 3 (Novel / De Novo, 39%)**: Structure is novel, not documented in PubChem.

### Why Current Approaches Plateau at 0.328:
$$\text{Score} = 0.16 \cdot \text{MRR}_{\text{C1}} + 0.45 \cdot \text{MRR}_{\text{C2}} + 0.39 \cdot \text{MRR}_{\text{C3}}$$
- Baseline models achieve $\text{MRR}_{\text{C1}} \approx 0.85$, $\text{MRR}_{\text{C2}} \approx 0.38$, $\text{MRR}_{\text{C3}} \approx 0.05$.
- Result: $0.16(0.85) + 0.45(0.38) + 0.39(0.05) = 0.136 + 0.171 + 0.020 = 0.327$.

### How to Reach 0.425+ (Rank 1):
1. **Class 1 (0.85 $\to$ 0.95)**: Clean library match using precursor ppm verification + entropy-weighted modified cosine. Contributes: **0.152**.
2. **Class 2 (0.38 $\to$ 0.52)**: Formula-gated candidate retrieval (<5 ppm + 7-Golden Rules) + FPNet 6,930-bit fingerprint prediction + GNN bond cleavage reranker. Contributes: **0.234**.
3. **Class 3 (0.05 $\to$ 0.12)**: 4-Channel mass-shifted analog propagation ($\Delta m/z$ neutral loss alignment) from natural product scaffolds. Contributes: **0.047**.
$$\text{Total Expected MRR} = 0.152 + 0.234 + 0.047 = \mathbf{0.433} > 0.425$$

---

## 3. SOTA Mass Spectrometry DL vs In-Silico Fragmentation

| Approach | Architecture / Paradigm | Strengths | Critical Bottlenecks | CASMI26 Role |
|---|---|---|---|---|
| **CFM-ID 4.0** | Probabilistic HMM on fragment tree | Interpretable, models collision energy | Combinatorial explosion ($O(N^3)$), very slow | Offline training augmentations |
| **MetFrag** | Combinatorial bond disconnection | Fast rule-based cleavage | Poor intensity prediction, high false positives | Baseline candidate scoring |
| **Spec2Vec** | Word2Vec on binned peaks + neutral losses | Fast unsupervised embeddings | No 2D structure prediction, coarse resolution | Pre-filtering reference spectra |
| **MS-Embed** | Dual-encoder contrastive (CLIP-style) | Fast MIPS candidate ranking | Information loss across subtle isomers | Candidate shortlisting |
| **MassFormer** | Graph Transformer (2D mol $\to$ MS2) | High-fidelity spectral prediction | High latency per candidate | Stage 3 top-50 reranker |
| **FPNet** | 6-layer Transformer (MS2 $\to$ 6,930-bit FP) | Direct multi-label fingerprint prediction | Requires candidate database to search | **Stage 2 backbone (Class 2/3)** |
| **MIST** | Formula Transformer (peaks as formulas) | Chemically grounded peak representations | Slower tokenization | Ensemble partner for FPNet |
| **GLACIER (2026)** | Single-stage object detector on mol graphs | 8x faster than ICEBERG, 70% Top-1 MassSpecGym | Complex graph representation | State-of-the-art benchmark |

---

## 4. Multi-Channel Analog Search (Mass-Shifted Propagation)

When a query precursor $M_Q$ differs from a reference precursor $M_L$ by $\Delta M = M_Q - M_L$, standard cosine library search fails. We propagate identity across **4 complementary channels**:

```
Query Spectrum (M_Q) ────────┐
                             ├─► [Channel 1: Direct Match]      (Core scaffold peaks: m/z_Q == m/z_L)
Library Spectrum (M_L) ──────┤─► [Channel 2: Shifted NL Match]  (Modified peaks: m/z_Q == m/z_L + ΔM)
                             ├─► [Channel 3: Sub-Fragment NL]   (Internal neutral losses: |m1 - m2|)
Precursor Isotope Pattern ───┴─► [Channel 4: Isotope Envelope]  (Formula validation of ΔM)
```

1. **Channel 1 (Direct Peak Match - Unmodified Core)**:
   $$m/z_{Q, i} = m/z_{L, j} \pm \epsilon, \quad S_{\text{direct}} = \frac{\sum_{\mathcal{M}_1} \sqrt{I_Q I_L}}{\sqrt{\sum I_Q^2 \sum I_L^2}}$$
2. **Channel 2 (Neutral Loss Match - Modified Fragment)**:
   $$M_Q - m/z_{Q, i} = M_L - m/z_{L, j} \pm \epsilon \iff m/z_{Q, i} = m/z_{L, j} + \Delta M \pm \epsilon$$
   $$S_{\text{shift}} = \frac{\sum_{\mathcal{M}_2} \sqrt{I_Q I_L}}{\sqrt{\sum I_Q^2 \sum I_L^2}}$$
3. **Channel 3 (Sub-Fragment Pattern - Internal Structural Invariants)**:
   $$\Delta m/z_{Q, (i_1, i_2)} = |m/z_{Q, i_1} - m/z_{Q, i_2}| \approx |m/z_{L, j_1} - m/z_{L, j_2}| = \Delta m/z_{L, (j_1, j_2)}$$
4. **Channel 4 (Precursor Isotope Pattern Validation)**:
   Calculates theoretical multinomial isotopic distribution for candidate modification formulas ($\Delta \text{Formula}$, e.g. $+\text{CH}_2$, $+\text{O}$, $+\text{Glc}$) and computes cosine similarity with observed precursor isotopic envelope.

---

## 5. Formula-Gated Candidate Filtering (<5 ppm + 7-Golden Rules)

### 5.1 Monoisotopic Mass Deconvolution
$$M_{\text{neutral}} = (m/z)_{\text{precursor}} - \delta_{\text{adduct}} \pm (M_{\text{neutral}} \times 5 \times 10^{-6})$$

### 5.2 Implementation of Kind & Fiehn 7-Golden Rules:
1. **Element Count Bounds**:
   $C_{1-100} H_{1-150} N_{0-20} O_{0-30} P_{0-5} S_{0-5} F_{0-6} Cl_{0-4} Br_{0-3}$.
2. **Senior's Valence & Parity Checks**:
   - $\sum_i v_i n_i \equiv 0 \pmod 2$ (Total valence sum must be even).
   - $\sum_i v_i n_i \ge 2 \cdot \max_i(v_i)$.
   - $\sum_i (v_i - 1) n_i \ge 2(n - 1)$ (Connected graph check).
3. **Hydrogen/Carbon Ratio**:
   $0.2 \le H/C \le 3.1$ (or $H/C \le 4.0$ for small alkanes).
4. **NOPS Heteroatom Ratio Checks**:
   $N/C < 1.3$, $O/C < 1.2$, $P/C < 0.3$, $S/C < 0.8$.
5. **Combined Heteroatom Bounds**:
   $(O+N)/C < 1.5$, $(P+S)/C < 0.5$.
6. **Isotopic Pattern Verification**:
   Validates predicted $M+1$ ($^{13}C$) and $M+2$ ($^{34}S, ^{37}Cl, ^{81}Br, ^{18}O$) abundance against observed precursor envelope.
7. **Adduct Consistency Verification**:
   Filters out impossible adduct assignments.

**Impact**: Restricting PubChem / COCONUT retrieval to formulas passing the 7-Golden Rules within 5 ppm reduces candidate pools from millions to **$50 - 250$ structures**, perfectly fitting in-memory reranking.

---

## 6. Structural Graph Reranking via GNN Bond Cleavage

Given a candidate molecular graph $G = (V, E)$ and observed MS2 peaks $\mathcal{P} = \{(m/z_k, I_k)\}_{k=1}^K$:

1. **GNN Architecture (Graph Isomorphism Network + Edge Features)**:
   Node representations update via:
   $$h_v^{(l)} = \text{MLP}^{(l)} \left( (1 + \epsilon^{(l)}) h_v^{(l-1)} + \sum_{u \in \mathcal{N}(v)} \text{ReLU}(h_u^{(l-1)} + e_{uv}) \right)$$
2. **Bond Cleavage Probability**:
   $$p(e_{uv} \text{ cleaves} | \text{CE}) = \sigma(\mathbf{w}^T [h_u^{(L)} \,\|\, h_v^{(L)} \,\|\, e_{uv} \,\|\, \text{CE}])$$
3. **Cleavage Compatibility Score**:
   For each observed peak $m/z_k$, find the minimum-cost edge cut $\mathcal{C}_k \subset E$ producing a fragment with mass matching $m/z_k$:
   $$E_{\text{cleave}}(k) = \min_{\mathcal{C} \models m/z_k} \sum_{e \in \mathcal{C}} (1 - p(e))$$
   $$S_{\text{GNN}}(G, \mathcal{P}) = \sum_{k=1}^K I_k \cdot \exp(-E_{\text{cleave}}(k))$$

---

## 7. Hierarchical Tri-Stage Ensembling Without Blowing Memory

```
Input Spectrum (m/z, CE, peaks)
         │
         ▼
[Stage 1: Formula-Gated Filtering] ──► Precursor mass (<5 ppm) + 7-Golden Rules (N ≤ 250)
         │
         ▼
[Stage 2: Bit-Packed Vector Search] ──► 6,930-bit FPNet POPCOUNT Tanimoto (N ≤ 50)
         │
         ▼
[Stage 3: Dense Reranking Ensemble] ──► LambdaMART / HistGradientBoosting
                                         ├─ FPNet Cosine Score
                                         ├─ Direct / Modified Spectral Cosine
                                         ├─ 4-Channel Analog Propagation Score
                                         ├─ GNN Bond Cleavage Compatibility
                                         ├─ Retention Time Delta |tR - tR_pred|
                                         └─ Natural Product Prior (COCONUT freq)
         │
         ▼
Top 25 Ranked SMILES (Submission Ready)
```

**Memory Optimization Benchmark**:
- Float32: $1,500 \times 250 \times 6,930 \times 4\,\text{bytes} = 10.4\,\text{GB}$.
- Packed `uint64`: $6,930 / 64 = 109$ integers $= 872\,\text{bytes}$ per molecule.
- Entire candidate search space fits in **< 350 MB RAM**!
