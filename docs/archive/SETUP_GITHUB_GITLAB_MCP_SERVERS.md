# Setup GitHub & GitLab MCP Servers

**Purpose**: Enable secure, credential-managed API interactions with GitHub and GitLab through MCP instead of manual token handling.

**Status**: Ready to implement

---

## Why MCP Servers?

✅ **Secure**: Credentials managed by MCP, not exposed in commands
✅ **Integrated**: Works natively with Claude Code
✅ **Convenient**: No manual token passing
✅ **Standard**: MCP is the official protocol for tool integration

---

## Option 1: Use Anthropic's Official MCP GitHub Server

### Installation

```bash
# Install the GitHub MCP server globally
npm install -g @anthropic-sdk/github-mcp-server

# Or via pip if available
uv pip install github-mcp-server
```

### Configuration

Add to `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": [
        "-y",
        "@anthropic-sdk/github-mcp-server"
      ],
      "env": {
        "GITHUB_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

### Available Tools

Once configured, you'll have access to:
- `github_search_issues`
- `github_create_issue`
- `github_update_issue`
- `github_list_pull_requests`
- `github_create_pull_request`
- `github_create_review`
- `github_push_files` (for commits)

---

## Option 2: Use Open-Source MCP GitHub Server

### Installation

```bash
# Clone the repository
git clone https://github.com/extension-org/mcp-github.git
cd mcp-github

# Install dependencies
npm install
# or
uv pip install -e .
```

### Configuration

Add to `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "github": {
      "command": "python3",
      "args": [
        "mcp_github/__main__.py"
      ],
      "env": {
        "GITHUB_TOKEN": "YOUR_TOKEN_HERE"
      }
    }
  }
}
```

---

## Option 3: Use GitLab MCP Server

### Installation

```bash
# Clone the GitLab MCP server
git clone https://github.com/extension-org/mcp-gitlab.git
cd mcp-gitlab

npm install
# or
uv pip install -e .
```

### Configuration

Add to `config/mcp_config.json`:

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "python3",
      "args": [
        "mcp_gitlab/__main__.py"
      ],
      "env": {
        "GITLAB_TOKEN": "YOUR_TOKEN_HERE",
        "GITLAB_URL": "http://localhost:8929"
      }
    }
  }
}
```

---

## Recommended: Combined Configuration

Update `config/mcp_config.json` to include both:

```json
{
  "mcpServers": {
    "surrealmcp": {
      "command": "npx",
      "args": ["-y", "@surrealdb/mcp-server"],
      "env": {
        "SURREALDB_URL": "ws://localhost:8000/rpc",
        "SURREALDB_NS": "cohezion",
        "SURREALDB_DB": "core"
      }
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic-sdk/github-mcp-server"],
      "env": {
        "GITHUB_TOKEN": "YOUR_GITHUB_TOKEN"
      }
    },
    "gitlab": {
      "command": "npx",
      "args": ["-y", "@extension-org/mcp-gitlab-server"],
      "env": {
        "GITLAB_TOKEN": "YOUR_GITLAB_TOKEN",
        "GITLAB_URL": "http://localhost:8929"
      }
    }
  }
}
```

---

## Token Management (Secure)

**Never commit tokens to git!** Use one of these approaches:

### Approach 1: Environment Variables (Recommended)

```bash
# Add to ~/.bashrc or ~/.zshrc
export GITHUB_TOKEN="ghp_xxxxxxxxxxxxxxxxxxxx"
export GITLAB_TOKEN="glpat_xxxxxxxxxxxxxxxxxxxx"

# Then reload shell
source ~/.bashrc
```

### Approach 2: .env File (Local Only)

Create `.env.local` (in .gitignore):

```
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
GITLAB_TOKEN=glpat_xxxxxxxxxxxxxxxxxxxx
```

Then load before using MCP:
```bash
set -a
source .env.local
set +a
```

### Approach 3: System Keyring

Store tokens in your system's credential manager:

```bash
# macOS
security add-generic-password -a github -s GITHUB_TOKEN -w "YOUR_TOKEN"

# Linux
pass insert github/token
```

Then update MCP config to read from keyring.

---

## Usage Examples

### Once Configured, You Can:

```python
# In Claude Code, use the MCP tools directly:
from mcp_client import MCPClient

github = MCPClient("github")

# Create a pull request
pr = github.create_pull_request(
    owner="manderson240",
    repo="cohezion",
    title="docs: Optimize CLAUDE.md for token efficiency",
    body="...",
    head="session-55-test-fixes-main",
    base="develop",
)

# List recent PRs
prs = github.list_pull_requests(owner="manderson240", repo="cohezion", state="open")
```

Or via Claude Code directly (once MCP servers are running):

```bash
# The MCP tools become available to Claude
# You can say: "Use GitHub to create a PR from session-55-test-fixes-main to develop"
```

---

## Next Steps

### If You Want to Use MCP Servers:

1. **Choose a server** (Option 1, 2, or 3 above)
2. **Install it**
3. **Add token to environment** (don't commit to git!)
4. **Update config/mcp_config.json**
5. **Restart Claude Code** to load new MCP servers
6. **Then**: I can create PRs/push to GitHub/GitLab directly

### If You Want to Continue with Secure Token Method:

Use the `/tmp/secure_push.sh` script I created earlier:
```bash
bash /tmp/secure_push.sh
# Paste token when prompted (won't echo)
```

---

## Verification

After setting up MCP servers:

```bash
# List available MCP servers
ls config/mcp_config.json

# Test GitHub connection
# (Once Claude restarts with new config)
# You'll see GitHub tools available in Claude Code
```

---

## Recommendation

**For this session**:
- Use the secure token script (`/tmp/secure_push.sh`) to push to GitHub
- Complete the CLAUDE.md deployment

**For future sessions**:
- Set up GitHub/GitLab MCP servers (this guide)
- All future PRs/commits handled via MCP
- No manual token passing needed

---

## Resources

- [Anthropic MCP GitHub Server](https://github.com/anthropic-sdk/github-mcp-server)
- [MCP Protocol Spec](https://spec.modelcontextprotocol.io/)
- [GitHub API](https://docs.github.com/en/rest)
- [GitLab API](https://docs.gitlab.com/ee/api/)

---

**Choose your path**:
1. ✅ **Now**: Use secure token script to finish this session's deployment
2. 🔄 **Later**: Set up MCP servers for future sessions
