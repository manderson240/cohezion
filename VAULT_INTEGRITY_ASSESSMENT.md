# Vault Integrity Assessment & Validation Plan

**Date**: 2026-02-09
**Task**: #16 - Validate vault state consistency and data integrity
**Status**: Pre-Task #6 Baseline Assessment
**Blocking**: Task #7 (Final verification and handoff report)

## Current State (Baseline)

### Vault Statistics
- **Total Documents**: 10 (1 decision, 1 template set per category, 1 project file)
- **Expected After Task #6**: 161+ documents (Phase 5B commit)
- **Git Status**: Vault is clean, ready for commits
- **Vault Directory**: `/home/mike-anderson/dev/cohezion/cloud-vault-mcp/vault`

### Current Documents
```
README.md
├── decisions/
│   ├── 2026-02-09-phase-5b-multi-agent-coordination-complete.md (completed)
│   └── _template.md (template)
├── experiments/
│   └── _template.md
├── patterns/
│   └── _template.md
├── projects/
│   └── _template.md (+ 1 index file)
├── papers/
│   └── _template.md
├── daily/
│   └── _template.md
```

## Vault Integrity Checks Planned

### 1. **Markdown Format Validation**
- [ ] All 161+ files properly formatted (no corrupted data)
- [ ] No unclosed code blocks, brackets, or links
- [ ] Valid YAML frontmatter in ADRs/experiments/patterns
- [ ] Proper heading hierarchy (H1 at top)
- **Tool**: `vault_integrity_checker.py` (Phase 2)

### 2. **Document Metadata Consistency**
- [ ] Decisions: `date`, `status` fields present
- [ ] Experiments: `date`, `status` fields present
- [ ] Patterns: `category` field present
- [ ] Projects: `status` field present
- [ ] Consistent date format (ISO 8601)
- **Tool**: YAML frontmatter validator

### 3. **Orphaned/Unreferenced Documents**
- [ ] No orphaned documents (files not linked from any other doc)
- [ ] All wikilinks `[[note-name]]` resolve to existing files
- [ ] Internal references point to valid paths
- [ ] Category index files exist and are comprehensive
- **Tool**: Reference graph analyzer

### 4. **Duplicate Detection & Conflict Analysis**
- [ ] No duplicate content signatures
- [ ] No conflicting decisions on same topic (different sessions)
- [ ] No competing experiment results without reconciliation
- [ ] Decision supersession properly documented
- **Tool**: Content deduplication engine

### 5. **Session 37 → Session 40 Transition Documentation**
- [ ] Session 37 completion documented (intake specialist)
- [ ] Sessions 38-39 retrospectives present
- [ ] Session 40 (Phase 5B) completion documented
- [ ] Handoff documents complete and linked
- [ ] Phase completion milestones clearly marked
- **Expected Files**:
  - `decisions/2026-02-09-phase-5b-multi-agent-coordination-complete.md` ✓
  - `projects/SESSION-40-PHASE-5B-COMPLETE.md` (pending)
  - `projects/SESSION-39-RETROSPECTIVE.md` (pending)

### 6. **Git History Integrity**
- [ ] `.git` directory exists and is valid
- [ ] `.git/objects` contains commit objects (no corruption)
- [ ] `.git/refs/heads` has proper branch pointers
- [ ] Git config file is valid
- [ ] Can perform `git log --all` without errors
- [ ] No dangling commits or orphaned objects
- **Recovery Plan**: Can restore from backups if needed

### 7. **Stale TODOs & Incomplete Sections**
- [ ] No [TODO] markers older than 7 days without context
- [ ] No [WIP], [draft], or [incomplete] tags in published docs
- [ ] FIXME/XXX comments have clear owners or resolution timeline
- [ ] No abandoned experimentation notes

### 8. **Backup & Recovery Readiness**
- [ ] `.git` directory present for version control
- [ ] Critical files backed up externally
- [ ] Recovery procedure documented in vault
- [ ] Can regenerate vault from git history
- **Action Items**:
  - Document backup locations
  - Create recovery runbook
  - Test recovery procedure

### 9. **Reference Consistency**
- [ ] All cross-references use consistent naming (kebab-case)
- [ ] No circular dependencies between documents
- [ ] Category hierarchies are consistent
- [ ] Tags are properly formatted and indexed
- **Pattern**: `[[phase-5b-multi-agent-coordination]]` (not spaces, camelCase)

## Integrity Issues Expected (Based on Historical Data)

### Low Priority
- Templates may have placeholder {{date}} values (handled by validator)
- Some older session handoff documents may be archived/redundant
- Category directories may have variable file counts

### Medium Priority
- Session 37-38 retrospectives may lack detailed metrics
- Some experiments may lack reconciliation notes
- Older projects may not link to Phase 5B work

### High Priority (Unlikely but Checking)
- Corruption in git objects (would prevent commits)
- Missing critical decision documents
- Broken reference chains between sessions

## Validation Process (Post-Task #6)

### Phase 1: Load & Scan (2 min)
```bash
python3 scripts/vault_integrity_checker.py
```
- Loads all 161+ documents
- Scans for format issues
- Indexes metadata
- Analyzes references

### Phase 2: Generate Report (30 sec)
- JSON report: `/cloud-vault-mcp/vault_integrity_report.json`
- Text summary: stdout
- Issues categorized as CRITICAL/WARNING

### Phase 3: Issue Remediation (variable)
- Fix CRITICAL issues before PR
- Document WARNINGs in report
- Generate repair procedures for common issues

### Phase 4: Backup Verification (5 min)
- Verify `.git` health with `git fsck`
- Test recovery procedure
- Document backup location

## Success Criteria

### Must Pass
- ✓ No CRITICAL integrity issues
- ✓ All markdown files format-valid
- ✓ All metadata fields present and consistent
- ✓ All references resolve correctly
- ✓ Git history is intact

### Should Pass
- ✓ No orphaned documents
- ✓ No stale TODOs (>7 days old)
- ✓ Session transition properly documented
- ✓ Backup/recovery procedures documented

### Nice to Have
- ✓ <5% format warnings
- ✓ <10% inconsistent metadata
- ✓ Vault structure well-organized and discoverable

## Risk Mitigations

### If Task #6 Doesn't Commit 144 Files
- **Plan A**: Validate what exists (10 docs + Phase 5B doc)
- **Plan B**: Partial commit and incremental validation
- **Plan C**: Identify why files aren't committing (size, format, encoding)

### If Git History Is Corrupted
- **Recovery**: Use filesystem backups if available
- **Mitigation**: Implement pre-commit integrity hook
- **Fallback**: Rebuild vault from source documents

### If References Are Broken
- **Repair**: Auto-generate reference map and fix links
- **Prevention**: Validate references before commit

## Timeline

| Phase | Est. Time | Trigger |
|-------|-----------|---------|
| Baseline (current) | 15 min | Started |
| Await Task #6 | Variable | Task #6 completes |
| Validation scan | 5 min | Post-commit |
| Issue remediation | 15-30 min | If needed |
| Recovery testing | 10 min | Post-remediation |
| Final report | 10 min | Documentation |

## Tools & Scripts

- **Main Validator**: `/scripts/vault_integrity_checker.py` (550+ lines)
- **Git Validator**: Built-in `git fsck --full`
- **Format Checker**: Regex-based markdown validation
- **Reference Analyzer**: Graph-based link resolution
- **Report Generator**: JSON + text output

## Deliverables (Task #16)

1. **Vault Integrity Report** (JSON)
   - Statistics, issues, recommendations
   - Location: `cloud-vault-mcp/vault_integrity_report.json`

2. **Remediation Plan** (Markdown)
   - Issues found and fixes applied
   - Recovery procedures documented
   - Prevention recommendations

3. **Recovery Procedures** (Markdown)
   - Git restore from backups
   - Manual fix procedures for common issues
   - Pre-commit validation hooks

4. **Updated MEMORY.md** (if needed)
   - Vault structure lessons learned
   - Best practices for future sessions

## Next Steps

**Immediate** (when Task #6 ready):
1. Run integrity checker on committed files
2. Document any issues found
3. Generate remediation plan
4. Test recovery procedures

**Follow-up** (before PR to main):
1. Apply all remediation fixes
2. Verify no critical issues remain
3. Update MEMORY.md with lessons
4. Create pre-commit validation hook

**Long-term**:
1. Periodic integrity checks (monthly)
2. Automated validation in CI/CD
3. Archive old session documents
4. SurrealDB migration planning (Phase 6)
