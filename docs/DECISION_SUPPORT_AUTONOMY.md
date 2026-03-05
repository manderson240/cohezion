# Decision Support Autonomy Architecture

## Philosophy

**Human**: Decides WHAT to do (ideas, direction, approval)
**COHEZION**: Handles HOW it's done (implementation, repo management)

---

## Separation of Concerns

### Human Responsibilities (Decision Making)
- ✅ Deciding what features to build
- ✅ Approving architectural changes
- ✅ Setting priorities
- ✅ Final approval on breaking changes
- ✅ Reviewing outcomes
- ✅ Defining "done"

### COHEZION Responsibilities (Repo Management)
- ✅ Writing the code
- ✅ Creating branches
- ✅ Managing commits
- ✅ Handling versioning (semver)
- ✅ Updating documentation
- ✅ Running tests
- ✅ Creating releases
- ✅ Keeping CHANGELOG current
- ✅ Managing dependencies

---

## Workflow: Decision → Execution

### Pattern 1: Direct Implementation (Low Risk)

**You Decide**: "Fix the typo in README"
**COHEZION Executes**:
```
1. Edits README.md
2. Runs tests (if any)
3. Commits: "docs: fix typo in README"
4. Pushes to main
5. Updates CHANGELOG
6. Notifies: "✅ Fixed typo, committed to main"
```
**Your Involvement**: 0 (after decision)

---

### Pattern 2: Feature Implementation (Medium Risk)

**You Decide**: "Add dark mode toggle"
**COHEZION Executes**:
```
1. Creates branch: feature/auto-dark-mode
2. Implements dark mode
3. Writes tests
4. Updates docs
5. Commits: "feat: add dark mode toggle"
6. Creates PR
7. Notifies: "📝 Dark mode ready for review"
```
**Your Involvement**: 1 approval to merge

---

### Pattern 3: Breaking Change (High Risk)

**You Decide**: "Refactor the API to be RESTful"
**COHEZION Executes**:
```
1. Creates branch: refactor/restful-api
2. Plans migration
3. Implements changes
4. Updates all dependent code
5. Updates docs with migration guide
6. Commits: "feat!: refactor to RESTful API"
7. Creates PR with detailed notes
8. Notifies: "⚠️ Breaking change ready for review"
```
**Your Involvement**: Review + Approve

---

### Pattern 4: Emergency Fix (Security)

**COHEZION Detects**: Security vulnerability in dependency
**COHEZION Executes**:
```
1. Updates dependency
2. Runs security tests
3. Commits: "security: patch vulnerability in X"
4. Pushes to main (auto-deploy if safe)
5. Creates release
6. Notifies: "🔒 Security patch deployed"
```
**Your Involvement**: 0 (pre-approved for security)

---

## Decision Tiers

### Tier 0: Pre-Approved (No Human Needed)
- Documentation fixes
- Comment improvements
- Dependency patches (security)
- Test additions
- Refactoring (no behavior change)

### Tier 1: Notification Only (Human Informed)
- Bug fixes (under 50 lines)
- Small features (isolated)
- Config updates
- CI/CD improvements

### Tier 2: PR Required (Human Reviews)
- New features
- API changes
- Database migrations
- Configuration changes

### Tier 3: Approval Required (Human Decides)
- Breaking changes
- Architecture shifts
- Security changes
- Major refactors

---

## Implementation

### Configuration

```yaml
# .autonomy/config.yaml
autonomy_level: 2.5  # Decision support mode

# Decision Tiers
tiers:
  tier_0:  # Pre-approved
    - docs_fixes
    - typo_fixes
    - security_patches
    - test_additions
    commit_directly: true
    
  tier_1:  # Notification
    - small_fixes
    - isolated_features
    create_pr: true
    auto_merge: true
    notify_before: false
    notify_after: true
    
  tier_2:  # PR Required
    - features
    - api_changes
    - migrations
    create_pr: true
    auto_merge: false
    require_review: false
    
  tier_3:  # Approval Required
    - breaking_changes
    - architecture
    - security_changes
    create_pr: true
    require_review: true
    require_approval: true

# Notifications
notifications:
  before_tier_2: false   # Don't ask before, just do
  after_every: true      # Always report what was done
  summary_daily: true    # Daily digest of activity
  
# Human Override
override:
  enabled: true
  can_pause: true
  can_rollback: true
```

---

## Commands

### You → COHEZION

```bash
# Simple request
cohezion "Fix the typo in README"
→ ✅ Fixed and committed

# Feature request
cohezion "Add dark mode"
→ 📝 PR #456 created, ready for review

# Breaking change (flagged automatically)
cohezion "Rename all User classes to Account"
→ ⚠️ Breaking change detected
   PR #457 created with migration guide
   Awaiting your approval

# Check what's pending
cohezion status
→ 📊 2 PRs awaiting review
   - PR #456: Dark mode (ready)
   - PR #457: API refactor (needs decision)

# Approve
cohezion approve 457
→ ✅ Approved and merged

# Rollback if needed
cohezion rollback
→ 🔄 Reverted last change
```

### COHEZION → You

```
📬 COHEZION Update:

✅ Completed:
   - Fixed typo in README
   - Committed: docs: fix typo
   - No action needed

📝 Pending Review:
   - Dark mode feature (PR #456)
   - Breaking change (PR #457)
   [Review] [Approve] [Modify]

📊 Today's Summary:
   - 3 auto-commits
   - 2 PRs created
   - 0.5 hours saved
```

---

## Notification Strategy

### Immediate (Don't Wait)
- Breaking changes detected
- Security issues found
- Tests failing
- Implementation complete for PR

### Daily Digest (Batch)
- All completed work
- Repository health metrics
- Upcoming maintenance

### Weekly Summary (Strategic)
- Time saved metrics
- Pattern analysis
- Suggestions for next week

---

## Safety Mechanisms

### Auto-Detection

```python
def classify_change(files, description):
    """Auto-detect tier."""
    
    # Breaking change indicators
    if any(indicator in description for indicator in [
        "remove", "delete", "rename", "change to", "replace"
    ]):
        if any(f.endswith(".py") for f in files):
            return "tier_3"  # Needs approval
    
    # Security indicators
    if "security" in description.lower():
        return "tier_1"  # Notify but auto-merge if tests pass
    
    # Documentation only
    if all(f.endswith(".md") or f.endswith(".txt") for f in files):
        return "tier_0"  # Pre-approved
    
    # Small fixes
    if len(files) <= 3 and "fix" in description.lower():
        return "tier_1"
    
    # Default
    return "tier_2"
```

---

## Example Session

### You
```
I need to add user authentication to the API
```

### COHEZION
```
🤖 I'll implement user authentication.

📋 Plan:
   1. Add auth endpoints (/login, /logout)
   2. Add JWT token handling
   3. Add middleware for protected routes
   4. Write tests
   5. Update API documentation

⚠️ This will be a Tier 2 change (new feature).
   I'll create a PR for your review.

[Proceed] [Modify Plan] [Cancel]
```

### You
```
Proceed
```

### COHEZION (30 minutes later)
```
✅ Implementation complete!

📊 Summary:
   - Branch: feature/auto-auth
   - Files: +4 new, +2 modified
   - Tests: 15 new, all passing
   - Commits: 3
   
📝 PR #458 created
   - Description: Full auth implementation
   - Migration: N/A (additive)
   - Breaking: No
   
[Review PR] [Approve & Merge] [Request Changes]
```

### You
```
Approve & Merge
```

### COHEZION
```
✅ Merged to main
🏷️  Tagged v1.5.0
📖  Updated documentation
📬  Release notes generated

📊 Time saved: 2 hours
```

---

## Key Principle

**You say**: "What" (the goal)
**COHEZION does**: "How" (the implementation)

**You review**: Major decisions, architecture, direction
**COHEZION manages**: Everything else

---

## Ready?

This gives you:
- ✅ Autonomous implementation
- ✅ Automatic repo management
- ✅ Human oversight on decisions
- ✅ Notifications, not interruptions
- ✅ Time saved on mechanical work

**Shall I implement this Decision Support Architecture?**
