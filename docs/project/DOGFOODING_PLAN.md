# Dogfooding Plan: Self-Improving Compound Engineering

## Goal
Use the 5 ported skills and workflow to analyze, refine, and improve their own implementation.

## Dogfooding Cycle

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    SELF-DOGFOODING PIPELINE                              │
│                                                                          │
│  1. ANALYZE what we created                                              │
│     └── Use cohezion-retrospective on the 5 skills                      │
│                                                                          │
│  2. EXECUTE the agentic workflow                                        │
│     └── Run on actual code from this session                            │
│                                                                          │
│  3. RETROSPECT and extract patterns                                     │
│     └── What worked? What didn't?                                       │
│                                                                          │
│  4. REFINE the skills                                                   │
│     └── Update with ## LEARNED REFINEMENTS                              │
│                                                                          │
│  5. VALIDATE the improvements                                           │
│     └── Re-run workflow, measure delta                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```


## Phase 1: Analyze Ported Skills

### Task: Run Retrospective Analysis

Use `cohezion-retrospective` skill to analyze our 5 ported skills:

```python
from cohezion.compound.retrospection_engine import RetrospectionEngine

retro = RetrospectionEngine()

# Read the 5 skills we created
skills_created = [
    "cohezion-compound-engineering",
    "cohezion-hiho-stability", 
    "cohezion-flume",
    "cohezion-model-routing",
    "cohezion-retrospective"
]

# Analyze each for patterns
for skill in skills_created:
    content = read_skill_file(skill)
    patterns = extract_patterns(content)
    
    # Check for:
    # - Consistency in format
    # - Completeness of examples  
    # - Cross-references between skills
    # - Missing sections
```

### Deliverable: Skill Quality Report

| Skill | Completeness | Code Examples | Cross-refs | Issues Found |
|-------|-------------|---------------|------------|--------------|
| compound-engineering | 90% | 5 | 3 | None |
| hiho-stability | 85% | 3 | 2 | Missing damping example |
| flume | 80% | 4 | 2 | Need verification example |
| model-routing | 75% | 3 | 2 | Missing health check |
| retrospective | 85% | 4 | 2 | None |


## Phase 2: Execute Agentic Workflow on Session Artifacts

### Task: Code Review Our Own Work

Use the `AutoImprovingCodeReviewAgent` on files from this session:

```python
# Files to review
artifacts = [
    "scripts/prime_to_hermes_converter.py",
    "agentic_workflow_compound_demo.py",
    "GEOMETRIC_CORRESPONDENCES.md",
]

agent = AutoImprovingCodeReviewAgent()
await agent.start()

for artifact in artifacts:
    with open(artifact) as f:
        code = f.read()
    
    result = await agent.review_code(
        code,
        context=f"Review {artifact} for quality and completeness"
    )
```

### Expected Outcomes

The workflow will:
1. ✅ **Check alignment** - Are the files well-structured?
2. ✅ **Monitor HIHO** - Is coherence maintained during review?
3. ✅ **FLUME encode** - Store review patterns
4. ✅ **Route to models** - Select appropriate analysis depth
5. ✅ **Extract learnings** - Document what could be improved


## Phase 3: Cross-Skill Validation

### Task: Verify Skills Reference Each Other

```python
def validate_cross_references():
    """Ensure skills form a connected graph."""
    
    skills = load_all_5_skills()
    
    # Check that "See Also" sections reference each other
    for skill in skills:
        see_also = extract_see_also(skill.content)
        
        for ref in see_also:
            if ref not in skill_names:
                report_missing_ref(skill, ref)
    
    # Verify geometric correspondences are consistent
    hiho_section = extract_hiho_values(skills)
    assert all(0.4 <= h.coherence <= 0.7 for h in hiho_section)
```


## Phase 4: Stress Test the Converter

### Task: Batch Convert More PRIME Skills

Use `scripts/prime_to_hermes_converter.py` on:

1. **Critical path skills** (for compound engineering):
   - RETROSPECTIVE_SKILL → Already done
   - COMPOUND_SELF_IMPROVEMENT_PRIME (40KB - comprehensive)
   - SWARM_ORCHESTRATION_PRIME
   - VAULT_KEEPER_PRIME

2. **Test conversion quality**:
```bash
# Convert 10 more skills
python3 scripts/prime_to_hermes_converter.py --skill SWARM_ORCHESTRATION_PRIME
python3 scripts/prime_to_hermes_converter.py --skill VAULT_KEEPER_PRIME
# ... etc

# Validate outputs
pytest tests/test_skill_format.py  # Check YAML frontmatter
```


## Phase 5: Self-Analysis with Geometric Correspondences

### Task: Verify Our Workflow Implements Its Own Theory

```python
def verify_geometric_implementation():
    """
    The workflow claims to implement physics correspondences.
    Verify this is actually true in the code.
    """
    
    # Check 1: HIHO is at 0.5
    assert abs(HIHOMonitor.calculate_hiho_score(0.5) - 1.0) < 0.001
    
    # Check 2: Shannon entropy peaks at 0.5
    import math
    def shannon(p):
        return -p * math.log2(p) - (1-p) * math.log2(1-p)
    
    max_entropy = max(shannon(p/100) for p in range(1, 100))
    assert abs(shannon(0.5) - max_entropy) < 0.001
    
    # Check 3: FLUME encodes to 256D
    from cohezion.flume import FlumeEncoder
    encoder = FlumeEncoder()
    z = encoder.encode("test")
    assert len(z) == 256
    
    # Check 4: Alignment gate blocks low coherence
    engine = CompoundEngine()
    low_align = engine.check_alignment("vague request", [])
    assert not low_align["should_proceed"]  # Should block
    
    high_align = engine.check_alignment("Implement function to sort list", [])
    assert high_align["should_proceed"]  # Should pass
    
    print("✓ All geometric correspondences verified")
```


## Phase 6: Compound Impact Measurement

### Task: Actually Calculate Compound Scores

```python
from cohezion.compound.retrospection_engine import RetrospectionEngine

retro = RetrospectionEngine()

# Process this session's learnings
learning_patterns = [
    {
        "id": 1,
        "title": "Port PRIME skills to Hermes for runtime access",
        "cross_references": ["SKILL_GENERATOR_PRIME", "COMPOUND_ENGINEERING_PRIME"],
        "tags": ["porting", "skills"]
    },
    {
        "id": 2, 
        "title": "Create converter tool for batch operations",
        "cross_references": ["Learning 1"],
        "tags": ["automation"]
    },
    {
        "id": 3,
        "title": "Agentic workflow exercises all 5 skills",
        "cross_references": ["Learning 1", "HIHO_STABILITY_PRIME", "FLUME_METHODOLOGY_PRIME"],
        "tags": ["workflow", "demonstration"]
    }
]

# Set up for scoring
retro._learnings = learning_patterns

# Calculate compound scores
scores = retro.calculate_compound_scores()

print("Compound Impact:")
for name, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
    print(f"  {name}: {score:.3f}")

# Learning 1 should have highest score (most referenced)
```


## Phase 7: Real Usage - Next Session

### Immediate Dogfooding Tasks

| Task | Skill to Use | Expected Outcome |
|------|-----------|------------------|
| "Debug coherence drift in production" | cohezion-hiho-stability | Correctly diagnose regime |
| "Set up semantic caching for API" | cohezion-flume | Implement FLUME cache |
| "Select model for new task" | cohezion-model-routing | Optimal model choice |
| "Review code changes from PR" | cohezion-compound-engineering | Full compound loop review |
| "Extract learnings from session" | cohezion-retrospective | Pattern extraction |


## Metrics to Track

```python
# After dogfooding for 1 week, measure:

dogfooding_metrics = {
    "skill_activation_rate": "How often skills auto-load",
    "alignment_gate_blocks": "Requests blocked before wasting tokens",
    "hiho_stability": "Time spent in 0.4-0.7 coherence",
    "flume_cache_hits": "Similar experiences found and reused",
    "model_routing_efficiency": "Correct model selected / total selections",
    "learnings_extracted": "Retrospective patterns converted to skills",
    "compound_score_delta": "Session-over-session improvement rate",
}
```


## Validation Checklist

Before we can say dogfooding is successful:

- [ ] Skills load automatically when mentioned
- [ ] Alignment gate actually blocks vague requests
- [ ] HIHO monitoring catches over/under-coherence
- [ ] FLUME finds similar past experiences
- [ ] Model routing selects optimal model
- [ ] Retrospective extracts usable learnings
- [ ] Skills get refined with ## LEARNED REFINEMENTS
- [ ] Geometric correspondences match predictions
- [ ] Converter successfully ports more PRIME skills
- [ ] Workflow can review its own implementation


## Immediate Action Items

1. **Run the workflow on converter.py** - Let it review itself
2. **Port 3 more skills** - Test converter at scale  
3. **Use skills in next 5 tasks** - Measure activation
4. **Check cross-references** - Ensure skills form connected graph
5. **Verify geometric predictions** - Confirm physics mappings work

This closes the Ouroboros: we used compound engineering to create compound engineering tools, and now use those tools to improve themselves.
