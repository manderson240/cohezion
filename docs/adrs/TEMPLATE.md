---
adr_number: NNN
title: <descriptive title>
date: YYYY-MM-DD
status: ACCEPTED | PROPOSED | DEPRECATED | SUPERSEDED-by-ADR-N
deciders: <who decided>
consulted: [list]
informed: [list]
authored_by: <author or campaign>
---

# ADR-NNN: <Title>

## Status

<status + date>

## Context

<what circumstance prompted this decision; what problem it addresses; what constraints exist; ~3 paragraphs>

## Decision

<what we chose to do; the actual decision in one paragraph + key parameters/numbers>

## Rationale

<why this option over the alternatives; ~3 paragraphs>

## Alternatives considered

### Option A: <name>
- Pros: ...
- Cons: ...
- Why rejected: ...

### Option B: <name>
- Pros / Cons / Why rejected

### Option C (chosen): <name>
- Pros / Cons / Why chosen

## Consequences

### Positive
- ...

### Negative
- ...

### Neutral
- ...

## Implementation

- Primary files: <list with paths>
- Test files: <list>
- Documentation: <CLAUDE.md sections + this ADR>

## Verification

How a reviewer can verify the decision is being followed:
- Static check: <command>
- Runtime check: <command>
- Test: <test name>

## Reversal cost

<low / medium / high — and explanation>

## Related ADRs

- Depends on: ...
- Informs: ...
- Tension with: ...

## References

- CLAUDE.md sections
- Vault decisions
- External literature (with real citations or [pending])
