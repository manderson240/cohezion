# TDD Elegant Development Skill

## Philosophy

**Red → Green → Refactor → Learn → Distill → Compound**

Every line of code should:
1. Start with a failing test (Red)
2. Pass with minimal code (Green)
3. Improve through refactoring (Refactor)
4. Teach us something (Learn)
5. Become a reusable pattern (Distill)
6. Build on previous elegance (Compound)

## The Cycle

### 1. Red (Write Failing Test)
- Think: "What behavior do I want?"
- Write test that expresses intent
- Run it - confirm it fails
- Commit: `test: add failing test for [feature]`

### 2. Green (Make It Pass)
- Think: "What's the simplest thing that works?"
- Write minimal production code
- No premature optimization
- Run tests - confirm all pass
- Commit: `feat: make [test] pass`

### 3. Refactor (Improve Without Changing Behavior)
- Think: "How can I make this clearer?"
- Look for duplication, unclear names, complexity
- Run tests - confirm still pass
- Commit: `refactor: improve [aspect] of [feature]`

### 4. Learn (Extract Insights)
- Think: "What did I discover?"
- Document patterns, anti-patterns, gotchas
- Update skill files
- Update coding standards
- Commit: `docs: distill learnings from [feature]`

### 5. Distill (Create Reusable Patterns)
- Think: "How can others benefit from this?"
- Extract helper functions, decorators, base classes
- Document usage patterns
- Create examples
- Commit: `feat: distill [pattern] from [feature]`

### 6. Compound (Build Higher)
- Think: "What can I build with this now?"
- Use new pattern in next feature
- Stack improvements
- Create compounding value
- Commit: `feat: compound [new feature] using [pattern]`

## Commit Message Conventions

- `test: [description]` - New or updated tests
- `feat: [description]` - New functionality
- `refactor: [description]` - Code improvement
- `docs: [description]` - Documentation
- `skill: [description]` - Skill/pattern extraction
- `fix: [description]` - Bug fixes

## Code Review Checklist

### Before Commit
- [ ] All tests pass
- [ ] No obvious duplication
- [ ] Names express intent
- [ ] Functions < 20 lines
- [ ] Classes < 200 lines
- [ ] No god objects
- [ ] Clear separation of concerns

### Before PR
- [ ] Test coverage > 90%
- [ ] Documentation complete
- [ ] Examples working
- [ ] Security reviewed
- [ ] Performance acceptable
- [ ] No breaking changes (or documented)

## Elegance Indicators

✅ Single responsibility  
✅ Plugin architecture  
✅ Declarative over imperative  
✅ Composition over inheritance  
✅ Immutable data structures  
✅ Pure functions where possible  
✅ Clear error messages  
✅ Self-documenting code  

## Anti-Patterns to Avoid

❌ God objects (>4 constructor params)  
❌ Deep nesting (>3 levels)  
❌ Magic numbers/strings  
❌ Copy-paste code  
❌ Premature abstraction  
❌ Side effects in unexpected places  
❌ Unclear naming  
❌ Missing error handling  

## Learning Journal

After each TDD cycle, ask:
1. What surprised me?
2. What was harder than expected?
3. What patterns emerged?
4. What would I do differently?
5. How can I make this easier next time?

Document in `.claude/skills/tdd-elegant-development/LEARNINGS.md`

---

**Status:** Active learning mode  
**Current Phase:** [Track in todo]  
**Cycle Count:** [Increment with each RGR cycle]