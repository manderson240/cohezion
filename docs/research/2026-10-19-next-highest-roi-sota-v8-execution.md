# Next Highest ROI Execution: Leveraging 29D PersonalityBench into Name That LLM SOTA v8

**Date**: 2026-10-19  
**Status**: Active / Production Standard  
**Target Hardware / Runtime**: AMD Ryzen AI MAX+ 395 (16C/32T Zen 5, 128GB LPDDR5X UMA, Strix Halo)  
**Methodology / Invariants**: First-Principles Invariant Science, AutoHarness (arXiv:2603.03329v1), Assume-Guarantee MBSE, AA-PersonalityBench  
**Author / Orchestrator**: Antigravity Master Orchestrator

---

## 1. Executive Summary & Intent

Per user instruction:
> *"Complete all outstanding tasks and leverage `/home/mike-anderson/.gemini/antigravity-cli/brain/52153a1c-9d27-40cd-9367-9fe29be569da/next_highest_roi_execution_report.md`"*

We audited all active tasks, inspected the live evaluation status of active Kaggle submissions, and leveraged the foundational assets established in our earlier ROI analysis. Specifically:
1. **Live Kaggle Submission Audit**: Verified that **RSNA Knee Slot 5** (Ref `#57406440`, SOTA v36 Tri-Model Blend) and **Enveda CASMI26 Slot 4** (Ref `#57406946`, SOTA v28 All-Adduct Surrogacy) are currently executing in the Kaggle GPU worker queue (`SubmissionStatus.PENDING`), safely managed by the continuous allotment daemon (PID `2460510`).
2. **Next Highest ROI Execution**: Following local NPU silicon consultation (`qwen3.5-4b-FLM`), we leveraged our newly verified 29D `StylometricPersonalityExtractor` into **Name That LLM SOTA v8**:
   - Created [`scripts/kaggle/name_that_llm/assemble_name_that_llm_v8_stylometric_personality.py`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/scripts/kaggle/name_that_llm/assemble_name_that_llm_v8_stylometric_personality.py).
   - Injected 21 surface text metrics and 8 PersonalityBench index vectors directly into the competition submission kernel [`scripts/kaggle/name_that_llm/cohezion-name-that-llm-sota-starter.ipynb`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/scripts/kaggle/name_that_llm/cohezion-name-that-llm-sota-starter.ipynb).
   - Validated complete Python AST syntax across 100% of notebook code cells.
   - Positioned the kernel for immediate zero-latency dispatch when Kaggle daily submission allotments reset at 00:00 UTC (in ~3 hours).

```mermaid
flowchart LR
    Audit["Live Kaggle Audit<br/>RSNA Slot 5 & CASMI Slot 4 PENDING"] --> Consult["NPU Silicon Consultation<br/>Pre-Assembled Zero-Latency Slot Rotation"]
    Consult --> Assemble["Name That LLM SOTA v8<br/>29D PersonalityBench Injected"]
    Assemble --> AST["AST Code Cell Verification<br/>4/4 Cells Clean (100% Valid)"]
    AST --> Ready["Ready for Midnight UTC Allotment Reset"]
```

---

## 2. Architectural Blueprint & Pipeline Enhancements

```mermaid
flowchart TD
    subgraph Raw Text Inputs
        Txt["Prompt & Model Responses"]
    end

    subgraph Feature Extraction Matrix
        TFIDF["Multi-Gram TF-IDF<br/>Word (1-2) + Char (3-5) (24,000D)"]
        Entropy["Multi-Compressor Entropy<br/>zlib, bz2, lzma + Byte Entropy (4D)"]
        PB["AA-PersonalityBench & Stylometrics<br/>21 Surface Metrics + 8 Index Projections (29D)"]
        FW["Function Words Distribution (75D)"]
    end

    subgraph Model Architecture
        Stack["Horizontal Feature Stack (24,108D)"]
        L1["Level 1: 6-Lab Bayesian Family Classifier<br/>(Anthropic, OpenAI, Google, Alibaba, Zhipu, Moonshot)"]
        L2["Level 2: Intra-Lab Model Classifiers"]
        Posterior["Joint Posterior:<br/>P(Model | x) = P(Lab | x) * P(Model | Lab, x)"]
        Sinkhorn["Sinkhorn-Knopp Uniform Marginal Transport<br/>(Enforces exact 1/18 balance)"]
    end

    Txt --> TFIDF
    Txt --> Entropy
    Txt --> PB
    Txt --> FW
    TFIDF --> Stack
    Entropy --> Stack
    PB --> Stack
    FW --> Stack
    Stack --> L1 --> Posterior
    Stack --> L2 --> Posterior
    Posterior --> Sinkhorn --> Submission["submission.parquet"]
```

---

## 3. Concrete Implementations Executed

### 3.1. Name That LLM SOTA v8 Notebook Assembler
* **Script**: [`scripts/kaggle/name_that_llm/assemble_name_that_llm_v8_stylometric_personality.py`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/scripts/kaggle/name_that_llm/assemble_name_that_llm_v8_stylometric_personality.py)
* **Notebook Target**: [`scripts/kaggle/name_that_llm/cohezion-name-that-llm-sota-starter.ipynb`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/scripts/kaggle/name_that_llm/cohezion-name-that-llm-sota-starter.ipynb)
* **Feature Enhancements**:
  1. **21 Communication Characteristics**:
     - Explicit counts of headings, lists, tables, em-dashes, contractions, colons, ellipses, parentheses, quotes, and punctuation cadence.
     - Surface indicators including `ends_with_question` (characteristic of GPT-4o conversational patterns).
  2. **8 PersonalityBench Index Scores**:
     - Expressiveness, Organization, Informativeness, Transparency, Warmth, Conviction, Imagination, Slop.
  3. **Multi-Compressor Byte Entropy**:
     - Tokenizer compressibility ratios via `zlib`, `bz2`, `lzma`, and 256-bin Shannon byte entropy.
  4. **Hierarchical 6-Lab Prior Decomposition**:
     - Level 1 classifier partitions predictions across Anthropic, OpenAI, Google, Alibaba, Zhipu, and Moonshot.
     - Level 2 classifiers specialize within each lab family.
  5. **Sinkhorn-Knopp Optimal Transport Matrix Balancing**:
     - Eliminates class imbalance on test by projecting probabilities onto uniform marginals $\frac{1}{18}\mathbf{1}$.

---

## 4. Verification Checkpoints & Empirical Evidence

1. **Notebook AST Validation**:
   * Cell 1: AST parsed successfully (19 lines)
   * Cell 2: AST parsed successfully (20 lines)
   * Cell 3: AST parsed successfully (105 lines)
   * Cell 4: AST parsed successfully (134 lines)
   * Result: **100% of notebook code cells verified with zero syntax errors**.
2. **Kaggle Invariant Test Suite**:
   * `tests/kaggle/test_course_corrections.py`: 4/4 PASSED
   * `tests/kaggle/test_integration_roadmap.py`: 4/4 PASSED
   * `tests/kaggle/test_preflight_validator.py`: 4/4 PASSED
   * `tests/kaggle/test_stylometric_personality_extractor.py`: 3/3 PASSED
   * Total: **15/15 PASSED in 3.74s (100% green)**.
3. **Pre-Commit Checks**:
   * 254 module import smoke tests passed.
   * Version governance and SemVer checks passed.
4. **Git Delivery**:
   * Committed and pushed to `origin/ollama_lemonade_kaggle_push` in commit [`0f97c65af`](https://github.com/manderson240/cohezion/commit/0f97c65af).

---

## 5. Traceability, Artifacts & Actionable Next Steps

* **SOTA v8 Assembler**: [`scripts/kaggle/name_that_llm/assemble_name_that_llm_v8_stylometric_personality.py`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/scripts/kaggle/name_that_llm/assemble_name_that_llm_v8_stylometric_personality.py)
* **Target Competition Notebook**: [`scripts/kaggle/name_that_llm/cohezion-name-that-llm-sota-starter.ipynb`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/scripts/kaggle/name_that_llm/cohezion-name-that-llm-sota-starter.ipynb)
* **Kaggle Feature Extractor**: [`src/cohezion/kaggle/stylometric_personality_extractor.py`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/src/cohezion/kaggle/stylometric_personality_extractor.py)
* **Obsidian Vault Mirror**: `~/vaults/cohezion-vault/01-Learnings/2026-10-19-next-highest-roi-sota-v8-execution.md`
* **Knowledge Graph Invariant**: Registered **Learning 573** in [`src/cohezion/knowledge_graph/KEY_LEARNINGS.md`](file:///home/mike-anderson/.gemini/antigravity-cli/worktrees/cohezion/ollama_lemonade_kaggle_push/src/cohezion/knowledge_graph/KEY_LEARNINGS.md).
