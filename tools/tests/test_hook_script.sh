#!/usr/bin/env bash
# Smoke tests for vault-link-suggest.sh
# Usage: bash tools/tests/test_hook_script.sh
# Exits 0 on all pass, 1 on any failure.

VAULT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOOK="$VAULT_ROOT/.claude/hooks/vault-link-suggest.sh"
COOLDOWN_FILE="/tmp/vault-link-suggest-$(id -u).last"
PASS=0
FAIL=0

_assert_exit() {
    local label="$1"
    local expected="$2"
    local actual="$3"
    if [[ "$actual" == "$expected" ]]; then
        echo "  PASS: $label"
        (( PASS++ ))
    else
        echo "  FAIL: $label (expected exit $expected, got $actual)"
        (( FAIL++ ))
    fi
}

_assert_output_contains() {
    local label="$1"
    local needle="$2"
    local haystack="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo "  PASS: $label"
        (( PASS++ ))
    else
        echo "  FAIL: $label (expected '$needle' in output)"
        (( FAIL++ ))
    fi
}

_assert_output_empty() {
    local label="$1"
    local output="$2"
    if [[ -z "$output" ]]; then
        echo "  PASS: $label"
        (( PASS++ ))
    else
        echo "  FAIL: $label (expected empty output, got: $output)"
        (( FAIL++ ))
    fi
}

echo "Running hook smoke tests..."
echo ""

# Clear cooldown before tests
rm -f "$COOLDOWN_FILE"

# Test 1: Non-.md file → silent exit 0
echo "Test 1: Non-.md file is ignored"
input='{"tool_input":{"file_path":"/some/path/file.py"}}'
out=$(echo "$input" | bash "$HOOK" 2>/dev/null)
_assert_exit "exits 0 for .py file" 0 $?
_assert_output_empty "no output for .py file" "$out"

# Reset cooldown
rm -f "$COOLDOWN_FILE"

# Test 2: Missing file_path → silent exit 0
echo "Test 2: Missing file_path is ignored"
input='{"tool_input":{}}'
out=$(echo "$input" | bash "$HOOK" 2>/dev/null)
_assert_exit "exits 0 for missing file_path" 0 $?
_assert_output_empty "no output for missing file_path" "$out"

# Reset cooldown
rm -f "$COOLDOWN_FILE"

# Test 3: Malformed JSON → silent exit 0 (jq fails gracefully)
echo "Test 3: Malformed JSON is handled gracefully"
out=$(echo "not json at all" | bash "$HOOK" 2>/dev/null)
_assert_exit "exits 0 for malformed JSON" 0 $?

# Reset cooldown
rm -f "$COOLDOWN_FILE"

# Test 4: Valid .md file path → exits 0 (vault_linker suggest may output something)
echo "Test 4: Valid .md file path exits 0"
md_file="$VAULT_ROOT/concepts/cs249r/workflow.md"
if [[ -f "$md_file" ]]; then
    input="{\"tool_input\":{\"file_path\":\"$md_file\"}}"
    out=$(echo "$input" | bash "$HOOK" 2>/dev/null)
    _assert_exit "exits 0 for valid .md file" 0 $?
else
    echo "  SKIP: Test 4 (vault file not found: $md_file)"
fi

# Test 5: Cooldown prevents second run within 30s
echo "Test 5: Cooldown prevents redundant runs"
rm -f "$COOLDOWN_FILE"

md_file="$VAULT_ROOT/concepts/cs249r/workflow.md"
input="{\"tool_input\":{\"file_path\":\"$md_file\"}}"

# First run — updates cooldown
echo "$input" | bash "$HOOK" > /dev/null 2>&1
first_exit=$?

# Second run immediately — should be silenced by cooldown
out=$(echo "$input" | bash "$HOOK" 2>/dev/null)
second_exit=$?

_assert_exit "second run exits 0" 0 $second_exit
_assert_output_empty "second run has no output (cooldown)" "$out"

echo ""
echo "Results: $PASS passed, $FAIL failed"
[[ "$FAIL" -eq 0 ]] && exit 0 || exit 1
