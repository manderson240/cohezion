---
stepsCompleted: [1, 2, 3, 4, 5]
inputDocuments:
  - docs/archive/FLUME_PAPER_DRAFT.md
  - docs/archive/FLUME_HF_MODEL_CARD.md
  - docs/blog/01_flume_thought_autoencoders.md
  - docs/blog/01_flume_triune_manifest.md
  - _bmad-output/project-context.md
  - _bmad-output/planning-artifacts/research/technical-marimo-reactive-notebooks-scientific-publications-research-2026-03-06.md
  - cloud-vault-mcp/vault/cortex/anthropic-research-engineer.md
date: 2026-03-23
author: Mike-anderson
project_name: concurrent-discovering-bubble
---

# Product Brief: FLUME VAE Research Showcase - Anthropic Interview Ready

## Executive Summary

The FLUME VAE Research Showcase transforms 18 months of production AI research into a single, evaluator-ready artifact for Anthropic's Research Engineer (Universes) application. Rather than promising 5 incomplete technologies, it delivers ONE complete research demonstration: a reproducible Marimo notebook showcasing hierarchical manifold compression (256D→512D→12D) with trained checkpoints, comprehensive tests, and technical documentation.

**Target Audience**: Anthropic's Universes team hiring managers and technical evaluators

**Success Metric**: Evaluator runs `marimo run notebooks/marimo/flume_showcase.py` and sees working research in <5 minutes

**Key Insight**: The technical work already exists (FLUME VAE implementation, 10 Marimo notebooks, 16MB checkpoint, 4,658 passing tests, 1,130 lines of docs). The gap is accessibility - making it evaluator-ready.

---

## Core Vision

### Problem Statement

Research engineer candidates with production-quality infrastructure struggle to showcase their work effectively to hiring teams. Current portfolio approaches either promise breadth without depth ("5 technologies coming soon!") or assume evaluators will navigate complex repositories without guidance. Anthropic's Universes team specifically seeks engineers who can "build robust infrastructure" and "communicate effectively" - but can't evaluate candidates when their strongest work is hidden behind inaccessible repos, unlinked notebooks, and unpublished documentation.

**Concrete Example**: An Anthropic evaluator visits the portfolio, sees 4/5 pillars marked "COMING SOON", clicks the one "LIVE" demo, and finds a 3D visualization with no context on how it was built, no reproducibility instructions, and no link to technical depth. First impression: vaporware. Reality: 10 working Marimo notebooks, trained checkpoints, and comprehensive docs exist but are invisible.

### Problem Impact

**For Candidates**:
- Applications filtered out due to poor presentation, not lack of technical depth
- Months of research work goes unevaluated because it's not accessible
- Cover letters claim "repository is live" but link to non-existent/private repos

**For Hiring Teams**:
- Can't verify technical claims without spending hours navigating undocumented codebases
- Miss strong candidates who built real infrastructure but presented it poorly
- Default to rejecting applications where work isn't immediately reproducible

**Quantified**: In this specific case, 10 Marimo notebooks + 16MB trained checkpoint + 1,130 lines of technical docs exist but are invisible to evaluators, creating a false negative risk.

### Why Existing Solutions Fall Short

**Approach 1: Breadth-First Portfolio (5 technology pillars)**
- ❌ Promises everything, delivers nothing evaluable
- ❌ "COMING SOON" signals incomplete work to hiring teams
- ❌ Evaluator has no clear entry point
- ❌ Hides strongest work behind placeholder cards

**Approach 2: GitHub-Only (link to repo)**
- ❌ Assumes evaluators will navigate complex directory structures
- ❌ No "start here" guide for non-contributors
- ❌ Requires 30+ minutes to understand what was built
- ❌ Private repos block evaluation entirely

**Approach 3: Documentation-Heavy (long PDFs)**
- ❌ Theory without runnable artifacts
- ❌ Claims not verifiable by evaluators
- ❌ No interactive exploration
- ❌ Reading takes hours, provides no hands-on experience

**Gap**: No existing approach combines interactive demo + technical depth + reproducibility + clear evaluation path in a single artifact optimized for hiring team evaluation.

### Proposed Solution

**FLUME VAE Research Showcase** - A complete, evaluator-ready research artifact built by assembling existing components:

**Core Experience** (5-minute path):
1. Evaluator clones public repo → runs `marimo run notebooks/marimo/flume_showcase.py`
2. Browser opens showing interactive 2D projection of 256D latent space with REAL trained checkpoint data
3. Can click "Read Technical Blog Post" → sees 458-line deep dive on VAE architecture with equations
4. Can click "View Test Suite" → sees 10 test files, 100% passing
5. Can click "Training From Scratch" → finds reproduction instructions

**Technical Components** (all exist, need assembly):
- Enhanced `flume_showcase.py` Marimo notebook loading real checkpoint
- Blog post `01_flume_thought_autoencoders.md` published at accessible URL
- `FLUME_README.md` with one-command setup and expected outputs
- Portfolio page updated: Remove 4 "COMING SOON" cards, focus on 1 complete artifact
- GitHub repo made public with "For Evaluators: Start Here" section

**Reproducibility Path**:
```bash
git clone https://github.com/[actual-username]/cohezion
cd cohezion
uv venv && source .venv/bin/activate && uv pip install -e .
marimo run notebooks/marimo/flume_showcase.py  # Works immediately, no config
```

**Differentiation**: Not a portfolio of promises - a single working research demonstration with production infrastructure, validated through 3 live competitions (Kaggle AGI, Luma AMD Speedrun, BlueQubit).

### Key Differentiators

**1. Already Built** (assembly, not creation):
- 10 Marimo notebooks exist → enhance one (`flume_showcase.py`)
- 16MB trained checkpoint exists → load it in notebook
- 1,130 lines of docs exist → make them accessible
- 4,658 tests exist → link them prominently
- **Time to complete**: 6-8 hours (assembly) vs. months (building from scratch)

**2. Competition-Validated**:
- Kaggle Measuring AGI: R-Zero self-evolving loop (0.5-coherence traps)
- Luma AMD Speedrun: K-Search world model (510 cycles, 157 prunes)
- BlueQubit Quantum: "Little Dimple" optimization
- **Differentiator**: Not toy examples - real competition entries proving it works under pressure

**3. Production Infrastructure**:
- 579 Python modules with mypy --strict (100% type coverage)
- 4,658 tests at 99.9% pass rate
- Async I/O, circuit breakers, cost-aware routing
- **Differentiator**: Research-grade code quality, not academic prototypes

**4. Interactive Reproducibility**:
- Marimo notebooks with PEP 723 inline dependencies
- One-command setup: `marimo run notebooks/marimo/flume_showcase.py`
- No Docker, no config files, no setup headaches
- **Differentiator**: Evaluators see working results in <5 minutes, not hours

**5. Research Depth**:
- 458-line technical blog post with VAE architecture equations
- Explains not just "what" but "why" (Percival's Triune Self philosophy)
- Links theory (continuous latent spaces) to practice (coherence tracking in agents)
- **Differentiator**: Shows ability to communicate complex ideas clearly (Anthropic values this highly)

**Why This Matters for Anthropic's Universes Team**:
- **Job Requirement**: "Train AI models to perform complex, difficult, long-horizon agentic tasks"
- **Your Evidence**: 3 competition entries are exactly this - long-horizon tasks under real constraints
- **Job Requirement**: "Strong software engineering skills and can build robust infrastructure"
- **Your Evidence**: 4,658 tests, mypy strict, production patterns
- **Job Requirement**: "Greatly value communication skills"
- **Your Evidence**: 1,130 lines of technical docs + interactive notebooks

**Unfair Advantage**: You already did the hard part (building it). The easy part (making it accessible) is 6-8 hours of assembly work, not months of research.

---

## Target Users

### Primary Users

**Persona 1: Dr. Sarah Chen - Senior Research Engineer (Technical Evaluator)**

Dr. Chen is a Research Engineer on Anthropic's Universes team with 8 years of experience in machine learning infrastructure. She reviews 5-10 candidate portfolios per week, spending 30-45 minutes per evaluation. Her background includes distributed systems, model training infrastructure, and production ML deployment.

**Problem Experience**:
Currently, Sarah wastes 15-20 minutes per candidate navigating unclear repositories, trying to find working examples, and verifying claims. She's frustrated by candidates who claim "production-ready" without providing reproducibility instructions. When she encounters a private GitHub repo or broken demo link, she immediately deprioritizes that application - not because the candidate lacks skills, but because she can't verify them.

**Success Vision**:
Sarah would say "this is exactly what I needed" when she can:
1. Clone a repo and run ONE command to see working research
2. Verify production infrastructure claims through actual test output
3. Read technical depth (equations, architecture decisions) without digging through code
4. Reproduce results deterministically (checkpoints + seeds provided)
5. Assess communication skills through clear documentation

**What Motivates Her**:
- Finding candidates who can ship production research, not just write papers
- Evidence of systems thinking (tests, type safety, error handling)
- Clear communication - can this person explain complex ideas to the team?
- Reproducibility - does the research actually work or is it vaporware?

---

**Persona 2: Alex Rodriguez - Universes Team Hiring Manager**

Alex manages the Universes team hiring pipeline, reviewing 50+ applications per week with only 5-10 minutes per portfolio during initial screening. They need to quickly identify candidates with both technical depth AND communication skills to pass to Sarah for detailed technical review.

**Problem Experience**:
Alex sees endless portfolios that look impressive at first glance but collapse under scrutiny: "COMING SOON" badges on 80% of features, GitHub links to private repos, claims of "10K tests passing" with no evidence, or beautiful UI with no working functionality. They waste hours passing candidates to technical reviewers only to hear "I can't evaluate this - nothing works."

**Success Vision**:
Alex would say "this is exactly what I needed" when they can:
1. See ONE complete artifact (not 5 promised technologies)
2. Click a live demo that works immediately (no setup required)
3. Scan technical accomplishments backed by evidence (competition results, test counts)
4. Assess fit with job requirements in <5 minutes
5. Confidently pass to technical review knowing it's reproducible

**What Motivates Them**:
- Reducing false positives (impressive-looking portfolios that don't work)
- Identifying "builders" who ship complete artifacts, not just prototypes
- Finding candidates who understand production constraints (cost, latency, reliability)
- Clear signal-to-noise ratio - evidence over promises

---

### Secondary Users

**Persona 3: Jamie Liu - Anthropic HR Coordinator**

Jamie coordinates interview scheduling and candidate communication. They need to quickly understand a candidate's core strengths to brief interview panels. When portfolios are unclear or link to inaccessible repos, Jamie can't provide context to interviewers, making the interview process less efficient.

**What They Need**:
- Clear executive summary they can read in 2 minutes
- Evidence of key qualifications (competitions, production systems, communication skills)
- Working contact information and accessible references
- No broken links or placeholder content

---

**Persona 4: Dr. Marcus Williams - Peer Researcher (Future Colleague)**

Marcus is a Research Engineer who would potentially work alongside the candidate. He's interested in the candidate's research depth, code quality standards, and ability to collaborate. He reviews candidates after they pass initial screening, looking for evidence of:
- Novel research contributions (not just reimplementing papers)
- Production-grade engineering (not academic prototypes)
- Clear documentation (can they onboard others to their work?)
- Intellectual rigor (equations, theoretical grounding, careful evaluation)

---

### User Journey

**Stage 1: Discovery (Alex - Hiring Manager)**

*How they find it*:
- Application submitted → Alex opens portfolio link from cover letter
- First impression: Portfolio homepage, scans in 30 seconds

*Critical decision point*:
- If they see 4/5 "COMING SOON" cards → deprioritized immediately
- If they see 1 complete artifact with "Run This Yourself" → interested, click through

*Success criteria*:
- Portfolio loads in <3 seconds
- Executive summary answers "What did you build?" in 1 paragraph
- Clear evidence of job requirement match (competitions, infrastructure, communication)

---

**Stage 2: Initial Evaluation (Alex → Sarah handoff)**

*Alex's actions*:
1. Scans portfolio (2 minutes)
2. Clicks live demo - does it work? (1 minute)
3. Checks GitHub - is it public? Can they see tests? (2 minutes)
4. Decision: Pass to Sarah for technical review OR deprioritize

*Handoff to Sarah*:
- Alex sends link with note: "Candidate built VAE for agent reasoning, has working demo and 4,658 tests. Worth detailed review."

---

**Stage 3: Technical Deep Dive (Sarah - Technical Evaluator)**

*Sarah's evaluation path*:
1. **5 minutes - Quick reproducibility check**:
   ```bash
   git clone [repo]
   marimo run notebooks/marimo/flume_showcase.py
   ```
   - Does it work without configuration?
   - Does it load real data (not synthetic)?
   - Is the output meaningful?

2. **10 minutes - Code quality assessment**:
   - Runs test suite: `uv run pytest tests/ -q`
   - Checks type coverage: `mypy --strict src/`
   - Scans architecture: Are patterns production-grade? (async, error handling, observability)

3. **15 minutes - Research depth evaluation**:
   - Reads technical blog post (458 lines)
   - Checks if equations are correct (VAE loss, KL divergence)
   - Evaluates novelty: Is this just reimplementing a paper or new contribution?

4. **10 minutes - Communication assessment**:
   - Documentation clarity: Can a peer understand this?
   - Marimo notebook pedagogical quality: Could this be used for onboarding?
   - GitHub README: Is there a "For Evaluators" section?

*Sarah's decision*:
- **Strong yes**: Working demo + production infrastructure + clear communication → advance to interview
- **No**: Can't reproduce, unclear documentation, or claims don't match evidence → reject
- **Maybe**: Impressive tech but missing key evidence → request clarification

---

**Stage 4: "Aha!" Moment (The Tipping Point)**

For **Alex**: "Finally, a candidate who built ONE thing completely instead of promising five things incompletely."

For **Sarah**: "This isn't just a toy VAE - they're using it in production for agent coherence tracking. The checkpoint loads, tests pass, and the blog post shows they understand the theory deeply."

For **Marcus** (peer review): "The HIHO stability insight (0.5 coherence optimal) is novel and well-explained. This person can contribute original research AND build production systems."

---

**Stage 5: Long-term Value (Post-Hire)**

*How the showcase continues to provide value*:
- Marimo notebooks become onboarding material for new Universes team members
- FLUME VAE architecture informs Anthropic's internal agent observability tools
- Candidate's competition experience (Kaggle AGI, Luma AMD) demonstrates ability to ship under pressure
- Clear documentation style becomes team standard

---

## Success Metrics

### User Success Metrics

**Primary Success Metric (Alex - Hiring Manager Path)**:
- **Metric**: Time from portfolio landing → decision to pass to technical review
- **Target**: <5 minutes
- **Measurement**: Portfolio analytics + hiring pipeline tracking
- **Success Indicator**: Alex can answer "Does this candidate demonstrate production research skills?" in <5 minutes

**Secondary Success Metric (Sarah - Technical Evaluator Path)**:
- **Metric**: Time from repo clone → reproducible demo running locally
- **Target**: <5 minutes (one command: `marimo run notebooks/marimo/flume_showcase.py`)
- **Measurement**: Setup friction logs, evaluator feedback
- **Success Indicator**: Sarah sees working FLUME VAE demo with real checkpoint data without configuration

**Depth Evaluation Metric (Sarah - Research Assessment)**:
- **Metric**: Evaluator completes full assessment (demo + tests + blog post + code quality) within allocated time
- **Target**: 40 minutes total
- **Breakdown**:
  - 5 min: Reproducibility check (notebook runs)
  - 10 min: Code quality (test suite, type coverage)
  - 15 min: Research depth (blog post, equations, novelty)
  - 10 min: Communication assessment (docs, README)
- **Success Indicator**: Sarah can confidently recommend "advance to interview" or "reject" based on complete evidence

**Verification Metric (Claims vs Reality)**:
- **Metric**: % of portfolio claims verifiable within 40-minute evaluation
- **Target**: 100% (4,658 tests claim → test suite runs and shows count; checkpoint claim → checkpoint loads; competition claim → results linked)
- **Measurement**: Evaluator checklist verification
- **Success Indicator**: Zero "I can't verify this claim" blockers

---

### Business Objectives

**Objective 1: Reduce False Negative Rate**
- **Goal**: Prevent strong candidates from being filtered out due to poor presentation
- **Current State**: Portfolio shows 4/5 "COMING SOON" → evaluator assumes incomplete work → reject
- **Target State**: Portfolio shows 1 complete artifact → evaluator sees production quality → advance to interview
- **Measurement**: Application progresses to technical review stage

**Objective 2: Maximize Signal-to-Noise Ratio**
- **Goal**: Every element evaluators interact with provides hiring-relevant signal
- **Current State**: Beautiful 3D visualization with no context on how it was built
- **Target State**: Every link (demo, tests, blog, GitHub) directly demonstrates job requirements
- **Measurement**: Evaluator spends 0 minutes on irrelevant content

**Objective 3: Demonstrate Job Requirement Match**
- **Goal**: Provide evidence for all 3 key requirements (long-horizon tasks, robust infrastructure, communication)
- **Anthropic Requirements**:
  1. "Train AI models to perform complex, difficult, long-horizon agentic tasks"
  2. "Strong software engineering skills and can build robust infrastructure"
  3. "Greatly value communication skills"
- **Evidence Provided**:
  1. 3 competition entries (Kaggle AGI, Luma AMD, BlueQubit) - long-horizon tasks under constraints
  2. 4,658 tests at 99.9% pass rate, mypy --strict, production patterns - robust infrastructure
  3. 1,130 lines of technical docs + interactive notebooks - clear communication
- **Measurement**: Evaluator feedback explicitly mentions all 3 requirements as strengths

---

### Key Performance Indicators

**KPI 1: Reproducibility Success Rate**
- **Definition**: % of evaluators who successfully run `marimo run notebooks/marimo/flume_showcase.py` without errors
- **Target**: 100% (no configuration required, dependencies inline via PEP 723)
- **Measurement**: Notebook execution logs, evaluator feedback
- **Leading Indicator**: Local testing on fresh VM shows zero-config success

**KPI 2: Evaluation Completion Rate**
- **Definition**: % of evaluators who complete all 4 assessment areas (demo, tests, research depth, communication) within 40 minutes
- **Target**: 100%
- **Breakdown**:
  - Demo works: 100% (checkpoint loads, visualization renders)
  - Tests pass: 100% (4,658/4,658 passing, <90 seconds runtime)
  - Research depth accessible: 100% (blog post linked, equations render, novelty clear)
  - Communication quality evident: 100% (README, docs, notebook comments clear)
- **Measurement**: Evaluator checklist completion

**KPI 3: Technical Depth Validation**
- **Definition**: Evaluator can verify novel research contribution (HIHO stability at 0.5 coherence)
- **Target**: 100% of evaluators who read blog post understand the core insight
- **Measurement**: "The HIHO stability insight (0.5 coherence optimal) is novel and well-explained" - explicit evaluator feedback
- **Validation**: Blog post includes equations, experimental results, theoretical grounding

**KPI 4: Production Quality Evidence**
- **Definition**: Evaluator can verify production-grade engineering claims
- **Checklist**:
  - ✅ Test suite runs: `uv run pytest tests/ -q` shows 4,658 passing
  - ✅ Type coverage: `mypy --strict src/` shows 100% coverage
  - ✅ Production patterns: Code review shows async/await, circuit breakers, observability
  - ✅ Real deployments: 3 competition entries link to actual submissions
- **Target**: 100% of checklist items verifiable in <10 minutes
- **Measurement**: Evaluator verification log

**KPI 5: First Impression Conversion**
- **Definition**: Time from portfolio landing → "this looks promising, let me investigate"
- **Target**: <30 seconds
- **Trigger**: Clear executive summary + "Run This Yourself" CTA + working demo link
- **Measurement**: Hiring manager (Alex persona) decision log
- **Success**: Alex moves from scan to click-through within 30 seconds

---

**Strategic Alignment:**

These metrics connect to the core vision of transforming hidden production research into evaluator-ready artifacts:
- **User Success**: Evaluators verify claims in <5 minutes (quick check) and assess depth in 40 minutes (complete evaluation)
- **Business Success**: Strong candidate advances instead of being filtered out due to presentation gaps
- **Validation**: 100% reproducibility + 100% claim verification + complete assessment achievable in allocated time

---

## MVP Scope

### Core Features

**1. Enhanced Marimo Notebook (`flume_showcase.py`)**
- Loads real checkpoint (`data/flume/checkpoints/flume_vae_ep50.pt`)
- Displays actual training metrics (MSE 0.1322, KL divergence 0.4329, 50 epochs)
- Interactive 2D/3D visualization of 256D latent space
- Embedded documentation explaining what evaluator is seeing
- **Delivery**: ~3 hours (modify existing notebook, load checkpoint, add docs)

**2. Reproducibility README (`FLUME_README.md`)**
- One-command setup: `marimo run notebooks/marimo/flume_showcase.py`
- Expected output description with screenshots
- Troubleshooting section (common issues + fixes)
- Link to test suite verification
- **Delivery**: ~1 hour (document existing working setup)

**3. Published Technical Blog Post**
- `docs/blog/01_flume_thought_autoencoders.md` accessible at stable URL
- Equations render correctly (KaTeX for math)
- Code examples have syntax highlighting
- Link from Marimo notebook to blog post
- **Delivery**: ~2 hours (Next.js MDX page + styling)

**4. Portfolio Page Updates**
- Remove 4 "COMING SOON" cards (focus on FLUME only)
- Add "For Evaluators: Run This Yourself" section
- Link to enhanced Marimo notebook, blog post, and test suite
- Clear executive summary (2-minute read)
- **Delivery**: ~1 hour (simplify existing page)

**5. GitHub Repository Accessibility**
- Make repo public OR update all links to correct accessible URL
- Add "For Evaluators: Start Here" section to README.md
- Verify test suite runs on fresh clone
- **Delivery**: ~1 hour (repo settings + README update)

**Total MVP Delivery Estimate**: 6-8 hours

---

### Out of Scope for MVP

**1. Additional Marimo Notebooks** - 10 notebooks exist but won't be enhanced (1 complete > 10 partial)
**2. Other Pillar Showcases** - Swarm/Compound/Mycelium/R-Zero showcases deferred to V2
**3. Interactive Blog Features** - No embedded code playgrounds (blog for reading, notebook for interaction)
**4. Automated Testing** - No CI/CD for notebook execution (manual verification sufficient)
**5. Multiple Checkpoints** - Only final checkpoint (epoch 50), not intermediate training states
**6. Video Walkthrough** - Written instructions + working demo sufficient

---

### MVP Success Criteria

**Gate 1: Technical Validation (Self-Test)**
- ✅ Fresh VM clone → `marimo run notebooks/marimo/flume_showcase.py` → works in <5 minutes
- ✅ Checkpoint loads → visualization renders → metrics display
- ✅ Blog post accessible → equations render → code highlights
- ✅ Test suite runs → 4,658 passing → <90 seconds

**Gate 2: Peer Review (Simulated Evaluator)**
- ✅ Colleague unfamiliar with project follows evaluator journey (40 minutes)
- ✅ Can clone, run, verify claims without getting blocked
- ✅ Can assess technical depth from artifacts alone

**Gate 3: Application Progression (Real Outcome)**
- ✅ Application advances to technical interview (not filtered out)
- ✅ Interviewer references specific artifacts (notebook, blog, competitions)
- ✅ Interview focuses on research depth, not "show me something that works"

**Metrics Thresholds:**
- Reproducibility: 100% success rate
- Verification: 100% of claims verifiable
- Evaluation Time: <5 min (Alex) + <40 min (Sarah)
- Signal Quality: Zero wasted evaluator time

---

### Future Vision

**Phase 2: Multi-Pillar Portfolio (3-6 months post-hire)**
- Replicate FLUME pattern for Compound, Swarm, Mycelium, R-Zero
- Each pillar meets 100% reproducibility standard

**Phase 3: Platform for Research Communication (6-12 months)**
- "Fork this portfolio" template for other researchers
- Automated reproducibility checker (CI/CD for research)
- 10+ researchers adopt pattern

**Phase 4: Anthropic Internal Tooling (post-hire)**
- FLUME VAE informs agent observability tools
- Notebooks become team onboarding material
- HIHO stability tested in Anthropic's agent training

**Long-Term Vision (2-3 years):**
- Portfolio evolves into "Research Transparency Standard"
- Publications include executable artifacts
- Hiring prioritizes reproducible demos over papers

---
