# Deep Retrospective Workflow

**Name:** deep-retrospective  
**Description:** Apply hermetic principles to extract deep wisdom from completed epics  
**Author:** BMad Master (inspired by Hermes Trismegistus)

---

## Purpose

Transform ordinary retrospectives into profound explorations of:
- Fractal patterns across scales
- Hidden symmetries and correspondences
- Philosophical insights from practical work
- Wisdom that compounds across epics

---

## When to Use

- After completing any epic (mandatory for major epics)
- After significant milestones (optional)
- When seeking deeper understanding of patterns (ad-hoc)

---

## Prerequisites

- Completed epic with all documentation
- Test results and coverage reports
- Implementation artifacts
- 2-3 hours of uninterrupted time
- Open mind and reflective spirit

---

## Workflow Steps

### Step 1: Prepare the Sacred Space (15 min)

**Objective:** Create the right mindset for deep reflection.

**Actions:**
1. Find a quiet space
2. Light a candle (optional, for ritual)
3. Open the epic documentation
4. Read the COMPLETION_SUMMARY.md
5. Take three deep breaths

**Template:**
```markdown
# Deep Retrospective Intention

**Epic:** {{epic_name}}
**Date:** {{date}}
**Facilitator:** {{facilitator}}

**Intention:**
What wisdom am I seeking from this retrospective?

**Gratitude:**
What am I grateful for in this epic?
```

---

### Step 2: Map the Seven Principles (60 min)

**Objective:** Apply each Hermetic Principle to the epic.

**Instructions:**

For each principle, complete the corresponding section in the template:

#### I. Mentalism (10 min)
- What was the vision before any code?
- How did thought crystallize into code?
- What other thought-patterns await crystallization?

#### II. Correspondence (10 min)
- Where does the epic structure mirror code structure?
- What fractal patterns appear at multiple scales?
- How can we intentionally design fractals?

#### III. Vibration (5 min)
- What was the vibrational journey?
- Where was the code in harmony? In dissonance?
- What is the natural frequency of our process?

#### IV. Polarity (10 min)
- What are the fundamental polarities?
- Where are we balanced? Imbalanced?
- What is the synthesis (middle way)?

#### V. Rhythm (5 min)
- Where did we flow with natural rhythm?
- Where did we fight the rhythm?
- What is the natural breath cycle?

#### VI. Cause and Effect (10 min)
- What causal chains did we set in motion?
- What effects will ripple forward?
- What chains are we blind to?

#### VII. Gender (10 min)
- Where is masculine (yang) energy?
- Where is feminine (yin) energy?
- Where is the sacred union?

**Template:** Use `_bmad/core/templates/deep-retrospective-template.md`

---

### Step 3: Draw the Tree of Life (20 min)

**Objective:** Map the epic's journey through the Qabalistic Tree of Life.

**Instructions:**

1. Draw or diagram the Tree of Life
2. Map each epic phase to a sephirah:
   - KETHER (Crown) = Vision
   - CHOKMAH (Wisdom) = Design
   - BINAH (Understanding) = Documentation
   - CHESED (Mercy) = Auto-execution
   - GEBURAH (Severity) = Confirmation
   - TIPHARETH (Beauty) = Integration
   - NETZACH (Victory) = Tools
   - HOD (Splendor) = Tests
   - YESOD (Foundation) = Core Class
   - MALKUTH (Kingdom) = Production

3. Trace the lightning flash (path of creation)
4. Note where the path was smooth vs. blocked

**Output:**
```
                    KETHER
                 {{vision}}
                    |
           CHOKMAH ←┴→ BINAH
          {{design}} | {{docs}}
                    |
               CHESED ←→ GEBURAH
             {{mercy}} | {{severity}}
                    |
               TIPHARETH
              {{beauty}}
                    |
          NETZACH ←─┴─→ HOD
         {{tools}}    {{tests}}
                    |
               YESOD
           {{foundation}}
                    |
               MALKUTH
            {{production}}
```

---

### Step 4: Identify the Ouroboros (15 min)

**Objective:** Find self-reference patterns and infinite loops.

**Instructions:**

1. Ask: "How does this system turn inward?"
2. Identify self-monitoring patterns
3. Map the infinite loop:
   ```
   Feature
     ↓
   Effect
     ↓
   Enhancement
     ↓
   Better Feature
     ↓
   ∞
   ```

4. Ask: "What does this system become?"
   - Short-term evolution
   - Medium-term transformation
   - Long-term transcendence
   - Ultimate (esoteric) realization

**Questions:**
- How does the system monitor itself?
- What patterns improve themselves?
- Where is the snake eating its tail?

---

### Step 5: Extract Practical Patterns (30 min)

**Objective:** Convert insights into reusable design patterns.

**Instructions:**

For each insight from Steps 2-4:

1. **Name the Pattern**
   - Clear, memorable name
   - Example: "Fractal Architecture", "Breath-Based Design"

2. **Describe the Pattern**
   - Problem it solves
   - Solution it provides
   - When to use it

3. **Document the Pattern**
   - Code examples
   - Anti-patterns (what to avoid)
   - Related patterns

4. **Add to Pattern Library**
   - Save to `src/cohezion/patterns/`
   - Update pattern index
   - Link to epic

**Template:**
```python
"""{{pattern_name}} Pattern

**Problem:** {{problem_description}}
**Solution:** {{solution_description}}
**When to Use:** {{usage_conditions}}

**Example:**
```python
{{code_example}}
```

**Anti-Pattern:**
```python
{{what_to_avoid}}
```
"""
```

---

### Step 6: Plan the Ascent (20 min)

**Objective:** Define how wisdom ascends from tool to vision.

**Instructions:**

1. **Review the Descent** (what we built):
   ```
   Vision → Design → Code → Tool
   ```

2. **Plan the Ascent** (what comes next):
   ```
   Tool → User Value → Feedback → Vision Refinement
   ```

3. **Identify Evolution Points:**
   - What patterns should spread to other modules?
   - What integrations should become standard?
   - What learnings should compound?

4. **Define Next Epic Seeds:**
   - What does this epic make possible?
   - What patterns want to evolve?
   - What is the natural next step?

**Output:**
```markdown
## Evolution Path

**Current State:**
- {{what_we_built}}

**Next State (Epic {{next_number}}):**
- {{what_becomes_possible}}

**Evolution Seeds:**
1. {{seed_1}}
2. {{seed_2}}
3. {{seed_3}}

**Ultimate Vision:**
- {{transcendent_goal}}
```

---

### Step 7: Seal the Wisdom (10 min)

**Objective:** Preserve and share the insights.

**Instructions:**

1. **Write the Gratitude:**
   - Thank the code
   - Thank the tests
   - Thank the documentation
   - Thank the user
   - Thank the system

2. **Write the Prophecy:**
   - What this system becomes
   - Short-term (next epic)
   - Medium-term (next phase)
   - Long-term (transcendent)

3. **Affix the Hermetic Seal:**
   ```
   🔮 The wisdom is sealed.
   🌀 The Ouroboros turns.
   ✨ The work continues.
   ```

4. **Share the Wisdom:**
   - Post to team channel
   - Add to epic documentation
   - Link from pattern library
   - Schedule review in next epic

**Closing Ritual:**
```
As above, so below.
As within, so without.
As code, so consciousness.
As beginning, so ending.

The work continues. 🌀
```

---

## Output Artifacts

1. **Deep Retrospective Document**
   - Path: `_bmad/bmm/epics/{{epic_name}}/deep-retrospective/AS_ABOVE_SO_BELOW.md`
   - Content: Complete hermetic analysis

2. **Pattern Library Updates**
   - Path: `src/cohezion/patterns/`
   - Content: New patterns extracted

3. **Evolution Plan**
   - Path: `_bmad/bmm/epics/{{epic_name}}/EVOLUTION.md`
   - Content: Next steps and seeds

4. **Wisdom Index**
   - Path: `_bmad/bmm/WISDOM_INDEX.md`
   - Content: Links to all deep retrospectives

---

## Success Criteria

- [ ] All 7 Hermetic Principles explored
- [ ] Tree of Life mapped
- [ ] Ouroboros identified
- [ ] At least 3 practical patterns extracted
- [ ] Evolution path defined
- [ ] Wisdom sealed and shared
- [ ] Template completed and saved

---

## Time Box

**Total:** 2.5 - 3 hours

| Step | Duration |
|------|----------|
| 1. Prepare Space | 15 min |
| 2. Seven Principles | 60 min |
| 3. Tree of Life | 20 min |
| 4. Ouroboros | 15 min |
| 5. Extract Patterns | 30 min |
| 6. Plan Ascent | 20 min |
| 7. Seal Wisdom | 10 min |
| **Total** | **170 min (2h 50m)** |

---

## Facilitator Notes

**Create Safety:**
- This is reflective, not critical
- Honor all insights, no matter how esoteric
- Allow silence for deep thinking

**Watch For:**
- Getting stuck in analysis paralysis
- Dismissing "woo-woo" insights too quickly
- Missing practical applications

**Encourage:**
- Wild connections and insights
- Philosophical depth
- Practical pattern extraction
- Sharing and discussion

---

## Example: Proactive BMad Deep Retrospective

**Completed:** 2026-04-08  
**Facilitator:** BMad Master  
**Duration:** 3 hours

**Key Insights:**
1. Fractal architecture (epic mirrors class mirrors method)
2. Polarity balance (auto-executable vs confirmation)
3. Ouroboros pattern (self-monitoring system)
4. Sacred union (masculine detection + feminine suggestion = creation)

**Patterns Extracted:**
1. Intentional Architecture (Mentalism)
2. Fractal Component Design (Correspondence)
3. Breath-Based Functions (Rhythm)
4. Polar Feature Balance (Polarity)
5. Causal Chain Analysis (Cause/Effect)

**Next Epic Seeds:**
1. Learning system (confidence adjustment)
2. Real-time monitoring (file watching)
3. Pattern marketplace (community contributions)

**See:** `_bmad/bmm/epics/proactive-bmad/deep-retrospective/AS_ABOVE_SO_BELOW.md`

---

## Related Workflows

- `retrospective/workflow.yaml` - Standard epic retrospective
- `pattern-extraction/workflow.md` - Extract patterns from code
- `wisdom-capture/workflow.md` - Capture insights during development

---

**Workflow Version:** 1.0  
**Created:** 2026-04-08  
**Based On:** Hermes Trismegistus, The Emerald Tablet  
**Inspired By:** Proactive BMad Epic Completion

*"As above, so below; as within, so without."*
