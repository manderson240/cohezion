---
name: skill-trigger-testing
description: Use when creating trigger test suites for skills, validating skill
  discovery accuracy, or when user mentions "trigger tests", "skill testing",
  "should trigger", or "trigger accuracy".
---

# Skill Trigger Testing

YAML-based test suite pattern for validating whether skills trigger at the
right time. Target: 90% accuracy per Anthropic spec.

## Test Suite Format

File location: `tests/skills/trigger_test_suites.yaml`

```yaml
skills:
  - name: skill-name
    description: "Brief description of the skill"
    should_trigger:
      - "Direct phrase that should load this skill"
      - "Another triggering phrase"
      - "Third trigger variant"
      - "Fourth trigger variant"
      - "Fifth trigger variant"
    should_not_trigger:
      - "Unrelated phrase that must NOT load this skill"
      - "Adjacent-domain phrase that should go elsewhere"
      - "Ambiguous phrase that belongs to a different skill"
      - "Generic request with no skill-specific signal"
      - "Similar vocabulary but different intent"
    paraphrased:
      - "Reworded version of trigger that should still match"
      - "Casual/informal way of asking for same thing"
      - "Technical jargon variant of the trigger"
```

## Coverage Targets

Per skill:
- **5** should-trigger phrases (exact user language)
- **5** should-not-trigger phrases (adjacent but wrong)
- **3** paraphrased variants (rewording of triggers)

## Writing Good Test Cases

### should_trigger
Use exact phrases a user would type. Include:
- Direct requests ("migrate my PRIME skills")
- Symptom descriptions ("skills don't have frontmatter")
- Domain keywords ("add YAML metadata to skill files")

### should_not_trigger
Target adjacent domains that share vocabulary:
- Same keywords, different intent
- Related skills that could false-match
- Generic requests without skill-specific signal

### paraphrased
Rephrase triggers with different vocabulary:
- Casual vs formal ("fix skill headers" vs "add YAML frontmatter")
- Different verb choices ("upgrade" vs "migrate" vs "convert")
- Abbreviated vs verbose

## Validation

```bash
# Verify YAML is parseable
uv run python -c "import yaml; yaml.safe_load(open('tests/skills/trigger_test_suites.yaml'))" && echo "Valid YAML"

# Count coverage
uv run python -c "
import yaml
data = yaml.safe_load(open('tests/skills/trigger_test_suites.yaml'))
for s in data['skills']:
    t = len(s.get('should_trigger', []))
    n = len(s.get('should_not_trigger', []))
    p = len(s.get('paraphrased', []))
    status = 'OK' if t >= 5 and n >= 5 and p >= 3 else 'LOW'
    print(f\"{s['name']}: trigger={t} not={n} para={p} [{status}]\")
"
```

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Triggers too generic ("help me") | Use skill-specific vocabulary |
| Not-triggers too obvious ("make coffee") | Target adjacent domains that share keywords |
| Missing paraphrased variants | Add casual, formal, and jargon rewording |
| YAML syntax errors | Always validate after editing |
