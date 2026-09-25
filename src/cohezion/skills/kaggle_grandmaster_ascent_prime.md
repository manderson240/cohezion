# SKILL: KAGGLE_GRANDMASTER_ASCENT_PRIME

## DOMAIN EXPERTISE
Autonomous Kaggle Leaderboard Climbing, Multi-Track Portfolio Management, Systems Engineering V-Model Verification Gates (VG-1 to VG-4), and Continuous Competitive Invariant Auditing.

## KEY TEXTS & CONCEPTS
- **Full Leaderboard Ingestion**: Bypasses truncated API views via `kaggle competitions leaderboard <comp> -d` to extract exact team ranks, total competitors, and mathematical distance to podium thresholds.
- **Winnable Payout Accounting**: Calculates actual prize rewards for realistic target positions (1st–3rd place), rejecting deceptive gross prize pool sums.
- **Acyclic Oriented Graph Matching (AOGM / TRA)**: Mathematical cell lineage scoring (Ulman et al., *Nature Methods* 2017) ensuring spatial graph reciprocity.
- **Game-Theoretic Market Dynamics**: Discrete order-book execution priority, Step-0 capital leverage, and terminal asset liquidation.
- **SWE-bench Verified Autonomous Agents**: Declarative ADK schemas, air-gapped container lifecycles, and non-metered submission invariants.
- **Discrete Program Synthesis & Cayley Groups**: Program induction over Dihedral symmetries and permutation groups for ARC abstraction.
- **SurrealDB Compound Graph Mesh**: Multi-agent coordination linking Scientist Digital Twins, verification gates, and competition entities.

## INSTRUCTION
1. **Continuous Portfolio Audit**:
   Execute the automated leaderboard auditor to inspect exact live positions and gaps:
   ```bash
   uv run python scripts/kaggle/leaderboard_inspector.py --sync-surreal
   ```
2. **Prioritization by Ending Soonest**:
   Strictly order development effort by remaining calendar days (e.g. Biohub at 4d, Kaggriculture at 5d) before allocating compute to long-horizon tracks.
3. **Systems Engineering V-Model Gating (Mandatory Before Any Submit)**:
   - **VG-1 (AST & Schema Gate)**: Validate that candidate code parses without errors (`ast.parse()`), declarative YAML manifests conform strictly to Pydantic schemas (e.g. `thinking_config` nested inside `GenerateContentConfig`), and entrypoints follow competition conventions.
   - **VG-2 (Local Head-to-Head Gate)**: Run local deterministic emulation (e.g. 30-seed simulation or offline holdout validation) to guarantee 100% win-rate and positive delta margin.
   - **VG-3 (Resource & Hardware Bounds Gate)**: Confirm execution complies with the Zero-Local-Weight Guardrail (0 MB host GPU VRAM) and fits within remote limits (<9h kernel timeout, <10 GB RAM, <3 GiB unpacked zip).
   - **VG-4 (Patch Non-Emptiness & Reciprocity Gate)**: Assert that `git diff HEAD` is non-empty before calling `submit_patch()`, check forward-backward reciprocity ($C_{i \to j} = C_{j \to i}$), and preserve live matchmaking slots (`LIVE_SLOTS = 2`).
4. **State Persistence**:
   Upsert all metrics, audit records, and retrospective learnings directly into SurrealDB (`competition`, `submission_record`, `learning` tables).

## VERSION
v1.0

## SEE ALSO
- `AUTOHARNESS_PRIME`
- `VMODEL_ENGINEERING_PRIME`
- `RECURSIVE_LEARNING_PRIME`
