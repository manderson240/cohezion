# /vault - Manage Team Vault

Share and install rules, commands, and skills across your team using `sx` and a private Git repository.

## Quick Reference

```bash
# Check status
sx config                              # Show config and vault URL
sx vault list                          # List all vault assets

# Pull team assets
sx install --repair --target .         # Install to current project

# Push assets
REPO=$(git remote get-url origin)

# Push a skill
sx add .claude/commands/my-skill.md --yes --type skill --name "my-skill" --scope-repo $REPO

# Push a rule
sx add .claude/rules/my-rule.md --yes --type rule --name "my-rule" --scope-repo $REPO

# Push globally (all repos)
sx add .claude/rules/my-rule.md --yes --type rule --name "my-rule" --scope-global

# Browse
sx vault show <asset-name>             # Show asset details
```

## Asset Types

| Type | Flag | Source Path |
|------|------|-------------|
| skill | `--type skill` | `.claude/commands/<name>.md` |
| rule | `--type rule` | `.claude/rules/<name>.md` |
| command | `--type command` | `.claude/commands/<name>.md` |

## When to Use

| Situation | Action |
|-----------|--------|
| Created new rule or skill | Push with `sx add` |
| Onboarding new team member | `sx install --repair --target .` |
| Rule changed and needs team-wide update | Push with `sx add` (auto-increments version) |
| Want to see what's shared | `sx vault list` |

## Scoping

| Scope | Use When |
|-------|----------|
| `--scope-repo` (recommended) | Assets belong to this project |
| `--scope-global` | Personal tools needed in all repos |

## Tips

- Do NOT use `--no-install` — it skips the lockfile update
- Always use `--name` to control the asset name in the vault
- Use `sx install --repair --target .` to install, not just `sx install`
- Add `.cursor/` to `.gitignore` — sx installs to Cursor too
