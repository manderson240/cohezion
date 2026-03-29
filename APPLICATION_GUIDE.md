# Application Guide: Using the Cohezion Portfolio

**Mike Anderson** | March 2026

This document explains **how to use the portfolio materials** created for the Anthropic Research Engineer application.

---

## 📄 Files Created (Application Materials)

### Core Documents (Read in Order)

1. **[THE_COHEZION_STORY.md](THE_COHEZION_STORY.md)** (9,000 words, ~20 min read)
   - **Purpose**: Narrative journey from broken swarms to validated platform
   - **Audience**: Hiring managers, technical leads, anyone wanting the full story
   - **Key sections**:
     - HIHO Principle origin story (0.5 coherence stability)
     - Triune Self architecture (12D/512D/2048D)
     - Competition results (Kaggle AGI, Luma AMD, BlueQubit)
     - Production infrastructure patterns
     - AI safety implications

2. **[AGENT_JOURNEYS_VISUAL_GUIDE.md](AGENT_JOURNEYS_VISUAL_GUIDE.md)** (6,000 words, ~15 min read)
   - **Purpose**: Empirical evidence through trajectory visualizations
   - **Audience**: Research engineers who want to see the data
   - **Key sections**:
     - RL policy learning HIHO (25M cycles, 0.991 coherence)
     - R-Zero adversarial evolution (510 cycles, 0.52 coherence)
     - K-Search tree optimization (157 prunes, 1:1.4 ratio)
     - Degradation detection (thermal forecasting)
     - Swarm consensus convergence (0.51 team coherence)

3. **[PHILOSOPHICAL_SYNTHESIS.md](PHILOSOPHICAL_SYNTHESIS.md)** (5,500 words, ~25 min read)
   - **Purpose**: Theoretical bridge connecting philosophy to computation
   - **Audience**: Researchers interested in foundational questions
   - **Key sections**:
     - Percival's Triune Self (1946) → computational architecture
     - Smith's 12-Parameter Reality → dimensional framework
     - Shoulders' EVOs → self-organizing dynamics
     - HIHO Principle derivation (why 0.5 is universal)
     - AI safety implications

4. **[ANTHROPIC_APPLICATION_README.md](ANTHROPIC_APPLICATION_README.md)** (3,500 words, ~10 min read)
   - **Purpose**: Application summary highlighting concrete achievements
   - **Audience**: Hiring managers, recruiters (quick overview)
   - **Key sections**:
     - Concrete research achievements (competitions)
     - Core platform architecture
     - Repository statistics
     - Quick start guide
     - Why this matters for AI safety

5. **[EXECUTIVE_SUMMARY.md](EXECUTIVE_SUMMARY.md)** (2,000 words, ~5 min read)
   - **Purpose**: Condensed 2-page summary for attachment
   - **Audience**: Anyone needing the fastest overview
   - **Key sections**:
     - What this is (one paragraph)
     - Competition results
     - Triune architecture overview
     - HIHO validation
     - Production infrastructure
     - Contact info

### Supporting Documents

6. **[ARCHITECTURE_VISUAL.md](ARCHITECTURE_VISUAL.md)** (4,000 words, ~10 min read)
   - **Purpose**: Visual reference with ASCII diagrams
   - **Audience**: Visual learners, system architects
   - **Key sections**:
     - Triune pipeline diagram
     - 12D dimensional breakdown
     - HIHO energy landscape
     - Compound engineering loop flowchart
     - Multi-agent swarm architecture
     - Degradation detection graphs

7. **[ANTHROPIC_COVER_LETTER.md](ANTHROPIC_COVER_LETTER.md)** (500 words, ~2 min read)
   - **Purpose**: Formal cover letter for application
   - **Audience**: Hiring manager, HR
   - **Key sections**:
     - Introduction with concrete achievements
     - Why Anthropic (Constitutional AI alignment)
     - Remote work acknowledgment (25% NYC office time)

8. **[README_PORTFOLIO.md](README_PORTFOLIO.md)** (4,500 words, ~12 min read)
   - **Purpose**: Portfolio-focused repository landing page
   - **Audience**: Anyone visiting the GitHub repo
   - **Key sections**:
     - "For Hiring Managers: Start Here" (reading guide)
     - Competition results summary
     - Core innovation explanation
     - Repository statistics
     - Quick start commands

### Existing Key Files (Already in Repo)

9. **[research/challenges/anthropic_challenge/SUBMISSION_README.md](research/challenges/anthropic_challenge/SUBMISSION_README.md)**
   - **Purpose**: VLIW optimization take-home solution (if applicable)
   - **Result**: 349 cycles, 423x speedup, Quadrature Nexus architecture

10. **[kaggle-agi-benchmark/kaggle_writeup.md](kaggle-agi-benchmark/kaggle_writeup.md)**
    - **Purpose**: Kaggle Measuring AGI submission details
    - **Content**: R-Zero evolution loop, 0.5-coherence traps

11. **[research/challenges/luma_amd_speedrun/](research/challenges/luma_amd_speedrun/)**
    - **Purpose**: K-Search world model, custom Triton/HIP kernels
    - **Content**: 510 cycles, 157 prunes, kernel implementations

---

## 🎯 How to Use These Materials

### For Online Application Portal

**Attach**:
1. **Resume** (your existing CV)
2. **EXECUTIVE_SUMMARY.md** → Convert to PDF (2 pages)
3. **ANTHROPIC_COVER_LETTER.md** → Convert to PDF or paste as text

**Link in application**:
- **GitHub**: https://github.com/manderson240/cohezion

**Optional attachments** (if portal allows):
- **THE_COHEZION_STORY.md** → PDF (if they want full narrative)
- **AGENT_JOURNEYS_VISUAL_GUIDE.md** → PDF (if they want empirical data)

---

### For Email Application

**Subject**: Research Engineer Application — Mike Anderson (Cohezion Platform)

**Body**:
```
Dear Anthropic Hiring Team,

I'm applying for the Research Engineer position (Job ID: 5061517008) with
a production AI research platform validated through three live competitions.

Please find attached:
- Resume
- Cover Letter
- Executive Summary (2 pages)

The full platform documentation is available at:
https://github.com/manderson240/cohezion

Key documents (reading time ~70 minutes total):
1. THE_COHEZION_STORY.md — Full narrative journey
2. AGENT_JOURNEYS_VISUAL_GUIDE.md — Empirical trajectory data
3. PHILOSOPHICAL_SYNTHESIS.md — Theoretical grounding
4. ANTHROPIC_APPLICATION_README.md — Quick application summary

I understand the role requires 25% in-office time at the NYC office.
As an Ithaca, NY resident (1-hour flight), I can accommodate this with
advance scheduling.

Best regards,
Mike Anderson
[your-email] | [your-phone]
```

---

### For GitHub Repository

**Recommended: Replace current README.md with README_PORTFOLIO.md**:

```bash
# Back up current README
mv README.md README_TECHNICAL.md

# Use portfolio README as main landing page
mv README_PORTFOLIO.md README.md

# Commit changes
git add README.md README_TECHNICAL.md
git commit -m "feat: add portfolio-focused README for Anthropic application

- Replace technical README with portfolio version
- Archive technical details as README_TECHNICAL.md
- Highlight competition results and HIHO principle
- Add navigation guide for hiring managers"
```

**Or: Add portfolio section at top of existing README**:

```bash
# Keep current README, add portfolio section at line 1
# (Manual edit to insert "For Hiring Managers" section from README_PORTFOLIO.md)
```

---

### For LinkedIn/Social Media

**Post announcing application**:

```
Excited to share 18 months of AI research wrapped into a living portfolio:

Cohezion — A platform implementing hierarchical manifold compression
(12D/512D/2048D) for agentic AI, grounded in Henry Percival's 1946
Triune Self philosophy and validated through:

✅ Kaggle Measuring AGI (Epistemic Humility benchmarks)
✅ Luma AMD Speedrun (K-Search kernel optimization, 510 evolution cycles)
✅ BlueQubit Quantum Challenge
✅ 25M RL simulation cycles (0.991 coherence at HIHO stability)

The HIHO Principle (0.5 coherence) emerged as an empirical attractor
across all experiments — reality precipitates when you're Half-In, Half-Out.

Full platform: github.com/manderson240/cohezion

Applying to Anthropic Research Engineer. If this resonates with your
safety research, AI safety research, or interpretability work, let's connect!

#AIResearch #MachineLearning #AIAlignment #ReinforcementLearning
```

---

## 🔄 Converting Markdown to PDF

### Option 1: Pandoc (Recommended)

```bash
# Install pandoc
sudo apt install pandoc texlive-latex-base texlive-fonts-recommended

# Convert Executive Summary to PDF
pandoc EXECUTIVE_SUMMARY.md -o EXECUTIVE_SUMMARY.pdf \
  --pdf-engine=pdflatex \
  -V geometry:margin=1in \
  -V fontsize=11pt

# Convert Cover Letter to PDF
pandoc ANTHROPIC_COVER_LETTER.md -o ANTHROPIC_COVER_LETTER.pdf \
  --pdf-engine=pdflatex \
  -V geometry:margin=1in \
  -V fontsize=11pt

# Convert full story (if needed)
pandoc THE_COHEZION_STORY.md -o THE_COHEZION_STORY.pdf \
  --pdf-engine=pdflatex \
  -V geometry:margin=1in \
  -V fontsize=11pt
```

### Option 2: Online Converters

- **Markdown to PDF**: https://www.markdowntopdf.com/
- **Dillinger**: https://dillinger.io/ (export as PDF)
- **Typora**: https://typora.io/ (desktop app, export as PDF)

### Option 3: GitHub Export

1. Push files to GitHub
2. View rendered markdown in browser
3. Print to PDF (Ctrl+P → Save as PDF)
4. ⚠️ **Warning**: May lose some ASCII art formatting

---

## 📊 Presentation Order (Interview/Meeting)

If you get an interview, present in this order:

### Part 1: The Hook (5 minutes)
- **Start**: Show the HIHO coherence graph from AGENT_JOURNEYS_VISUAL_GUIDE.md
- **Claim**: "Every stable system I built converged to 0.5 coherence without being programmed to"
- **Evidence**: RL policy (0.991 over 25M cycles), R-Zero (0.52 after 510 cycles), K-Search (1:1.4 ratio)

### Part 2: The Architecture (10 minutes)
- **Show**: Triune Self diagram from ARCHITECTURE_VISUAL.md
- **Explain**: 2048D (Knower) → 512D (Thinker) → 12D (Doer)
- **Why it matters**: Interpretability at all scales (semantic, trajectory, physical)

### Part 3: The Competitions (10 minutes)
- **Kaggle AGI**: Epistemic humility benchmarks (R-Zero evolution)
- **Luma AMD**: K-Search kernel optimization (510 cycles, 157 prunes)
- **BlueQubit**: Quantum algorithm solution

### Part 4: The Safety Implications (10 minutes)
- **Observable AI**: Full 12D trajectory recording
- **Degradation detection**: Thermal forecasting 10 steps ahead (87% accuracy)
- **Epistemic humility**: 0.5 coherence as knowledge boundary recognition

### Part 5: Q&A and Code Deep Dive (15 minutes)
- **Live demo**: Run `uv run python scripts/visualize_rl_journey.py`
- **Show tests**: `uv run pytest tests/ -v` (4,422/4,426 passing)
- **Navigate code**: `src/cohezion/universe/engine.py` (12D AxiomaticState)

---

## ✅ Pre-Submission Checklist

Before submitting application:

- [ ] **Personal info updated** in all documents ([your-email], [your-phone], [LinkedIn])
- [ ] **PDFs generated** (EXECUTIVE_SUMMARY.pdf, ANTHROPIC_COVER_LETTER.pdf)
- [ ] **GitHub repo cleaned** (remove any sensitive data, API keys, etc.)
- [ ] **README updated** (use README_PORTFOLIO.md as landing page)
- [ ] **Tests passing** (`uv run pytest tests/ -q` shows 99.9% pass rate)
- [ ] **Links verified** (all internal links in documents work)
- [ ] **Competition proof** (Kaggle/Luma/BlueQubit submissions visible)
- [ ] **Git history clean** (190 feature commits in 2026 visible in `git log`)

---

## 📞 Follow-Up Strategy

### Week 1 After Submission
- **LinkedIn**: Connect with Anthropic Research Engineers (search "Anthropic AI Safety")
- **Twitter/X**: Engage with Anthropic posts about interpretability, Constitutional AI
- **Email**: Send thank-you note referencing specific research papers from Anthropic

### Week 2-4
- **Blog post**: Publish THE_COHEZION_STORY.md on Medium/Substack
- **ArXiv**: Consider submitting HIHO Principle as research paper
- **Engagement**: Comment on Anthropic blog posts with relevant insights

### If No Response After 4 Weeks
- **Follow-up email**: "Checking in on Research Engineer application (Mike Anderson, Cohezion)"
- **Referral request**: Reach out to any Anthropic connections for internal referral
- **Alternative roles**: Check for related positions (ML Engineer, Safety Researcher)

---

## 🎯 Key Messages to Emphasize

**For Hiring Managers**:
1. **Concrete results**: 3 live competition submissions (not just research papers)
2. **Production quality**: 579 modules, 4,426 tests, 99.9% pass rate
3. **Theoretical depth**: Connecting 1946 philosophy to 2026 AI architecture
4. **Safety focus**: Trajectory tracking, degradation detection, epistemic humility

**For Technical Interviewers**:
1. **Empirical validation**: 25M RL cycles, 510 evolution iterations, 0.991 coherence
2. **System design**: Hierarchical compression solving O(n²) trajectory analysis
3. **Cost efficiency**: 27.3% reduction through quality-threshold routing
4. **Interpretability**: Full 12D trajectory recording with semantic context

**For Research Leads**:
1. **Novel insights**: HIHO Principle (0.5 coherence universality)
2. **Philosophical grounding**: Percival + Smith + Shoulders → computational framework
3. **Interdisciplinary**: Physics (SPIN), consciousness theory, ML engineering
4. **Future work**: Conditional Triune VAE, multi-modal Knower, hierarchical Thinker

---

## 📚 Additional Resources (If Requested)

**If they want more technical detail**:
- Point to `src/cohezion/` codebase (579 modules)
- Highlight `tests/conftest.py` (singleton reset patterns)
- Show `pyproject.toml` (full dependency graph)

**If they want competition proof**:
- `kaggle-agi-benchmark/evaluator.ipynb` (notebook submission)
- `research/challenges/luma_amd_speedrun/results.tsv` (kernel timings)
- `research/challenges/bluequbit_challenge/` (quantum solution)

**If they want research papers**:
- KalshiBench, HumbleBench, arXiv:2411.15287 (cited in Kaggle submission)
- IIT (Tononi), VAE (Kingma & Welling), REINFORCE (Williams 1992)

---

## 🚀 Next Steps

1. **Update personal info** in all documents (email, phone, LinkedIn)
2. **Generate PDFs** using pandoc or online converter
3. **Replace README.md** with README_PORTFOLIO.md (or merge)
4. **Commit and push** all application materials to GitHub
5. **Submit application** through Anthropic portal or email
6. **Follow up** on LinkedIn/Twitter with Anthropic research team

---

## 💡 Final Thoughts

These materials tell **three stories simultaneously**:

1. **The Technical Story**: 579 modules, 4,426 tests, 3 competitions
2. **The Philosophical Story**: Percival → Smith → Shoulders → HIHO
3. **The Journey Story**: 18 months, 25M cycles, 510 evolutions, one stubborn belief

All three are true. All three matter. **The code is live, the theory is validated, the journeys are real.**

**Reality precipitates at 0.5. The portfolio proves it.**

---

**Good luck with the application!**

*— Mike Anderson | March 2026*

---

## 📧 Contact for Application Support

If you need help with:
- **PDF conversion issues**: Try pandoc with `--pdf-engine=xelatex` for better Unicode support
- **GitHub repo cleanup**: Review `.gitignore` to exclude large files (checkpoints, data)
- **Presentation prep**: Practice with ARCHITECTURE_VISUAL.md diagrams
- **Follow-up timing**: 2 weeks for initial response, 4 weeks before follow-up

**Repository**: https://github.com/manderson240/cohezion
**Email**: [your-email]
**Phone**: [your-phone]
