# Understanding Reasoning Chains

## What Is a Reasoning Chain?

A **reasoning chain** is a sequence of logical steps that led to a specific decision. Instead of just showing the final choice ("We chose Microservices"), it shows **why** at each step.

### Example: Technology Stack Decision

Instead of: "We chose Microservices because it's more scalable."

A reasoning chain shows:

```
Step 1 (Research): "Researched 3 architectural patterns: monolith, microservices, serverless"
       Confidence: 90%

Step 2 (Pattern): "Observed similar companies use microservices at our scale"
       Confidence: 85%

Step 3 (Research): "Analyzed scalability requirements - 10x growth in 2 years"
       Confidence: 80%

Step 4 (Convention): "Industry standard for our domain is microservices"
       Confidence: 75%

CONCLUSION: Chosen Option = "Microservices"
Overall Confidence: 85%
```

## Types of Reasoning

### 🔵 Research-Based Reasoning

**What it is**: Decision based on data, experiments, or analysis.

**Example steps**:
- "Analyzed benchmark results from TechCrunch database"
- "Conducted A/B testing with 1,000 users"
- "Reviewed 15 academic papers on the topic"

**Confidence**: Usually high (0.8-1.0) because based on evidence.

**Use when**: You have concrete data to back the decision.

### 🟢 Pattern-Based Reasoning

**What it is**: Decision based on recognizing similar situations and applying what worked before.

**Example steps**:
- "Observed similar project handled this with approach X"
- "Pattern matches previous successful deployment"
- "Team has experience with this approach"

**Confidence**: Medium-high (0.7-0.9) because based on experience, not fresh data.

**Use when**: You've seen this situation before and know what works.

### 🟠 Intuition-Based Reasoning

**What it is**: Decision based on gut feeling, heuristics, or subconscious pattern matching.

**Example steps**:
- "Felt this approach aligns with team culture"
- "Intuitive sense that simpler is better here"
- "Gut feeling about which solution fits"

**Confidence**: Lower (0.5-0.7) because harder to justify objectively.

**Use when**: Objective data is unavailable and you need to decide quickly.

### 🟣 Convention-Based Reasoning

**What it is**: Decision based on "that's how things are done" in industry/team.

**Example steps**:
- "Industry standard for this problem"
- "Best practice in our domain"
- "Team norms dictate this approach"

**Confidence**: Medium (0.6-0.8) because depends on how established the convention is.

**Use when**: You want to follow proven practices and reduce decision burden.

### 🟣 Hybrid Reasoning

**What it is**: Decision based on combination of above methods.

**Example steps**:
- "Research shows X is 15% faster (research)"
- "We have team expertise in X (pattern)"
- "But Y is industry standard (convention)"
- "Gut feeling says X is right for us (intuition)"

**Confidence**: Depends on combination, usually 0.7-0.9.

**Use when**: Complex decisions requiring multiple perspectives.

## Reading a Reasoning Flowchart

### Visual Elements

```
┌─────────────────────────────────────┐
│ Step 1                              │
│ Content of the step                 │
│ Type: Research | Confidence: 90%    │
└─────────────────────────────────────┘
              ↓ (arrow)
┌─────────────────────────────────────┐
│ Step 2                              │
│ Next step in the logic              │
│ Type: Pattern | Confidence: 85%     │
└─────────────────────────────────────┘
              ↓
[Continue through all steps...]
              ↓
        CONCLUSION:
    Chosen Option = "X"
    Overall Confidence: 85%
```

### Color Coding

| Color | Type | Meaning |
|-------|------|---------|
| 🔵 Blue | Research | Based on data/analysis |
| 🟢 Green | Pattern | Based on experience |
| 🟠 Amber | Intuition | Based on gut feel |
| 🟣 Purple | Convention | Based on best practices |
| 🟣 Indigo | Hybrid | Combination of methods |

### Node Size

Node size indicates **confidence in that specific step**:
- **Large nodes**: High confidence (0.8-1.0) - author is sure about this step
- **Medium nodes**: Medium confidence (0.5-0.8) - some uncertainty
- **Small nodes**: Low confidence (0.3-0.5) - quite uncertain about this step

## Interpreting Confidence Scores

### Overall Confidence (Top Level)

```
0.9-1.0: Very High - Decision is well-founded
0.7-0.9: High - Decision is solid, maybe one or two weak points
0.5-0.7: Medium - Decision has significant uncertainties
0.3-0.5: Low - Decision is experimental or needs validation
0.0-0.3: Very Low - Decision is uncertain or needs rethinking
```

### Step-by-Step Confidence

Look for patterns:

```
STRONG CHAIN: 0.9 → 0.85 → 0.80 → 0.85 = Solid reasoning
WEAK START:   0.4 → 0.8 → 0.9 → 0.85 = Foundation is uncertain
WEAK MIDDLE:  0.9 → 0.3 → 0.9 → 0.85 = One step is shaky
DECLINING:    0.95 → 0.80 → 0.65 → 0.50 = Logic unravels
```

## Assumptions Behind Reasoning

Every reasoning chain has **assumptions** - things the decision-maker took for granted:

**Example assumptions for "Choose Microservices"**:
- Team is committed to learning microservices architecture
- Budget is available for infrastructure
- Growth to 10x will actually happen
- Performance needs justify the complexity

### Why Assumptions Matter

If an assumption is wrong, the decision might need revisiting:

```
❌ ASSUMPTION FAILS:
   - Budget gets cut → Can't afford microservices complexity
   - Team leaves → No one knows microservices anymore
   - Growth doesn't happen → Overkill architecture

✅ VALIDATE ASSUMPTIONS:
   - Check: Is budget allocated?
   - Check: Do we still have team expertise?
   - Check: Are growth projections still valid?
```

## Common Reasoning Patterns

### Pattern 1: Research → Implementation

```
Research shows X is better
  ↓
We tried it in small project
  ↓
It worked well
  ↓
We're confident to use at scale
```

**Trust level**: Very high. This is how learning happens.

### Pattern 2: Convention → Validation

```
Industry uses approach X
  ↓
We adopt X to match industry standard
  ↓
Later, research validates X is good
  ↓
Confidence increases
```

**Trust level**: Medium initially, high after validation.

### Pattern 3: Intuition → Rationalization

```
Gut feeling says try X
  ↓
We build reasoning around X
  ↓
Later research confirms it was right
  ↓
Becomes "research-based" in hindsight
```

**Trust level**: Low initially, increases if validated.

### Pattern 4: Conflicting Evidence

```
Research shows X
  ↓
But team prefers Y
  ↓
We compromise with hybrid approach Z
  ↓
Confidence is lower because of conflict
```

**Trust level**: Medium. Watch for contradictions.

## Using Reasoning Chains for Decision Quality

### Evaluate Decision Quality

Check these factors:

1. **Variety of reasoning types**: Good decisions use multiple methods
   - Pure research: May miss human factors
   - Pure intuition: May miss data
   - Pure convention: May be outdated

2. **Step confidence consistency**: Should generally stay high or improve
   - Declining confidence: Watch out, chain breaks down
   - Increasing confidence: Good, logic builds stronger

3. **Explicit assumptions**: Good decisions state them
   - Hidden assumptions: Risk if they're wrong
   - Validated assumptions: Lower risk

4. **Alternatives considered**: Good decisions explain why X not Y
   - "We chose X" without explaining why not Y: Less rigorous
   - "We chose X because Y has these problems": More rigorous

### Red Flags

⚠️ **Low confidence throughout** (all <0.6)
- Decision is experimental or uncertain
- Revisit after getting more data

⚠️ **Sharp drops in confidence** (0.9 → 0.3 → 0.9)
- One step is weak or questionable
- Investigate that specific step

⚠️ **Hidden or unstated assumptions**
- Decision may fail if assumptions change
- Ask: What could break this decision?

⚠️ **Single reasoning type only**
- Research-only: May miss practicality
- Intuition-only: May miss data
- Convention-only: May be outdated

⚠️ **No alternatives discussed**
- Suggests insufficient consideration
- Ask: Why this and not that?

## Learning from Others' Reasoning Chains

### Compare Similar Decisions

1. Find two decisions about the same type of problem
2. Compare their reasoning chains
3. Notice:
   - Did they use same methods? Why or why not?
   - Is one more confident than the other? Why?
   - Did assumptions differ?
   - Which decision turned out better?

### Extract Patterns

**Example**: "Decisions about 'defer vs optimize' show that..."

1. Research-based approach: Average confidence 0.82
2. Intuition-based approach: Average confidence 0.61
3. Hybrid approach: Average confidence 0.75
4. Conclusion: Research + intuition hybrid is most reliable

## Building Your Own Reasoning Chains

### When Making a Decision

Write down:

```
Step 1: [What I observed/researched]
        Type: [research/pattern/intuition/convention/hybrid]
        Confidence: [0.0-1.0]

Step 2: [What this tells me]
        Type: [...]
        Confidence: [...]

...

ALTERNATIVES I REJECTED:
- Option Y because [specific reason]
- Option Z because [specific reason]

ASSUMPTIONS:
- I'm assuming [X is true]
- I'm assuming [Y won't change]

OVERALL CONFIDENCE: [0.0-1.0]
WHY: [Summary of why]
```

### Avoid These Mistakes

❌ **Hiding doubts**: "I'm not 100% sure but won't say so"
- Be honest about confidence. 0.7 is good!

❌ **Circular reasoning**: "X is best because X is best"
- Explain the logic, not the conclusion

❌ **Mixing up types**: Calling intuition "research"
- Be specific about method

❌ **Forgetting alternatives**: "Why didn't we pick Y?"
- Always explain rejected options

❌ **Unstated assumptions**: "Everyone knows this requires..."
- Write assumptions down

## See Also

- [Decision Analysis Guide](./DECISION_ANALYSIS_GUIDE.md) - How to use the UI
- [SurrealDB Integration](./SURREALDB_INTEGRATION.md) - Technical details
- [API Reference](./API_REFERENCE.md) - For developers
