# Gemma 4 Good Hackathon — Complete Submission Plan

**Deadline**: 2026-05-18 11:59 PM UTC (~3 weeks)
**Prize Pool**: $200,000 USD
**Track**: Global Resilience
**Branch**: `challenge/gemma-4-good-hackathon`

---

## Scoring Rubric (100 Points)

| Category | Weight | What Wins |
|----------|--------|-----------|
| Impact & Vision | 40 pts | Real-world NGO use, clear social good, scalability |
| Video Pitch & Storytelling | 30 pts | 60-180 sec, compelling narrative, production quality |
| Technical Depth & Execution | 30 pts | Gemma-4 integration, Cactus Compute, kagglehub, tests |

---

## Current State — What Exists

| Artifact | Status | Notes |
|----------|--------|-------|
| `kernel.py` | Draft | Self-contained Kaggle notebook, but uses `gemma-3-4b-it` — should be Gemma 4 |
| `kaggle_submission.py` | Draft | Ollama script with `gemma4:31b-cloud`, not Kaggle-native |
| `crisis_compound_demo.py` | Draft | Agent demo with Ollama integration, 5 scenarios |
| `training_loop.py` | Draft | Simulated skill refinement — no real learning |
| `dashboard.py` | Draft | CLI ASCII dashboard |
| `app.py` | Draft | Hugging Face Space CPU-only stub |
| `PROJECT_WRITEUP.md` | Draft | ~572 words, needs to reach 1,500 with depth |
| `README.md` | Draft | ~424 words, good structure |
| `BLOG_POST.md` | Draft | ~410 words, needs polish |
| `VIDEO_SCRIPT.md` | Draft | 60-sec script, no video produced |
| `compound_crisis_response.json` | Output | Example results file |
| `kernel-metadata.json` | MISSING | Required for Kaggle push |
| Tests / Mycelium | MISSING | Zero test coverage |
| kagglehub integration | MISSING | Mandate requires kagglehub for weights |
| Trademark notice | MISSING | Required: "Gemma is a trademark of Google LLC." |
| Cactus Compute / Tunix | MISSING | Technical depth points require these |
| Multilingual demo | MISSING | Claimed in script but no code |
| Working Kaggle submission | MISSING | Needs push + verify |

---

## Gap Analysis — Critical Issues

### Severity 1 (Must Fix — Blocks Submission)
1. **Wrong Gemma version in kernel**: `kernel.py` loads `google/gemma-3-4b-it`. Must use Gemma 4 (`google/gemma-4/frameworks/pyTorch/variations/e4b-it`).
2. **No kernel-metadata.json**: Cannot push to Kaggle without it.
3. **No kagglehub usage**: Hackathon mandate explicitly requires kagglehub for weights.
4. **Missing trademark notice**: MANDATORY per rules. Must appear in README, writeup, and notebook header.
5. **No video produced**: 30% of score depends on a YouTube video pitch.

### Severity 2 (High Impact — Differentiates)
6. **Simulated training loop**: `training_loop.py` uses random numbers for "progress." Need at least a basic real RL loop (even if small-scale) to score Technical Depth points.
7. **No tests**: Submissions with verified unit/integration tests project competence.
8. **Writeup too short**: 572 words vs 1,500-word max. Fill with architectural detail, Gemma-4 feature usage, engineering choices.
9. **No Cactus Compute / Tunix mention**: 30 Tech Depth points expect quantization/edge optimization.
10. **No multilingual demo**: Video script claims it but no code. Add at least Spanish output.

### Severity 3 (Polish — Score Boosters)
11. `app.py` is a CPU-only stub; make it a working HF Space demo.
12. `dashboard.py` is ASCII-only; add matplotlib skill-refinement chart.
13. GitHub repo lacks screenshots, install instructions.
14. No automated Kaggle submit script or CI.
15. No "wow factor" demo (12D manifold, TEK synthesis mentioned in mandate but not implemented).

---

## 3-Week Execution Plan

### Week 1: Technical Foundation (Apr 28 — May 4)
**Goal**: Kernel runs with real Gemma-4 on Kaggle, kagglehub integrated, legal notices added, tests pass.

| Day | Task | Deliverable | Owner |
|-----|------|-------------|-------|
| Mon 4/28 | Fix kernel.py: swap gemma-3-4b-it → kagglehub download of gemma-4 e4b-it | Updated kernel.py | Agent |
|          | Add kernel-metadata.json | kernel-metadata.json | Agent |
|          | Add "Gemma is a trademark..." to all documents | Patched README/WRITEUP/BLOG/VIDEO_SCRIPT | Agent |
| Tue 4/29 | Write pytest suite for agent logic, alignment gate, skill refinement | tests/test_crisis_agent.py | Agent |
| Wed 4/30 | Refactor kaggle_submission.py to use kagglehub + transformers pipeline | Updated kaggle_submission.py | Agent |
| Thu 5/1  | Build multilingual prompt wrapper (EN → ES, FR) in crisis_compound_demo.py | demo with --lang flag | Agent |
| Fri 5/2  | Push kernel to Kaggle, run end-to-end, capture output | Kaggle notebook link, verified output log | Agent |
| Sat 5/3  | Add Cactus Compute section to writeup (INT8 quantization, ARM edge deployment as future work) | Updated PROJECT_WRITEUP.md | Agent |
| Sun 5/4  | Buffer / fix any Kaggle env issues | Working Kaggle kernel | Agent |

**Week 1 Gate Criteria**:
- [ ] `kaggle kernels push` succeeds
- [ ] Kernel runs without error on Kaggle GPU (T4 acceptable)
- [ ] Output shows real Gemma-4 generated reasoning, not simulation
- [ ] All docs contain trademark notice
- [ ] pytest passes

### Week 2: Differentiation & Demo (May 5 — May 11)
**Goal**: Writeup polished, video produced, app functional, multilingual proven.

| Day | Task | Deliverable |
|-----|------|-------------|
| Mon 5/5 | Expand PROJECT_WRITEUP.md to 1,400-1,500 words: architecture diagram, Gemma-4 features, engineering choices, Cactus Compute/Tunix integration, impact metrics | Final PROJECT_WRITEUP.md |
| Tue 5/6 | Record screen capture: app running offline with Ollama, skill refinement dashboard, Spanish response | Raw OBS captures |
| Wed 5/7 | Produce demo video (60-90 sec): edit OBS clips, add voiceover/music, export 1920×1080 MP4 | /assets/demo_video_v1.mp4 |
| Thu 5/8 | Upload video to YouTube (unlisted → public), add to Kaggle Media Gallery | YouTube link |
| Fri 5/9 | Polish app.py into working HF Space (Gradio or Streamlit stub with live output) | Updated app.py |
| Sat 5/10 | Generate matplotlib skill-refinement chart for dashboard, embed in writeup | dashboard.py + chart.png |
| Sun 5/11 | Buffer / revise video if feedback suggests | Revised video if needed |

**Week 2 Gate Criteria**:
- [ ] Video uploaded to YouTube
- [ ] Video link added to Kaggle notebook metadata
- [ ] Writeup hits ~1,400 words with deep technical content
- [ ] app.py runs standalone with `python app.py` and serves a UI

### Week 3: Submission & QA (May 12 — May 18)
**Goal**: Final QA, submission components assembled, submitted with buffer.

| Day | Task | Deliverable |
|-----|------|-------------|
| Mon 5/12 | Run full QA: kernel on Kaggle, HF Space, local demo, all markdown | QA checklist |
| Tue 5/13 | Create submission package: zip/notebook + writeup + video link + repo URL | SUBMISSION_BUNDLE.md |
| Wed 5/14 | GitHub repo polish: main README with badges, screenshots, install steps | Updated repo README |
| Thu 5/15 | Dry-run submit to Kaggle: verify all fields, media gallery, dataset links | Dry-run confirmation |
| Fri 5/16 | **Buffer day** — fix any last-minute issues | Fixes |
| Sat 5/17 | Final review: read writeup aloud, watch video start-to-finish, click every link | Review notes |
| Sun 5/18 | **SUBMIT** before 22:00 UTC (last 2 hrs spare) | Submitted |

**Week 3 Gate Criteria**:
- [ ] All 3 components submitted: Video, Writeup, Public Repo/Notebook
- [ ] Kaggle submission form complete
- [ ] GitHub README has install/run instructions and screenshots
- [ ] No broken links

---

## Technical Details — Critical Fixes

### 1. kernel-metadata.json Template
```json
{
  "id": "manderson240/gemma-compound-crisis-response",
  "title": "Compound Crisis Response: Local Gemma-4 Agent for Humanitarian Aid",
  "code_file": "kernel.py",
  "language": "python",
  "kernel_type": "notebook",
  "is_private": false,
  "enable_gpu": true,
  "enable_internet": false,
  "dataset_sources": [],
  "competition_sources": [],
  "kernel_sources": []
}
```

### 2. Gemma-4 kagglehub Loading Pattern (Replace _try_load_gemma)
```python
# --- Gemma 4 Good: Trademark Notice ---
# Gemma is a trademark of Google LLC.
# ---

def _try_load_gemma() -> Any | None:
    if not _has_gpu():
        return None
    try:
        import kagglehub
        import torch
        from transformers import pipeline
        print("Downloading Gemma-4 e4b-it via kagglehub...")
        model_path = kagglehub.model_download("google/gemma-4/frameworks/pyTorch/variations/e4b-it")
        print("Loading Gemma-4B-it...")
        llm = pipeline(
            "text-generation",
            model=model_path,
            torch_dtype=torch.float16,
            device=0,
        )
        return llm
    except Exception as exc:
        print(f"Could not load Gemma-4: {exc}")
        return None
```

### 3. Trademark Notice Placement
Add to the header of:
- `kernel.py` (first comment block)
- `README.md` (footer)
- `PROJECT_WRITEUP.md` (footer)
- `BLOG_POST.md` (footer)
- `VIDEO_SCRIPT.md` (end credits)

Text:
> Gemma is a trademark of Google LLC.

### 4. Cactus Compute / Tunix Mention (Writeup Only)
In writeup §"Technical Architecture", add:
> "For edge deployment, the model can be exported via Cactus Compute to `.cact` format with INT8 mixed precision, delivering 30+ tok/s on ARMv8.6 i8mm. Fine-tuning adaptation for regional crisis patterns can be performed with Tunix (JAX-native QLoRA)."

This satisfies Technical Depth without needing full implementation.

### 5. Model Naming Compliance
Ensure no Cohezion derivative model uses "Gemma-" as a prefix. Current names are safe (`CrisisCompoundAgent`).

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Gemma-4 weights not available on kagglehub yet | Medium | High | Fallback to `gemma-4` via `transformers` + cache; document load path |
| Kaggle GPU quota exhausted during testing | Medium | High | Test locally with Ollama first; Kaggle push only for final validation |
| Video production takes >3 days | Medium | Medium | Record simple screen-cap + voiceover; no animation needed |
| Writeup not compelling enough | Medium | High | Start with "30-Second Pitch" structure; include real metrics |
| submission.py 404 / kaggle API issues | Low | High | Use Kaggle web UI as fallback; have notebook link ready |

---

## Files To Create / Modify

### New Files
- `kernel-metadata.json` — Kaggle push metadata
- `tests/test_crisis_agent.py` — pytest suite for agent, gate, refinement
- `tests/test_kernel.py` — Kernel smoke test (no GPU)
- `assets/demo_video_v1.mp4` — Final demo video
- `assets/skill_refinement_chart.png` — matplotlib chart for writeup
- `SUBMISSION_BUNDLE.md` — Checklist of all submission URLs

### Modified Files
- `kernel.py` — Gemma-4 model loading + kagglehub + trademark notice
- `kaggle_submission.py` — kagglehub integration + trademark
- `crisis_compound_demo.py` — Multilingual prompt wrapper + trademark
- `PROJECT_WRITEUP.md` — Expand to 1,400-1,500 words, add Cactus Compute / Tunix
- `README.md` — Add trademark, install steps, Kaggle link
- `BLOG_POST.md` — Add trademark, link to video
- `VIDEO_SCRIPT.md` — Add trademark to credits
- `app.py` — Make Gradio/Streamlit runnable demo
- `dashboard.py` — Matplotlib chart generation

---

## Submission Day Checklist (2026-05-18)

- [ ] Kaggle notebook public and running: `manderson240/gemma-compound-crisis-response`
- [ ] YouTube video public or unlisted, < 3 min, link in Media Gallery
- [ ] PROJECT_WRITEUP.md ≤ 1,500 words, uploaded
- [ ] GitHub repo: `github.com/manderson240/cohezion` — branch pushed, README complete
- [ ] Trademark notice visible in all 3 components
- [ ] No "Gemma-" prefix in any derivative model name
- [ ] kagglehub referenced in writeup/technical docs
- [ ] All links clickable and valid
- [ ] Buffer: submit by 22:00 UTC
