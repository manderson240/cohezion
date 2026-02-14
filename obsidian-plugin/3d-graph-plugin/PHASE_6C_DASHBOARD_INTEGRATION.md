# Phase 6C for Dashboard Engineers (Phase 7A/7B)

**Quick Reference for Phase 7A/7B Teams**

## What Phase 6C Provides

### 1. Contradiction Detection Service

**Import**:
```typescript
import { SemanticContradictionDetector } from '../services/SemanticContradictionDetector';

const detector = new SemanticContradictionDetector('http://localhost:11434');
const contradictions = await detector.detectContradictions(decisions, lessons, 0.7);
```

**Input**:
- `decisions`: Array of {id, rationale, chosen_option, confidence_score, alternatives_rejected}
- `lessons`: Array of {id, key_insight, implications, incoming_links}
- `threshold`: 0.7 (default, adjustable)

**Output**:
```typescript
DecisionContradiction[] = [
  {
    decision_id: string,
    lesson_id: string,
    challenge_type: 'contradicts' | 'undermines' | 'requires_review',
    severity: 'critical' | 'high' | 'medium' | 'low',
    description: string
  }
]
```

### 2. Database Queries

**Available Methods in SurrealDBClient**:

```typescript
// Get all decisions for embedding
const decisions = await dbClient.queryAllDecisionsForEmbedding();

// Get all lessons for embedding
const lessons = await dbClient.queryAllLessonsForEmbedding();

// Store detected contradictions
const count = await dbClient.storeSemanticContradictions(contradictions);

// Query all contradictions for a decision
const result = await dbClient.detectContradictions(decisionId);

// Get contradiction counts
const counts = await dbClient.queryAllContradictionCounts();
```

### 3. Dashboard Data

**For Phase 7A (Health Dashboard)**:

```surreal
// Get contradictions by severity
SELECT severity, COUNT() as count
FROM decision_contradictions
WHERE detection_method = 'semantic'
GROUP BY severity

// Get contradictions by type
SELECT challenge_type, COUNT() as count
FROM decision_contradictions
WHERE detection_method = 'semantic'
GROUP BY challenge_type

// Get contradictions for specific decision
SELECT * FROM decision_contradictions
WHERE decision_id = '<decision_id>'
AND detection_method = 'semantic'
ORDER BY severity DESC
```

**Expected Results**:
```
Severity Distribution:
  critical: 3-8
  high: 8-15
  medium: 8-15
  low: 3-8

Type Distribution:
  contradicts: 12-20
  undermines: 8-12
  requires_review: 4-8
```

### 4. For Phase 7B (Recommendations)

**Contradiction Data Available**:
- `decision_id`: Which decision is challenged
- `lesson_id`: What lesson challenges it
- `severity`: How serious (critical/high/medium/low)
- `challenge_type`: How it's challenged (contradicts/undermines/requires_review)
- `description`: Why it's a contradiction

**Usage in Recommendations**:
1. High severity contradictions → Lower decision confidence
2. "contradicts" type → Strong recommendation for review
3. "undermines" type → Moderate confidence reduction
4. "requires_review" type → Flag for human attention

### 5. Integration Pattern

**Suggested Implementation**:

```typescript
// In your dashboard component
async function loadContradictionMetrics() {
  const dbClient = new SurrealDBClient('http://localhost:8000');

  // Get contradiction counts grouped by severity
  const counts = await dbClient.queryAllContradictionCounts();

  // Display in dashboard
  return {
    totalContradictions: Array.from(counts.values()).reduce((a, b) => a + b, 0),
    byDecision: counts,
    metrics: {
      criticalCount: /* count where severity='critical' */,
      highCount: /* count where severity='high' */,
      averageSeverity: /* calculate from data */
    }
  };
}

// For recommendation scoring
function adjustDecisionConfidence(decision, contradictions) {
  const contradictionsForDecision = contradictions.filter(
    c => c.decision_id === decision.id
  );

  const severityPenalty = contradictionsForDecision.reduce((penalty, c) => {
    switch(c.severity) {
      case 'critical': return penalty + 0.3;
      case 'high': return penalty + 0.2;
      case 'medium': return penalty + 0.1;
      default: return penalty;
    }
  }, 0);

  return Math.max(0, decision.confidence_score - severityPenalty);
}
```

## Performance Characteristics

- **Contradiction Detection**: ~2s end-to-end
- **SurrealDB Query**: <100ms for typical queries
- **Caching**: 5-minute TTL on query results
- **Scalability**: Handles 88 decisions × 44 lessons easily

## Testing

**Sample Test Data Available**:
```typescript
const sampleDecisions = [
  { id: 'use-typescript', rationale: '...', chosen_option: '...', ... },
  { id: 'agile-methodology', rationale: '...', chosen_option: '...', ... },
  // ... more decisions
];

const sampleLessons = [
  { id: 'typescript-overhead', key_insight: '...', implications: '...', ... },
  { id: 'agile-at-scale', key_insight: '...', implications: '...', ... },
  // ... more lessons
];
```

**Run Tests**:
```bash
npm run build
npx ts-node src/__tests__/SemanticContradictionDetector.test.ts
```

## Files Reference

### For Phase 7A (Dashboard):
- `src/services/SurrealDBClient.ts` - Query methods
- Query SurrealDB directly for aggregations

### For Phase 7B (Recommendations):
- `src/services/SemanticContradictionDetector.ts` - Contradiction detection logic
- Use `challenge_type` and `severity` for confidence adjustment

### Documentation:
- `PHASE_6C_SEMANTIC_CONTRADICTION_DETECTION.md` - Full algorithm details
- `SemanticContradictionDetector.test.ts` - Test examples

## Common Queries

### Contradiction Summary
```surreal
SELECT
  COUNT() as total,
  array::group(severity) as by_severity,
  array::group(challenge_type) as by_type
FROM decision_contradictions
WHERE detection_method = 'semantic'
```

### Decisions with Most Contradictions
```surreal
SELECT decision_id, COUNT() as contradiction_count
FROM decision_contradictions
WHERE detection_method = 'semantic'
GROUP BY decision_id
ORDER BY contradiction_count DESC
LIMIT 10
```

### Contradiction Timeline
```surreal
SELECT
  decision_id,
  lesson_id,
  severity,
  challenge_type
FROM decision_contradictions
WHERE detection_method = 'semantic'
ORDER BY timestamp DESC
LIMIT 20
```

## Troubleshooting

**No contradictions returned**:
- Check Ollama is running on `localhost:11434`
- Verify SurrealDB has decision and lesson data
- Check threshold (default 0.7 may be too high)

**SurrealDB query fails**:
- Verify `decision_contradictions` table exists
- Check `detection_method='semantic'` filter
- Ensure IAM permissions include SELECT

**Performance slow**:
- Contradictions detected once per run (~2s)
- Query cache is 5 minutes - clear if needed
- Use caching in dashboard to avoid repeated queries

## What's NOT in Phase 6C

- ❌ Real-time streaming contradictions
- ❌ UI components for displaying contradictions
- ❌ Automated contradiction resolution
- ❌ Interactive contradiction explorer

These are planned for future phases.

---

**Phase 6C Status**: ✅ COMPLETE and READY
**For Dashboard Engineers**: Phase 7A/7B can proceed
**Contact**: validation-engineer for questions on algorithm details
