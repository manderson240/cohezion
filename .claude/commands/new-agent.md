---
description: Scaffold a new Claude Code agent file with valid frontmatter
arguments:
  - name: name
    description: Agent name (lowercase kebab-case, e.g. "my-agent")
    required: true
  - name: description
    description: Agent description (min 10 characters)
    required: true
  - name: tools
    description: Comma-separated tool list (e.g. "Read,Glob,Bash")
    required: false
  - name: disallowed-tools
    description: Comma-separated disallowed tool list
    required: false
  - name: model
    description: Model name (e.g. "sonnet", "opus", "haiku")
    required: false
---

Create a new Claude Code agent file at `.claude/agents/$ARGUMENTS.name.md`.

## Steps

1. **Generate frontmatter** using the validation schema:

```python
from cohezion.validation.agent_schema import generate_agent_frontmatter

frontmatter = generate_agent_frontmatter(
    name="$ARGUMENTS.name",
    description="$ARGUMENTS.description",
    tools=$ARGUMENTS.tools.split(",") if "$ARGUMENTS.tools" else None,
    disallowed_tools=$ARGUMENTS.disallowed-tools.split(",") if "$ARGUMENTS.disallowed-tools" else None,
    model="$ARGUMENTS.model" if "$ARGUMENTS.model" else None,
)
```

2. **Write the agent file** at `.claude/agents/$ARGUMENTS.name.md` with:
   - The generated frontmatter
   - A markdown template body with sections: Role, Workflow, Constraints

3. **Validate** the written file:

```python
from cohezion.validation.agent_schema import validate_agent_file
result = validate_agent_file(".claude/agents/$ARGUMENTS.name.md")
print(f"Agent '{result.name}' created and validated successfully")
```

## Template Body

After the frontmatter, include this template:

```markdown
# [Agent Name] Agent

[One-sentence description of what this agent does.]

## Role

[Describe the agent's primary responsibility and scope.]

## Workflow

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Constraints

- [Constraint 1]
- [Constraint 2]
```
