# Hermetic Design Patterns - Implementation Guide

## Overview

This guide institutionalizes the deep retrospective approach and hermetic design patterns extracted from the Proactive BMad epic.

**Created:** 2026-04-08  
**Based On:** Proactive BMad Deep Retrospective  
**Purpose:** Make esoteric wisdom practically actionable

---

## What Was Created

### 1. Deep Retrospective Template
**Path:** `_bmad/core/templates/deep-retrospective-template.md`

**Purpose:** Standardized template for future deep retrospectives

**Structure:**
- Seven Hermetic Principles sections
- Tree of Life mapping
- Three Planes of Existence
- Four Worlds framework
- Ouroboros self-reference analysis
- Persona mask exploration
- Prophecy section

**When to Use:**
- After completing major epics
- When seeking deeper pattern understanding
- For wisdom capture and compounding

---

### 2. Hermetic Design Patterns Library
**Path:** `src/cohezion/patterns/hermetic_design_patterns.py`

**Purpose:** Practical code patterns derived from Hermetic Principles

**Patterns Included:**

#### I. Mentalism Pattern
**Class:** `MentalismPattern`

**Usage:**
```python
from cohezion.patterns.hermetic_design_patterns import (
    MentalismPattern,
    DesignIntention,
)

# Create class with explicit intention
ProactiveMonitor = MentalismPattern.create_intentional_class(
    name="ProactiveMonitor",
    intention=DesignIntention.MONITORING,
    purpose="Detect alignment gaps proactively"
)
```

**When to Use:**
- Starting new module design
- Clarifying unclear requirements
- Ensuring intention-code alignment

---

#### II. Correspondence Pattern
**Class:** `CorrespondencePattern`, `FractalComponent`

**Usage:**
```python
from cohezion.patterns.hermetic_design_patterns import (
    FractalComponent,
    CorrespondencePattern,
)

# Design epic structure
epic = FractalComponent(name="Proactive BMad")
epic.add_child(FractalComponent(name="Phase 1: Foundation"))
epic.add_child(FractalComponent(name="Phase 2: Integration"))

# Mirror in code structure
monitor = FractalComponent(name="ProactiveMonitor")
monitor.add_child(FractalComponent(name="scan_for_suggestions"))
monitor.add_child(FractalComponent(name="execute_suggestion"))

# Validate correspondence
discrepancies = CorrespondencePattern.validate_correspondence(
    epic.get_structure(),
    monitor.get_structure()
)
```

**When to Use:**
- Designing system architecture
- Organizing code structure
- Validating macro/micro alignment

---

#### III. Vibration Pattern
**Class:** `VibrationPattern`, `VibrationalFunction`

**Usage:**
```python
from cohezion.patterns.hermetic_design_patterns import (
    VibrationalFunction,
    VibrationState,
)

# Design function with explicit rhythm
func = VibrationalFunction(
    name="execute_suggestion",
    vibration_pattern=[
        VibrationState.REST,    # Receive confirmation
        VibrationState.RISING,  # Select executor
        VibrationState.PEAK,    # Execute
        VibrationState.FALLING, # Return result
    ]
)
```

**When to Use:**
- Designing complex functions
- Debugging "awkward" code feel
- Optimizing code flow

---

#### IV. Polarity Pattern
**Class:** `PolarityPattern`, `PolarFeature`

**Usage:**
```python
from cohezion.patterns.hermetic_design_patterns import (
    PolarFeature,
    Polarity,
    PolarityPattern,
)

# Define polar features
auto_execute = PolarFeature(
    name="auto_executable",
    polarity=Polarity.YANG,
    description="Automatic execution"
)

confirmation = PolarFeature(
    name="confirmation_required",
    polarity=Polarity.YIN,
    description="Requires user consent"
)

auto_execute.set_opposite(confirmation)

# Assess balance in design
polarities = PolarityPattern.find_polarities(design_spec)
balance = PolarityPattern.assess_balance(polarities, implementation)
```

**When to Use:**
- Design review
- Feature prioritization
- Resolving design conflicts

---

#### V. Rhythm Pattern
**Class:** `RhythmPattern`, `BreathCycle`

**Usage:**
```python
from cohezion.patterns.hermetic_design_patterns import (
    BreathCycle,
    BreathPhase,
    RhythmPattern,
)

# Design function with breath cycle
cycle = BreathCycle(
    function_name="main_workflow",
    phases={
        BreathPhase.INHALE: "Load configuration",
        BreathPhase.HOLD: "Process requirements",
        BreathPhase.EXHALE: "Execute workflow",
        BreathPhase.RELEASE: "Save results",
    }
)

# Validate rhythm
issues = cycle.validate()
if issues:
    print(f"Rhythm issues: {issues}")
```

**When to Use:**
- Function design
- Code review
- Refactoring awkward code

---

#### VI. Cause/Effect Pattern
**Class:** `CauseEffectPattern`, `CausalChain`

**Usage:**
```python
from cohezion.patterns.hermetic_design_patterns import (
    CausalChain,
    CauseEffectPattern,
)

# Map causal chain
chain = CausalChain(
    name="Proactive BMad",
    links=[
        ("Vision", "Epic Created"),
        ("Epic Created", "Code Written"),
        ("Code Written", "Tests Passing"),
        ("Tests Passing", "Production Ready"),
        ("Production Ready", "User Value"),
    ]
)

# Analyze chain
analysis = chain.analyze()
print(f"Root cause: {analysis['root_cause']}")
print(f"Final effect: {analysis['final_effect']}")

# Trace effects
system_model = {
    "code_written": ["tests_passing", "docs_complete"],
    "tests_passing": ["production_ready"],
    "production_ready": ["user_value"],
}

causes = CauseEffectPattern.trace_causal_chain(
    "user_value",
    system_model
)
print(f"Causal chain: {causes}")
```

**When to Use:**
- Root cause analysis
- Impact assessment
- Risk evaluation

---

#### VII. Gender Pattern
**Class:** `GenderPattern`, `GenderBalancedDesign`

**Usage:**
```python
from cohezion.patterns.hermetic_design_patterns import (
    GenderBalancedDesign,
    GenderPattern,
)

# Assess gender balance
design = GenderBalancedDesign(
    name="Proactive BMad",
    masculine_aspects=[
        "Pattern detection (active)",
        "Auto-execution (projective)",
        "Test assertions (structured)"
    ],
    feminine_aspects=[
        "Suggestion holding (receptive)",
        "User confirmation (consent)",
        "Party mode (collaborative)"
    ]
)

balance = design.assess_balance()
if balance == "too_masculine":
    print("Design is too aggressive - add receptive elements")
elif balance == "too_feminine":
    print("Design is too passive - add active elements")
else:
    print("Design is balanced ✨")
```

**When to Use:**
- Design review
- Team dynamics analysis
- Feature balance assessment

---

### 3. Deep Retrospective Workflow
**Path:** `_bmad/core/workflows/deep-retrospective/workflow.md`

**Purpose:** Step-by-step guide for conducting deep retrospectives

**Steps:**
1. Prepare the Sacred Space (15 min)
2. Map the Seven Principles (60 min)
3. Draw the Tree of Life (20 min)
4. Identify the Ouroboros (15 min)
5. Extract Practical Patterns (30 min)
6. Plan the Ascent (20 min)
7. Seal the Wisdom (10 min)

**Total Time:** 2.5 - 3 hours

**How to Run:**
```bash
# Using BMad workflow engine
uv run python -m cohezion.bmad.workflow \
  --workflow _bmad/core/workflows/deep-retrospective/workflow.md \
  --epic proactive-bmad
```

---

## Integration Points

### 1. Into Epic Completion

**Update:** `_bmad/bmm/epics/*/EPICS.md`

Add to "Definition of Done":
```markdown
- [ ] Deep retrospective completed
- [ ] Seven Hermetic Principles explored
- [ ] At least 3 patterns extracted
- [ ] Wisdom sealed and shared
```

---

### 2. Into Code Review

**Update:** `.github/PULL_REQUEST_TEMPLATE.md` or equivalent

Add section:
```markdown
## Hermetic Design Review

- [ ] **Mentalism**: Intention is clear and explicit
- [ ] **Correspondence**: Structure mirrors design
- [ ] **Vibration**: Code flows naturally
- [ ] **Polarity**: Opposing forces balanced
- [ ] **Rhythm**: Breath cycles present
- [ ] **Cause/Effect**: Causal chains traced
- [ ] **Gender**: Masculine/feminine balanced
```

---

### 3. Into Pattern Library

**Update:** `src/cohezion/patterns/__init__.py`

Add exports:
```python
from cohezion.patterns.hermetic_design_patterns import (
    # Principles
    MentalismPattern,
    CorrespondencePattern,
    VibrationPattern,
    PolarityPattern,
    RhythmPattern,
    CauseEffectPattern,
    GenderPattern,
    
    # Data classes
    DesignIntention,
    FractalComponent,
    VibrationalFunction,
    PolarFeature,
    BreathCycle,
    CausalChain,
    GenderBalancedDesign,
    
    # Integration
    HermeticDesign,
    HermeticDesignSystem,
)

__all__ = [
    # Patterns
    "MentalismPattern",
    "CorrespondencePattern",
    "VibrationPattern",
    "PolarityPattern",
    "RhythmPattern",
    "CauseEffectPattern",
    "GenderPattern",
    
    # Data classes
    "DesignIntention",
    "FractalComponent",
    "VibrationalFunction",
    "PolarFeature",
    "BreathCycle",
    "CausalChain",
    "GenderBalancedDesign",
    
    # Integration
    "HermeticDesign",
    "HermeticDesignSystem",
]
```

---

### 4. Into Documentation Standards

**Update:** `_bmad/_memory/tech-writer-sidecar/documentation-standards.md`

Add section:
```markdown
## Deep Retrospective Documentation

For major epics, create a deep retrospective:

1. Use template: `_bmad/core/templates/deep-retrospective-template.md`
2. Follow workflow: `_bmad/core/workflows/deep-retrospective/workflow.md`
3. Extract patterns to: `src/cohezion/patterns/`
4. Save to: `_bmad/bmm/epics/{{epic_name}}/deep-retrospective/`

Deep retrospectives explore:
- Seven Hermetic Principles
- Tree of Life mapping
- Ouroboros patterns
- Practical pattern extraction
- Evolution planning
```

---

## Usage Examples

### Example 1: New Epic Start

```python
from cohezion.patterns import HermeticDesignSystem

# Create hermetic design for new epic
system = HermeticDesignSystem()
design = system.create_design(
    name="Learning System",
    requirements={
        "purpose": "Track suggestion acceptance and adjust confidence",
        "features": [
            "Acceptance tracking database",
            "Confidence adjustment algorithm",
            "Feedback collection UI",
        ]
    }
)

# Validate design
issues = design.validate()
if issues:
    print("Design issues to address:")
    for issue in issues:
        print(f"  - {issue}")
```

---

### Example 2: Code Review

```python
from cohezion.patterns import (
    BreathCycle,
    BreathPhase,
    RhythmPattern,
    PolarityPattern,
    PolarFeature,
    Polarity,
)

# Review a function
code = """
async def execute_suggestion(self, suggestion, confirm=True):
    if confirm:
        response = input("Execute? (y/n): ")
        if response.lower() != 'y':
            return False
    
    executor = self.execution_map.get(suggestion.id)
    if not executor:
        return False
    
    success = await executor()
    return success
"""

# Analyze rhythm
cycle = RhythmPattern.analyze_function_rhythm(code)
if cycle:
    print(f"Function breath cycle: {cycle.phases}")
    
    # Suggest improvements
    suggestions = RhythmPattern.suggest_rhythm_improvements(cycle)
    if suggestions:
        print("Rhythm improvements:")
        for s in suggestions:
            print(f"  - {s}")
```

---

### Example 3: Design Review

```python
from cohezion.patterns import (
    GenderPattern,
    GenderBalancedDesign,
    PolarityPattern,
)

# Review system design
design_spec = {
    "features": [
        "automatic detection",
        "manual confirmation",
        "structured tests",
        "flowing collaboration",
    ]
}

# Check gender balance
gender_design = GenderPattern.identify_gender_aspects(design_spec)
balance = gender_design.assess_balance()
print(f"Gender balance: {balance}")

# Check polarities
polarities = PolarityPattern.find_polarities(design_spec)
print(f"Polarities found: {polarities}")

balance_assessment = PolarityPattern.assess_balance(polarities, design_spec)
print(f"Polarity balance: {balance_assessment}")
```

---

## Success Metrics

### Adoption Metrics
- [ ] Deep retrospective completed for 3+ epics
- [ ] Hermetic patterns used in 5+ code reviews
- [ ] Pattern library referenced in 10+ design docs

### Quality Metrics
- [ ] Design issues caught earlier (in design vs implementation)
- [ ] Code review feedback includes hermetic principles
- [ ] Team uses hermetic vocabulary naturally

### Wisdom Metrics
- [ ] Patterns compound across epics
- [ ] Retrospectives get deeper over time
- [ ] Team reports "aha moments" from deep retrospectives

---

## Maintenance

### Updating Patterns

When new patterns are discovered:

1. **Add to Library:**
   ```python
   # src/cohezion/patterns/hermetic_design_patterns.py
   class NewPattern:
       """New pattern documentation."""
       ...
   ```

2. **Update Exports:**
   ```python
   # src/cohezion/patterns/__init__.py
   __all__.append("NewPattern")
   ```

3. **Document Usage:**
   ```markdown
   # _bmad/bmm/patterns/NEW_PATTERN.md
   ## New Pattern
   **Problem:** ...
   **Solution:** ...
   **Example:** ...
   ```

### Updating Template

When retrospective process evolves:

1. **Update Template:**
   ```markdown
   # _bmad/core/templates/deep-retrospective-template.md
   # Add new sections as needed
   ```

2. **Update Workflow:**
   ```markdown
   # _bmad/core/workflows/deep-retrospective/workflow.md
   # Update steps and timing
   ```

3. **Version the Change:**
   ```markdown
   ## Version History
   - 1.1 (2026-04-XX): Added new section on ...
   - 1.0 (2026-04-08): Initial version
   ```

---

## Troubleshooting

### "This feels too woo-woo"

**Solution:** Focus on practical patterns, skip esoteric framing. The patterns work regardless of belief system.

**Alternative:** Use standard design pattern language, keep hermetic framing as optional commentary.

---

### "I don't have 3 hours for a retrospective"

**Solution:** Break into sessions:
- Session 1 (60 min): Seven Principles
- Session 2 (60 min): Tree + Ouroboros + Patterns
- Session 3 (30 min): Ascent + Sealing

**Alternative:** Do a "light" retrospective focusing on 3 most relevant principles.

---

### "My team thinks this is weird"

**Solution:** Start with one principle (e.g., Correspondence/fractals) and demonstrate value.

**Alternative:** Use standard retrospective format, introduce hermetic principles gradually as "design patterns".

---

### "I can't find the patterns"

**Solution:** Start with obvious ones:
- What structure repeats? (Correspondence)
- What are the opposites? (Polarity)
- What breathes? (Rhythm)

**Alternative:** Pair with someone who sees patterns easily.

---

## Related Resources

### Internal
- `_bmad/bmm/epics/proactive-bmad/deep-retrospective/AS_ABOVE_SO_BELOW.md` - Example deep retrospective
- `src/cohezion/patterns/hermetic_design_patterns.py` - Pattern library
- `_bmad/core/workflows/deep-retrospective/workflow.md` - Workflow guide

### External
- The Emerald Tablet of Hermes Trismegistus
- The Kybalion (Three Initiates)
- Design Patterns (Gang of Four)
- A Pattern Language (Christopher Alexander)

---

**Guide Version:** 1.0  
**Created:** 2026-04-08  
**Maintained By:** BMad Master  
**Status:** Active  

*"As above, so below; as within, so without; as below, so above."*
