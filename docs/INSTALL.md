# Cohezion Installation Guide

## Quick Install

```bash
# 1. Clone repository
git clone https://github.com/manderson240/cohezion.git
cd cohezion

# 2. Run automated setup
./activate.sh full

# 3. Configure GitHub token
export GITHUB_TOKEN=your_token_here
# Or add to .env file
echo "GITHUB_TOKEN=your_token_here" > .env

# 4. Enable autonomy (optional)
./setup-automation.sh
```

## Requirements

### System Requirements
- Python 3.11+
- Git 2.30+
- GitHub CLI (gh)
- Docker (for MCP server)

### Python Dependencies
```bash
pip install -r requirements.txt
```

Or with uv:
```bash
uv pip install -e ".[dev]"
```

## Configuration

### GitHub Authentication

```bash
# Login to GitHub CLI
gh auth login

# Verify access
gh auth status

# For full security features, refresh with admin scope
gh auth refresh -h github.com -s admin:repo_hook
```

### Environment Variables

Create `.env` file:

```bash
# Required
GITHUB_TOKEN=ghp_your_token_here

# Optional - Notifications
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
NOTIFICATION_EMAIL=you@example.com

# Optional - Autonomy Level
AUTONOMY_LEVEL=3
```

### Autonomy Configuration

Create `.autonomy/config.yaml`:

```yaml
autonomy_level: 3
notifications:
  channel: slack
  webhook: ${SLACK_WEBHOOK_URL}
permissions:
  write_code: true
  commit_directly: true
  version_bumps: auto
limits:
  max_lines_per_commit: 500
  auto_rollback_on_failure: true
```

## Verification

### Test Installation

```bash
# Test MCP connection
python scripts/security/test_mcp_connection.py

# Run security check
./cohezion.py security

# Check status
./cohezion.py status

# Launch dashboard
./cohezion.py dashboard
```

### Expected Output

```
✅ GitHub CLI authenticated
✅ MCP configuration valid
✅ API access working
✅ Security API accessible
✅ Docker available
✅ MCP server image available

🎉 All tests passed! System is ready.
```

## Troubleshooting

### Issue: GitHub CLI not authenticated

**Solution**:
```bash
gh auth login
# Follow browser prompts
```

### Issue: Permission denied on state files

**Solution**:
```bash
chmod 600 .env
chmod 700 orchestrator/state
```

### Issue: Tests fail with import errors

**Solution**:
```bash
# Install in editable mode
pip install -e .

# Or set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue: Docker not available

**Solution**:
```bash
# Install Docker
sudo apt-get install docker.io

# Or use without MCP (limited features)
# Edit mcp_servers.json to use CLI instead
```

### Issue: State manager errors

**Solution**:
```bash
# Initialize state directory
mkdir -p orchestrator/state
chmod 700 orchestrator/state

# Clear corrupted state (if needed)
rm -rf orchestrator/state/*
```

## Post-Installation

### 1. Enable Autonomy (Recommended)

```bash
./setup-automation.sh
```

This sets up:
- Daily security checks (08:00 UTC)
- Weekly reports (Monday 09:00 UTC)
- Documentation health monitoring

### 2. Test Autonomy

```bash
# Simple task - should auto-commit
./cohezion.py "Fix typo in README"

# Check if committed
git log -1
```

### 3. Configure Notifications

Slack:
```bash
export SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
echo "SLACK_WEBHOOK_URL=$SLACK_WEBHOOK_URL" >> .env
```

Email:
```bash
export NOTIFICATION_EMAIL=you@example.com
echo "NOTIFICATION_EMAIL=$NOTIFICATION_EMAIL" >> .env
```

## Directory Structure After Install

```
cohezion/
├── .autonomy/
│   ├── config.yaml
│   └── audit/
├── orchestrator/
│   ├── state/           # System state
│   └── events/          # Event log
├── reports/             # Generated reports
├── logs/                # System logs
├── .env                 # Environment variables
└── ...
```

## Updates

### Update System

```bash
# Pull latest
git pull origin main

# Run update script
./activate.sh full
```

### Check Version

```bash
./cohezion.py --version
```

## Uninstall

```bash
# Remove automation
crontab -e
# Remove Cohezion entries

# Remove files
rm -rf .autonomy/
rm -rf orchestrator/state/
```

## Support

- **Documentation**: `docs/`
- **CLI Help**: `./cohezion.py --help`
- **Status**: `./cohezion.py status`
- **Issues**: GitHub Issues

---

**Installation Complete!** Run `./activate.sh quick` to verify.
