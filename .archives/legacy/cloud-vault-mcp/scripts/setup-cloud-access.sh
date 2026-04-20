#!/bin/bash
# Setup Cloud Claude Access to Vault
# Run on LOCAL machine (where vault is hosted)

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

echo "Cohezion Vault - Cloud Claude Access Setup"
echo "==========================================="
echo ""

# Check prerequisites
log_info "Checking prerequisites..."

if ! command -v ssh-keygen &> /dev/null; then
    log_error "ssh-keygen not found. Install OpenSSH."
    exit 1
fi

if ! command -v git &> /dev/null; then
    log_error "git not found. Install git."
    exit 1
fi

if [ ! -d /home/mike-anderson/vaults/cohezion-vault ]; then
    log_error "Vault directory not found at /home/mike-anderson/vaults/cohezion-vault"
    exit 1
fi

# Step 1: Generate SSH Key
echo ""
log_info "Step 1: Generating SSH key for cloud access..."

SSH_KEY_PATH="$HOME/.ssh/id_cloud_claude"

if [ -f "$SSH_KEY_PATH" ]; then
    log_warn "SSH key already exists at $SSH_KEY_PATH"
    read -p "Overwrite? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Keeping existing SSH key"
    else
        rm "$SSH_KEY_PATH" "$SSH_KEY_PATH.pub"
        ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "cloud-claude-vault-access"
        log_info "SSH key generated"
    fi
else
    ssh-keygen -t ed25519 -f "$SSH_KEY_PATH" -N "" -C "cloud-claude-vault-access"
    log_info "SSH key generated"
fi

# Step 2: Add to authorized_keys with restrictions
echo ""
log_info "Step 2: Adding public key to authorized_keys..."

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

# Read public key
PUBLIC_KEY=$(cat "$SSH_KEY_PATH.pub")

# Check if already present
if grep -q "cloud-claude-vault-access" "$HOME/.ssh/authorized_keys" 2>/dev/null; then
    log_warn "Public key already in authorized_keys"
else
    # Add with restrictions
    echo "no-pty,no-X11-forwarding,no-agent-forwarding,permitopen=\"127.0.0.1:8360\" $PUBLIC_KEY" >> "$HOME/.ssh/authorized_keys"
    chmod 600 "$HOME/.ssh/authorized_keys"
    log_info "Public key added with restrictions"
fi

# Step 3: Configure git remote for vault
echo ""
log_info "Step 3: Configuring vault git backup..."

read -p "GitHub repository URL (git@github.com:USER/vault-backup.git) [skip to use manual]: " GITHUB_URL

if [ -n "$GITHUB_URL" ]; then
    cd /home/mike-anderson/vaults/cohezion-vault

    # Check if remote already exists
    if git remote get-url origin &> /dev/null; then
        log_warn "Git remote 'origin' already configured"
        current_remote=$(git remote get-url origin)
        echo "Current: $current_remote"
        read -p "Overwrite? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git remote remove origin
            git remote add origin "$GITHUB_URL"
            log_info "Git remote updated"
        fi
    else
        git remote add origin "$GITHUB_URL"
        log_info "Git remote added"
    fi

    # Try initial push
    if git branch | grep -q "main"; then
        read -p "Push to GitHub now? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            git push -u origin main || log_warn "Push failed - check SSH key access to GitHub"
            log_info "Initial push complete"
        fi
    fi
fi

# Step 4: Update .env for MCP server
echo ""
log_info "Step 4: Updating MCP server configuration..."

ENV_FILE="/home/mike-anderson/dev/cohezion/cloud-vault-mcp/.env"

if grep -q "GIT_REMOTE_URL=" "$ENV_FILE"; then
    if [ -n "$GITHUB_URL" ]; then
        sed -i "s|GIT_REMOTE_URL=.*|GIT_REMOTE_URL=$GITHUB_URL|" "$ENV_FILE"
        log_info "GIT_REMOTE_URL updated in .env"
    fi
fi

# Step 5: Display summary
echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
log_info "SSH Key Setup:"
echo "  Private key: $SSH_KEY_PATH (keep secret, transfer securely to cloud machine)"
echo "  Public key:  $SSH_KEY_PATH.pub"
echo "  Permissions: 600 (read/write owner only)"
echo ""
log_info "SSH Config (for cloud machine):"
echo "  Host: $(hostname -I | awk '{print $1}')"
echo "  User: $USER"
echo "  Port: 22"
echo ""
log_info "Local Verification:"
ssh -i "$SSH_KEY_PATH" localhost "echo 'SSH connection works!'" && log_info "Connection test passed" || log_error "Connection test failed"
echo ""

# Step 6: Display setup instructions for cloud machine
echo "=========================================="
echo "Next Steps (on CLOUD MACHINE):"
echo "=========================================="
cat << 'EOF'

1. Create SSH config (~/.ssh/config):

Host vault-tunnel
    HostName <LOCAL_MACHINE_IP>
    User <LOCAL_USERNAME>
    IdentityFile ~/.ssh/cohezion/id_cloud_claude
    StrictHostKeyChecking accept-new
    LocalForward 127.0.0.1:8360 127.0.0.1:8360
    ServerAliveInterval 60
    ServerAliveCountMax 10
    ExitOnForwardFailure yes

2. Copy private key securely:
   - Transfer id_cloud_claude to ~/.ssh/cohezion/
   - chmod 600 ~/.ssh/cohezion/id_cloud_claude

3. Test tunnel:
   ssh -N -f vault-tunnel
   curl http://127.0.0.1:8360/health

4. Update ~/.claude/mcp.json:
   {
     "mcpServers": {
       "cohezion-vault": {
         "type": "http",
         "url": "http://127.0.0.1:8360/mcp",
         "headers": {
           "Authorization": "Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263"
         }
       }
     }
   }

5. Set up health monitoring:
   chmod +x ~/.local/bin/vault-tunnel-health.sh
   tmux new-session -d -s vault-health ~/.local/bin/vault-tunnel-health.sh

See CLOUD_CLAUDE_ACCESS.md for detailed instructions.

EOF

echo ""
log_info "Setup scripts available in /scripts:"
echo "  - setup-cloud-access.sh (this script)"
echo "  - verify-tunnel.sh (test connection)"
echo "  - rotate-token.sh (security maintenance)"
echo ""
