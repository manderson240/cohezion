# Session Context

## User Prompts

### Prompt 1

Implement the following plan:

# /learn — Skill to Create: Cohezion Vault Brain Architecture Directory Map

**Status:** Ready to create once plan mode exits

**Skill location:** `.claude/skills/cohezion-vault-brain-architecture/SKILL.md`

**Trigger conditions:**
- Writing files to `~/vaults/cohezion-vault/`
- Any session that references `patterns/`, `concepts/`, or `decisions/` in the vault
- Error: `ls: cannot access '/home/mike-anderson/vaults/cohezion-vault/patterns/': No such file or dire...

### Prompt 2

Provide a code review for the given pull request.

To do this, follow these steps precisely:

1. Use a Haiku agent to check if the pull request (a) is closed, (b) is a draft, (c) does not need a code review (eg. because it is an automated pull request, or is very simple and obviously ok), or (d) already has a code review from you from earlier. If so, do not proceed.
2. Use another Haiku agent to give you a list of file paths to (but not the contents of) any relevant CLAUDE.md files from the c...

