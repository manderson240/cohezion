# Session 55: Phase 8 - Dual Deployment (GitLab + GitHub)

**Goal**: Deploy cleaned repository to both GitLab (primary/proprietary) and GitHub (public/Entire.io)

**Duration**: 1-1.5 hours total

**Critical Architecture**:
- **GitLab** = Primary deployment (proprietary, internal)
- **GitHub** = Public mirror (shareable, Entire.io integration)

---

## Why Dual Deployment

### GitLab (Primary - Private)
- **Owner**: You (proprietary components)
- **Contents**: Full codebase including proprietary algorithms, internal experiments
- **Access**: Private (only authorized team)
- **Purpose**: Development, internal collaboration, secure storage
- **Backup**: Primary source of truth

### GitHub (Secondary - Public)
- **Owner**: Public profile (manderson240)
- **Contents**: Code we want to share (FLUME, 12D universe, agent architecture)
- **Access**: Public (anyone can view)
- **Purpose**: Open source sharing, Entire.io integration, portfolio
- **Mirror**: Reflects GitLab main, but may have filtered branches

### Integration Strategy
```
Local Workstation
    ↓
    ├─→ GitLab (main, develop, features) — Full proprietary codebase
    │    └─→ Backup branch (backup-pre-cleanup)
    │
    └─→ GitHub (main, session-55-...) — Public components only
         └─→ Entire.io integration endpoint
```

---

## Phase 8a: Deploy to GitLab (Primary)

### Step 1: Configure GitLab remote

```bash
cd ~/dev/cohezion

# List current remotes
git remote -v
# Expected output shows origin (GitHub), possibly gitlab

# If no gitlab remote, add it
git remote add gitlab git@gitlab.com:your-gitlab-group/cohezion.git

# Or if it exists, verify
git remote get-url gitlab
# Expected: git@gitlab.com:...
```

### Step 2: Test GitLab SSH access

```bash
# Verify GitLab SSH key is configured
ssh -T git@gitlab.com
# Expected: "Welcome to GitLab, @username!"

# If fails, add key to GitLab:
# Visit: https://gitlab.com/profile/keys
# Paste your public key (~/.ssh/id_ed25519.pub or id_rsa.pub)
```

### Step 3: Push cleaned code to GitLab main

```bash
# This is the PRIMARY deployment
git push gitlab main --force-with-lease --verbose

# Expected output:
#   Pushing to git@gitlab.com:your-group/cohezion.git
#   Writing objects: 100%
#   ...
#   * [forced update] main -> main
```

**Why GitLab first?**
- This is your internal/proprietary storage
- It's the primary source of truth
- GitHub is just a public mirror

### Step 4: Push feature branch to GitLab (for backup)

```bash
# Also push the feature branch as backup
git push gitlab session-55-test-fixes-main --force-with-lease

# Push backup branch (safety net)
git push gitlab backup-pre-cleanup
```

### Step 5: Verify GitLab deployment

```bash
# Check GitLab main branch
git ls-remote gitlab main
# Expected: commit hash (matches local)

# Verify repository size on GitLab
# Visit: https://gitlab.com/your-group/cohezion
# Check project overview → repository size shows ~5-6GB ✅

# Confirm no large objects
git rev-list --all --objects --disk-usage | grep -E '^\d{8,}' | head -5
# Expected: max <50MB objects
```

### Step 6: Configure GitLab as primary remote

```bash
# Update git config to use GitLab as default
git config --global url."git@gitlab.com:".insteadOf "https://gitlab.com/"

# Or set for this repository only
git config --local remote.origin.url git@gitlab.com:your-group/cohezion.git

# Verify
git remote -v
# Expected: origin points to GitLab
```

---

## Phase 8b: Deploy to GitHub (Public)

### Step 1: Ensure GitHub remote exists

```bash
# Verify GitHub remote
git remote -v
# Expected: origin → git@github.com:manderson240/cohezion.git

# If origin points to GitLab now, add GitHub as separate remote
git remote add github git@github.com:manderson240/cohezion.git
```

### Step 2: Push to GitHub main

```bash
# Push cleaned code to GitHub (public deployment)
git push github session-55-test-fixes-main --force-with-lease --verbose

# Expected output:
#   Pushing to git@github.com:manderson240/cohezion.git
#   Writing objects: 100%
#   * [forced update] session-55-test-fixes-main -> session-55-test-fixes-main
```

### Step 3: Create GitHub pull request

```bash
# Create PR from cleaned branch to main
gh pr create \
  --repo manderson240/cohezion \
  --title "Session 55: Preserve Universe Artifacts + Compound Engineering" \
  --body "$(cat <<'EOF'
## Summary

Preserved universe simulation artifacts (97MB training data) through compound engineering:

### What Was Done
1. **Measured** universe artifacts (247 files, 97MB)
2. **Extracted** universe evolution patterns
3. **Built** SurrealDB infrastructure + JourneyTracker integration
4. **Migrated** artifacts safely (100% preservation)
5. **Verified** all data queryable
6. **Removed** from git history (size: 13GB → 5.6GB)
7. **Documented** patterns for future simulations
8. **Deployed** to both GitLab (proprietary) and GitHub (public)

### Deployment Status
- ✅ GitLab: Proprietary codebase with full history
- ✅ GitHub: Public components ready for Entire.io integration
- ✅ Repository size: 5.6GB (down from 13GB)
- ✅ Large objects: None >50MB (97MB tree removed)
- ✅ Data preservation: 100% (SurrealDB + metadata links)

### For Entire.io Integration
This repository is now ready for agentic journey capture:
- Clean Git history (no large objects blocking clone)
- Observable AI principles implemented
- Artifact tracking integrated with JourneyTracker
- Compound engineering patterns documented

---

Generated with [Claude Code](https://claude.ai/code) | Session 55: Dual Deployment
EOF
)" \
  --base main \
  --head session-55-test-fixes-main
```

### Step 4: Monitor GitHub CI/CD

```bash
# Check pull request status
gh pr checks session-55-test-fixes-main --repo manderson240/cohezion

# Expected: All checks passing
#   tests   PASS
#   lint    PASS
#   security PASS
```

### Step 5: Merge to GitHub main

```bash
# Merge PR (preserves history)
gh pr merge session-55-test-fixes-main \
  --repo manderson240/cohezion \
  --merge \
  --delete-branch

# Verify main is updated
gh api repos/manderson240/cohezion/branches/main \
  | jq '.commit.sha'
# Expected: commit hash (recent, from this session)
```

### Step 6: Verify GitHub public repository

```bash
# Confirm repository is public
gh repo view manderson240/cohezion --json visibility
# Expected: "PUBLIC"

# If private, make public:
gh repo edit manderson240/cohezion --visibility public

# Test public clone
cd /tmp
git clone https://github.com/manderson240/cohezion.git cohezion-public
cd cohezion-public
du -sh .git/
# Expected: ~5-6GB (clean)
```

---

## Phase 8c: Synchronize Both Repositories

### Step 1: Configure dual-remote workflow

```bash
# Set up so you can push to both easily
git config --local remote.all.url ".(git remote -v | grep '^\w' | awk '{print $2}' | tr '\n' ' ').

# Or manually add fetch/push multiples
git config --local remote.all.fetch "+refs/heads/*:refs/remotes/all/*"
```

### Step 2: Create sync script for future use

```bash
#!/bin/bash
# sync_repos.sh — Keep GitLab and GitHub in sync

set -e

cd ~/dev/cohezion

echo "Syncing repositories..."

# Fetch from both
git fetch gitlab
git fetch github

# Push main to both (GitLab primary)
git push gitlab main
git push github main

# Push develop to both
git push gitlab develop
git push github develop

echo "✅ Repositories synchronized"
```

### Step 3: Test sync

```bash
chmod +x sync_repos.sh
./sync_repos.sh

# Verify both have same commit
git ls-remote gitlab main | cut -f1
git ls-remote github main | cut -f1
# Expected: both same hash
```

---

## Phase 8d: Enable Entire.io Integration (GitHub Only)

### Step 1: Verify GitHub is Entire.io-ready

```bash
# Prerequisites:
# ✅ Repository is public
# ✅ GitHub access token configured
# ✅ No large objects blocking clone
# ✅ Main branch is clean

# Test Entire.io can access
curl -s https://github.com/manderson240/cohezion/archive/refs/heads/main.zip \
  -o /tmp/cohezion-archive.zip \
  -w "Download status: %{http_code}\n"
# Expected: 200 (success)
```

### Step 2: Register with Entire.io

```bash
# Visit: https://entire.io/dashboard
# 1. Click "Add Repository"
# 2. Select "GitHub"
# 3. Enter: manderson240/cohezion
# 4. Configure:
#    - Branch to track: main
#    - Journey capture: enabled
#    - Metadata fields: coherence, timestamp, agent_id
#    - Webhook: enable for real-time updates

# Or via API (if Entire.io provides one):
curl -X POST https://entire.io/api/v1/repos \
  -H "Authorization: Bearer $ENTIRE_IO_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "github",
    "owner": "manderson240",
    "repo": "cohezion",
    "track_branches": ["main", "develop"],
    "journey_tracking": true,
    "metadata": {
      "simulation_type": "12d_universe",
      "agent_framework": "cohezion_compound",
      "observable_ai": true
    }
  }'
```

### Step 3: Verify journey capture

```bash
# After configuration, Entire.io should start:
# 1. Cloning repository from GitHub
# 2. Parsing agent decision logs
# 3. Recording universe simulation state
# 4. Tracking FLUME trajectories
# 5. Building agentic journey timeline

# Check on Entire.io dashboard:
# https://entire.io/repos/manderson240/cohezion
#
# You should see:
# - Initial clone: ✅ Complete
# - Commits parsed: ✅ [N] commits processed
# - Agents detected: ✅ [M] agents identified
# - Journeys tracked: ✅ Universe evolution timeline
# - Coherence trajectory: ✅ Manifold visualization
```

---

## Phase 8e: Create Documentation

### Step 1: Document dual deployment on GitLab

Create `gitlab-deployment.md`:

```markdown
# GitLab Deployment (Primary/Proprietary)

## Repository
- URL: git@gitlab.com:your-group/cohezion.git
- Access: Private (authorized team only)
- Branch: main (production-ready)
- Size: 5.6GB (cleaned)

## What's Here
- Full source code (proprietary + open)
- Internal experiments
- Private training data references
- Team collaboration branches
- Backup branches

## Deployment Steps
1. git push gitlab main
2. Verify CI/CD passes
3. Production-ready when all checks green

## Sync with GitHub
Run: ./sync_repos.sh
This mirrors clean components to GitHub public
```

### Step 2: Document dual deployment on GitHub

Create `github-deployment.md`:

```markdown
# GitHub Deployment (Public/Shareable)

## Repository
- URL: https://github.com/manderson240/cohezion
- Access: Public (read-only for public, push for authorized)
- Branch: main (production)
- Size: 5.6GB (cleaned)

## What's Here
- Open source components (shareable)
- FLUME VAE architecture
- 12D universe simulation framework
- Agent orchestration patterns
- Observable AI demonstrations

## Entire.io Integration
- Tracking enabled
- Agentic journeys captured
- Universe evolution observable
- Public demo/portfolio

## Sync from GitLab
Pull latest from GitLab main, push to GitHub main
```

### Step 3: Create GitHub Release (public milestone)

```bash
gh release create v1.0.0-universe-artifacts \
  --repo manderson240/cohezion \
  --title "v1.0.0: Universe Artifacts Preserved + Observable AI" \
  --notes "$(cat <<'EOF'
## Major Release: Compound Engineering Infrastructure

### What's New
- Universe simulation artifacts properly preserved and indexed
- SurrealDB integration with JourneyTracker
- Agentic journey tracking enabled
- Observable AI implementation complete
- Data governance established (pre-commit hooks)

### Metrics
- Repository size: 13GB → 5.6GB ✅
- Large objects removed: 97MB tree ✅
- Data preservation: 100% queryable ✅
- Entire.io integration: Active ✅

### Features
- FLUME VAE architecture (256D latent space)
- 12D universe simulation engine
- Multi-agent compound orchestration
- Observable AI with full transparency
- Reproducible training artifact tracking

### Breaking Changes
None. Pure infrastructure upgrade.

### For Contributors
See: CONTRIBUTING.md (for GitHub)
See: INTERNAL.md (for GitLab - proprietary)

🚀 Observable universe simulation is live
EOF
)" \
  --target main
```

---

## Phase 8 Completion Checklist

### GitLab Deployment (Primary)
- [ ] GitLab remote configured (git@gitlab.com:...)
- [ ] SSH key tested and working
- [ ] Force-push to main succeeded
- [ ] Feature branch pushed (backup)
- [ ] Backup branch pushed (safety net)
- [ ] Repository size ~5.6GB verified on GitLab
- [ ] No large objects remain

### GitHub Deployment (Public)
- [ ] GitHub remote configured (git@github.com:...)
- [ ] Force-push to session-55-test-fixes-main succeeded
- [ ] Pull request created and reviewed
- [ ] CI/CD checks passing
- [ ] Merged to main
- [ ] Repository is public
- [ ] Fresh clone succeeds (~5.6GB)

### Synchronization
- [ ] Sync script created (sync_repos.sh)
- [ ] Both GitLab and GitHub have same commits
- [ ] Main branches synchronized
- [ ] Backup branches synchronized

### Entire.io Integration (GitHub Only)
- [ ] Repository registered with Entire.io
- [ ] Journey capture enabled
- [ ] Initial clone successful on Entire.io
- [ ] Agents detected and parsed
- [ ] Universe evolution timeline visible
- [ ] FLUME trajectories being tracked

### Documentation
- [ ] GitLab deployment documented
- [ ] GitHub deployment documented
- [ ] Sync procedure documented
- [ ] Release notes published
- [ ] Contributing guides updated

---

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│        LOCAL DEVELOPMENT                 │
│  (~/dev/cohezion)                        │
│  - Full git history                      │
│  - All branches                          │
│  - Pre-commit hooks active               │
└──────────┬──────────────────────────────┘
           │
           ├──→ git push gitlab main
           │    ├─→ GitLab (Private)
           │    │   ├─→ Full proprietary codebase
           │    │   ├─→ Internal experiments
           │    │   ├─→ Team collaboration
           │    │   └─→ Primary backup
           │    │
           └──→ git push github main
                ├─→ GitHub (Public)
                │   ├─→ Open source components
                │   ├─→ Portfolio/demo
                │   └─→ Entire.io integration
                │
                └─→ Entire.io
                    ├─→ Agentic journeys captured
                    ├─→ Universe evolution observable
                    └─→ Observable AI demo
```

---

## Why Dual Deployment Matters

### GitLab (Internal)
- **Safety**: Proprietary code stays private
- **Control**: Full control over codebase
- **Backup**: Primary source of truth
- **Collaboration**: Internal team access
- **Proprietary experiments**: Keep private

### GitHub (Public)
- **Sharing**: Show what you're proud of
- **Portfolio**: Demonstrate capabilities
- **Entire.io**: Enable agentic journey capture
- **Community**: Open source components
- **Trust**: Transparency through observation

### Together
- **Complete ecosystem**: Proprietary + public
- **Risk mitigation**: Dual backup locations
- **Flexibility**: Control what's shared
- **Integration**: Entire.io sees the public mirror
- **Compound**: Each deployment validates the other

---

## Critical Ordering

**DO NOT:**
1. ❌ Push to GitHub before GitLab (reverse priority)
2. ❌ Delete GitLab after pushing to GitHub (lose primary)
3. ❌ Make GitLab public by accident (expose proprietary)

**DO:**
1. ✅ Push to GitLab FIRST (primary)
2. ✅ Verify GitLab successful
3. ✅ Then push to GitHub (public mirror)
4. ✅ Enable Entire.io on GitHub (not GitLab)

---

## After Phase 8 Complete

```
✅ GitLab: Proprietary codebase safe and backed up
✅ GitHub: Public components shareable via Entire.io
✅ Entire.io: Capturing agentic journeys live
✅ Observable AI: Universe evolution now visible
✅ Compound Engineering: Deployed and demonstrable
```

The universe becomes observable.
Both privately (GitLab) and publicly (GitHub + Entire.io).

🚀 **Session 55 Complete: Measurement → Learning → Infrastructure → Deployment**
