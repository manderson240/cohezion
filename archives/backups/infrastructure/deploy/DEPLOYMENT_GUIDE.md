# Portfolio Deployment Guide

**One-command deployment for Cohezion dashboard + documentation**

---

## Quick Start (3 Commands)

```bash
# 1. Deploy dashboard to Vercel
cd src/web/anima_dashboard && vercel deploy --prod

# 2. Export training data
cd /home/mike-anderson/dev/cohezion && uv run python -m cohezion.llm_training_bridge export-all

# 3. Verify deployment
curl https://cohezion.vercel.app/api/health
```

---

## Prerequisites

### 1. Vercel Account

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login
```

### 2. Build Dependencies

```bash
cd src/web/anima_dashboard
npm install  # or bun install
```

### 3. API Backend

The dashboard hits `http://localhost:8080` by default. For production:

```bash
# Start API server
uv run python -m cohezion.api.server --host 0.0.0.0 --port 8080
```

Or deploy API separately (Render, Railway, Fly.io).

---

## Dashboard Deployment

### Option 1: Vercel (Recommended)

**Step 1:** Create `vercel.json`:

```json
{
  "buildCommand": "next build",
  "outputDirectory": ".next",
  "devCommand": "next dev",
  "installCommand": "npm install",
  "framework": "nextjs",
  "regions": ["iad1"]
}
```

**Step 2:** Deploy:

```bash
cd src/web/anima_dashboard
vercel --prod
```

**Step 3:** Custom domain (optional):

```bash
vercel domains add cohezion.ai
```

### Option 2: Netlify

**Step 1:** Create `netlify.toml`:

```toml
[build]
  command = "next build"
  publish = ".next"

[[redirects]]
  from = "/api/*"
  to = "http://localhost:8080/:splat"
  status = 200
```

**Step 2:** Deploy:

```bash
netlify deploy --prod
```

### Option 3: GitHub Pages

**Step 1:** Update `next.config.ts`:

```typescript
const nextConfig = {
  basePath: '/cohezion',
  assetPrefix: '/cohezion/',
  output: 'export',  // Static export
};
```

**Step 2:** Build and push:

```bash
npm run build
cp -r out/ docs/  # GitHub Pages directory
git add docs/
git commit -m "Deploy dashboard to GitHub Pages"
git push
```

**URL:** `https://manderson240.github.io/cohezion/`

---

## Training Data Export

### Export DPO/RLHF Data

```bash
# Export all training formats
uv run python -m cohezion.llm_training_bridge export-all \
  --output-dir data/training \
  --prefix anthropic_submission
```

**Output Files:**
- `data/training/anthropop_preferences.jsonl` - DPO preference pairs
- `data/training/anthropoc_rewards.jsonl` - RLHF scalar rewards
- `data/training/anthropik_judgments.jsonl` - Judgment fine-tuning

### Verify Export

```bash
# Check file sizes
wc -l data/training/*.jsonl

# Preview first record
head -1 data/training/anthropoc_preferences.jsonl | jq
```

### Upload to Hugging Face

```bash
# Install Hugging Face CLI
pip install huggingface_hub

# Login
huggingface-cli login

# Upload dataset
huggingface-cli upload \
  manderson240/cohezion-training-data \
  data/training/ \
  ./
```

---

## Documentation Deployment

### GitHub Pages for Docs

**Step 1:** Create `docs/_config.yml`:

```yaml
title: Cohezion Physics Documentation
theme: jekyll-theme-slate
markdown: GFM
```

**Step 2:** Enable GitHub Pages:

```bash
# Push docs to gh-pages branch
git subtree push --prefix docs origin gh-pages
```

**URL:** `https://manderson240.github.io/cohezion/`

### ReadTheDocs (Optional)

**Step 1:** Create `docs/conf.py`:

```python
project = 'Cohezion'
copyright = '2026, Mike Anderson'
author = 'Mike Anderson'
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.napoleon']
```

**Step 2:** Push to ReadTheDocs:

```bash
# Connect GitHub repo to ReadTheDocs
# https://readthedocs.org/dashboard/import/
```

---

## Portfolio Landing Page

### Create `PORTFOLIO.md` (Already Exists)

This file serves as the portfolio landing page with:
- Research narrative (`THE_UNIFIED_PHYSICS_NARRATIVE.md`)
- Live dashboard demo
- Training data samples
- Competition submissions

### GitHub README Update

Update main `README.md` with:

```markdown
## Live Demo

- **Dashboard**: https://cohezion.vercel.app
- **Documentation**: https://manderson240.github.io/cohezion/docs/
- **Training Data**: https://huggingface.co/datasets/manderson240/cohezion-training-data

## Research Paper

[The Unified Physics Narrative](THE_UNIFIED_PHYSICS_NARRATIVE.md) - 689 lines tracing 400-year lineage from Newton to Smith, with 4 empirical validations.

## Code Statistics

- **391 Python modules** across 68 packages
- **132,998 lines** of production code
- **2,854 passing tests**
- **162 skill documents** (~10K lines)

## Competition Submissions

- **Kaggle Measuring AGI**: `kaggle-agi-benchmark/`
- **Luma AMD Speedrun**: `research/challenges/luma_amd_speedrun/`
- **BlueQubit**: `research/challenges/bluequbit_challenge/`
```

---

## Anthropic Application Package

### Create Application Directory

```bash
mkdir -p anthropic_application
cd anthropic_application
```

### Files to Include:

1. **Research Paper**: `THE_UNIFIED_PHYSICS_NARRATIVE.md` (symlink)
2. **Portfolio README**: `PORTFOLIO.md` (symlink)
3. **Cover Letter**: `ANTHROPIC_COVER_LETTER.md` (already exists)
4. **Technical Summary**: `docs/ANTHROPIC_TECHNICAL_SUMMARY.md` (already exists)
5. **Dashboard URL**: Deployed link
6. **Training Data URL**: Hugging Face link
7. **GitHub Repo**: `https://github.com/manderson240/cohezion`

### Submission Script

Create `submit_anthropic.sh`:

```bash
#!/bin/bash
# Anthropic application submission

# 1. Deploy dashboard
cd src/web/anima_dashboard && vercel deploy --prod

# 2. Export training data
cd /home/mike-anderson/dev/cohezion
uv run python -m cohezion.llm_training_bridge export-all

# 3. Upload to Hugging Face
huggingface-cli upload manderson240/cohezion-training-data data/training/ ./

# 4. Print application URLs
echo "Dashboard: https://cohezion.vercel.app"
echo "Training Data: https://huggingface.co/datasets/manderson240/cohezion-training-data"
echo "GitHub: https://github.com/manderson240/cohezion"
echo "Research Paper: THE_UNIFIED_PHYSICS_NARRATIVE.md"
```

---

## Verification Checklist

### Dashboard

- [ ] Deployed to Vercel/Netlify/GitHub Pages
- [ ] API backend running (local or deployed)
- [ ] FlumeNavigator loads 3D visualization
- [ ] UniverseProvider connects to backend
- [ ] No console errors

### Training Data

- [ ] Exported `preferences.jsonl` (DPO pairs)
- [ ] Exported `rewards.jsonl` (RLHF rewards)
- [ ] Exported `judgments.jsonl` (fine-tuning)
- [ ] Uploaded to Hugging Face
- [ ] Dataset card complete

### Documentation

- [ ] Lagrangian formalization (`docs/LANGRANGIAN_FORMALIZATION.md`)
- [ ] Fiber bundle structure (`docs/FIBER_BUNDLE_STRUCTURE.md`)
- [ ] Unified physics narrative (`THE_UNIFIED_PHYSICS_NARRATIVE.md`)
- [ ] GitHub Pages deployed
- [ ] All links working

### Application

- [ ] Cover letter personalized
- [ ] Research paper linked
- [ ] Dashboard URL included
- [ ] Training data URL included
- [ ] GitHub repo linked
- [ ] Competition submissions mentioned

---

## Troubleshooting

### Dashboard Build Fails

```bash
# Clear cache
rm -rf .next node_modules
npm install
npm run build
```

### API Connection Refused

```bash
# Check if server is running
curl http://localhost:8080/api/health

# Restart server
uv run python -m cohezion.api.server
```

### Training Export Empty

```bash
# Check journey data exists
ls -la data/universe/*.json

# Re-run export with verbose logging
uv run python -m cohezion.llm_training_bridge export-all --verbose
```

---

## Post-Deployment

### Monitor Dashboard

```bash
# Vercel analytics
vercel analytics

# Check logs
vercel logs
```

### Update Documentation

```bash
# Rebuild docs
cd docs && make html

# Push to gh-pages
git subtree push --prefix docs origin gh-pages
```

### Iterate on Application

```bash
# Update cover letter
vim ANTHROPIC_COVER_LETTER.md

# Commit and push
git add .
git commit -m "Update Anthropic application"
git push
```

---

## Summary

**3 Commands to Deploy:**

1. `vercel deploy --prod` (dashboard)
2. `uv run python -m cohezion.llm_training_bridge export-all` (training data)
3. `huggingface-cli upload` (dataset upload)

**Application Package:**

- Research paper (689 lines)
- Live dashboard (deployed URL)
- Training data (Hugging Face)
- GitHub repo (132K lines)
- Competition submissions (3 challenges)

**You're ready to submit.**
