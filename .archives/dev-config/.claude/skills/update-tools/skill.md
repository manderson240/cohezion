# update-tools

Update all Cohezion CLI tools to their latest versions.

## What This Updates

| Tool | Mechanism |
|------|-----------|
| `entire` | `https://entire.io/install.sh` |
| `sx` | `sx update` (built-in) |
| `uv` | `uv self update` |
| `gh` | GitHub releases (cli/cli) |
| `claude` | Self-managed (notifies if new version exists) |
| `pilot` | Managed by Pilot installer |

## Usage

```
/update-tools
```

Or run directly:

```bash
./scripts/update_tools.sh
```

## Scheduled Job

Runs daily at 3am via systemd timer. To check status:

```bash
systemctl --user status cohezion-tools-update.timer
systemctl --user status cohezion-tools-update.service
journalctl --user -u cohezion-tools-update.service --since today
```

## Instructions

When this skill is invoked:

1. Run `./scripts/update_tools.sh` and show the output
2. Report what was updated, what was already current, and any failures
3. If `gh` is significantly out of date (more than 5 minor versions), flag it
