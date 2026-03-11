---
title: Session 55 - HTTP 500 failure may be protocol-specific; SSH push alternative
  available
date: '2026-02-11'
status: proposed
tags: [decision, inferred]
decision_reasoning:
  reasoning_chain:
  - sequence: 1
    content: 'Context: Session 55 - HTTP 500 failure may be protocol-specific; SSH
      push alternative ava...'
    type: research
    confidence: 0.65
    assumption: Problem was clearly identified
  - sequence: 2
    content: Explored multiple implementation approaches and trade-offs
    type: pattern
    confidence: 0.6
    assumption: Multiple options were considered
  - sequence: 3
    content: Evaluated options against project constraints and criteria
    type: research
    confidence: 0.58
    assumption: Options were systematically evaluated
  reasoning_type: research
  confidence_score: 0.6
aspect: thinker
neural:
  activation: 0.493
  stage: growing
  cluster: decisions
---

## Context

During Session 55's attempt to push the cleaned-up Cohezion repository to its remote, `git push` over HTTPS consistently returned HTTP 500 (Internal Server Error) responses. The push payload was approximately 6.5 GB after cleanup (down from 12 GB), which exceeded the hosting provider's default HTTPS upload limits for git operations.

Investigation revealed several key facts:
- The HTTP 500 was a server-side rejection, not a client-side error -- the git protocol handshake succeeded but the data transfer was terminated by the server
- GitLab's default HTTPS push limit is typically lower than SSH's, as HTTP uses chunked transfer encoding with timeouts per chunk
- SSH push uses a persistent connection with no per-chunk timeout, making it more resilient for large payloads
- The repository's pack structure (even after consolidation) produced a large transfer payload that exceeded HTTP timeout windows

## Decision

Identify the HTTP 500 failure as protocol-specific rather than a data integrity issue, and switch to SSH push as the alternative transport:

```bash
# Switch remote URL from HTTPS to SSH
git remote set-url origin git@gitlab.com:org/cohezion.git

# Retry push over SSH (persistent connection, no chunked timeout)
git push --all origin
git push --tags origin
```

If SSH push also fails, the repository size is genuinely too large and further cleanup (history rewriting via BFG) is needed before any push succeeds.

## Consequences

**Positive:**
- Correctly diagnosed the failure as a transport layer issue, not a data corruption or git protocol problem
- SSH push avoids the chunked timeout limitations of HTTPS
- Established a diagnostic pattern: when push fails, check protocol before assuming data problems
- Informed the subsequent [[2026-02-13-gitlab-to-github-consolidation-with-artifact-governance|GitHub migration decision]] -- GitHub's HTTPS limits are similarly restrictive for multi-GB pushes

**Negative:**
- SSH requires key-based authentication setup (not always available in CI/CD environments)
- Does not solve the fundamental problem (repository is too large) -- only works around the transport limitation
- If both HTTPS and SSH fail, the only remaining option is further history reduction

## Alternatives Considered

### Alt 1: Increase HTTPS Timeout on Server Side
- **Rejected**: Requires GitLab administrator access. For self-hosted GitLab, the `client_max_body_size` nginx setting could be increased, but for gitlab.com SaaS this is not configurable.

### Alt 2: Push in Smaller Batches (Shallow History)
- **Rejected**: `git push` does not natively support incremental history transfer for the initial push. Workarounds (pushing tags/branches individually) still transfer the full pack for each ref.

### Alt 3: Use `git bundle` as Transfer Mechanism
- **Rejected**: Creates an out-of-band file transfer that must be manually applied at the remote. Adds significant operational complexity compared to switching to SSH.

### Alt 4: Further Reduce Repository Size Before Pushing
- **Considered as fallback**: If SSH also fails, then the repository genuinely needs history rewriting (BFG or `git filter-repo`) to strip large objects. This became the approach used in the GitHub migration.

## See Also

- [[multi-platform-repository-deployment-with-external-integration]]
- [[2026-02-11-session-55-phase-c-execution-ready]]
- [[troubleshooting-mcp-infrastructure]]
- [[api-design]] — HTTP 500 failures during push reveal protocol-level API design concerns when deploying across platforms
- [[data-discipline-prevent-generated-data-in-git]] — the repository size issues driving this push were caused by training data committed to git history
- [[2026-02-09-session-46-git-unification-complete]] — prior git unification session that established the repository baseline this push attempted to deploy
