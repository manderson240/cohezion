#!/bin/bash
# Verify cloud tunnel connectivity
# Run on CLOUD MACHINE

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

test_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}[✓]${NC} $2"
        return 0
    else
        echo -e "${RED}[✗]${NC} $2"
        return 1
    fi
}

test_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

test_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

echo "Vault Tunnel Verification"
echo "========================="
echo ""

CHECKS_PASSED=0
CHECKS_FAILED=0

# Check 1: SSH key exists
echo "Checking SSH key..."
if [ -f ~/.ssh/cohezion/id_cloud_claude ]; then
    test_result 0 "SSH private key found"
    ((CHECKS_PASSED++))

    # Check permissions
    PERMS=$(stat -c %a ~/.ssh/cohezion/id_cloud_claude 2>/dev/null || stat -f %OLp ~/.ssh/cohezion/id_cloud_claude 2>/dev/null)
    if [ "$PERMS" = "600" ] || [ "$PERMS" = "0600" ]; then
        test_result 0 "SSH key permissions correct (600)"
        ((CHECKS_PASSED++))
    else
        test_result 1 "SSH key permissions incorrect (should be 600, got $PERMS)"
        ((CHECKS_FAILED++))
    fi
else
    test_result 1 "SSH private key not found at ~/.ssh/cohezion/id_cloud_claude"
    ((CHECKS_FAILED++))
fi

# Check 2: SSH config
echo ""
echo "Checking SSH config..."
if grep -q "Host vault-tunnel" ~/.ssh/config 2>/dev/null; then
    test_result 0 "SSH config has vault-tunnel entry"
    ((CHECKS_PASSED++))
else
    test_result 1 "SSH config missing vault-tunnel entry"
    test_warn "Create entry in ~/.ssh/config - see CLOUD_CLAUDE_ACCESS.md"
    ((CHECKS_FAILED++))
fi

# Check 3: Local port availability
echo ""
echo "Checking local port 8360..."
if nc -z 127.0.0.1 8360 2>/dev/null; then
    test_result 0 "Port 8360 is open (tunnel might already be running)"
    ((CHECKS_PASSED++))
else
    test_warn "Port 8360 is not open (tunnel not running - will test connection)"
    ((CHECKS_FAILED++))
fi

# Check 4: Attempt connection
echo ""
echo "Attempting SSH connection..."

# Try to establish tunnel
if ssh -N -f vault-tunnel 2>/dev/null; then
    test_result 0 "SSH tunnel established"
    ((CHECKS_PASSED++))
    TUNNEL_RUNNING=1

    # Give it a moment to fully establish
    sleep 2
else
    test_result 1 "SSH tunnel failed to establish"
    test_warn "Check: SSH host is reachable, SSH key has correct permissions, remote host is configured"
    ((CHECKS_FAILED++))
    TUNNEL_RUNNING=0
fi

# Check 5: Port is now open
echo ""
echo "Verifying tunnel port is open..."
if nc -z 127.0.0.1 8360 2>/dev/null; then
    test_result 0 "Port 8360 is now accessible"
    ((CHECKS_PASSED++))
else
    test_result 1 "Port 8360 is not accessible"
    ((CHECKS_FAILED++))
fi

# Check 6: Health check endpoint
echo ""
echo "Testing MCP server health..."
if curl -s -m 5 "http://127.0.0.1:8360/health" > /dev/null 2>&1; then
    test_result 0 "MCP server health endpoint responsive"
    ((CHECKS_PASSED++))
else
    test_result 1 "MCP server health endpoint not responding"
    test_warn "Check: MCP server is running on local machine, tunnel is properly forwarded"
    ((CHECKS_FAILED++))
fi

# Check 7: MCP tools availability
echo ""
echo "Testing MCP tool discovery..."
RESPONSE=$(curl -s -m 5 -H "Authorization: Bearer a712027605bbd33068da5462bbcc18d90f844df23f948f124908fa726d678263" \
    "http://127.0.0.1:8360/mcp" 2>/dev/null)

if [ -n "$RESPONSE" ] && [ "$RESPONSE" != "Unauthorized" ]; then
    test_result 0 "MCP server is responding to authenticated requests"
    ((CHECKS_PASSED++))

    # Check for vault tools
    if echo "$RESPONSE" | grep -q "vault" 2>/dev/null; then
        test_result 0 "Vault tools are available"
        ((CHECKS_PASSED++))
    else
        test_warn "Vault tools not detected in response (may still work, check with Claude Code)"
        ((CHECKS_FAILED++))
    fi
else
    test_result 1 "MCP server not responding or auth failed"
    test_warn "Check: Bearer token in ~/.claude/mcp.json matches server .env"
    ((CHECKS_FAILED++))
fi

# Check 8: Claude Code MCP config
echo ""
echo "Checking Claude Code MCP configuration..."
if [ -f ~/.claude/mcp.json ]; then
    test_result 0 "Claude Code MCP config exists"
    ((CHECKS_PASSED++))

    if grep -q "cohezion-vault" ~/.claude/mcp.json; then
        test_result 0 "cohezion-vault MCP server configured"
        ((CHECKS_PASSED++))
    else
        test_result 1 "cohezion-vault not configured in mcp.json"
        test_warn "Add to ~/.claude/mcp.json - see CLOUD_CLAUDE_ACCESS.md"
        ((CHECKS_FAILED++))
    fi
else
    test_result 1 "Claude Code MCP config not found at ~/.claude/mcp.json"
    test_warn "Create config file - see CLOUD_CLAUDE_ACCESS.md"
    ((CHECKS_FAILED++))
fi

# Summary
echo ""
echo "========================="
echo "Summary"
echo "========================="
echo -e "Passed: ${GREEN}$CHECKS_PASSED${NC}"
echo -e "Failed: ${RED}$CHECKS_FAILED${NC}"
echo ""

if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed!${NC}"
    echo ""
    echo "Your cloud Claude can now access the vault."
    echo "Test with: Use vault_read to read decisions/..."
    exit 0
else
    echo -e "${RED}✗ Some checks failed${NC}"
    echo ""
    echo "Review failed items and see CLOUD_CLAUDE_ACCESS.md"
    echo "Run: ssh -v vault-tunnel (for SSH debugging)"
    exit 1
fi
