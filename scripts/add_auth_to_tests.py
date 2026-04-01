#!/usr/bin/env python3
"""Add authentication headers to A2A test methods."""

import re
from pathlib import Path


TEST_FILE = Path(__file__).parent.parent / "tests/api/test_a2a_endpoints.py"

def add_auth_to_tests():
    """Add mock_auth_token fixture and headers to test methods."""
    content = TEST_FILE.read_text()

    # Pattern 1: Add mock_auth_token to function signatures
    # Find: def test_xxx(self, client, mock_compound_executor)
    # Replace: def test_xxx(self, client, mock_auth_token, mock_compound_executor)

    pattern1 = r'(def test_\w+\(self, client)(, mock_compound_executor\))'
    replacement1 = r'\1, mock_auth_token\2'
    content = re.sub(pattern1, replacement1, content)

    # Pattern 2: Add headers to client.post() calls without headers
    # Find: client.post("/tasks/send", json={
    # Replace: client.post("/tasks/send", json={..., headers={"X-Cohezion-Key": mock_auth_token})

    # This is complex, so let's do it manually in targeted edits
    lines = content.split('\n')
    modified_lines = []
    i = 0

    while i < len(lines):
        line = lines[i]

        # Check if this is a client.post or client.get call WITHOUT headers
        if ('client.post("/tasks' in line or 'client.get("/tasks' in line) and 'headers=' not in line:
            # Look ahead for closing paren
            call_lines = [line]
            j = i + 1
            while j < len(lines) and ')' not in lines[j]:
                call_lines.append(lines[j])
                j += 1
            if j < len(lines):
                call_lines.append(lines[j])

            # Check if headers already present
            full_call = '\n'.join(call_lines)
            if 'headers=' not in full_call:
                # Find the closing paren and add headers before it
                last_line_idx = len(call_lines) - 1
                last_line = call_lines[last_line_idx]

                # Find position of closing paren
                if ')' in last_line:
                    # Insert headers before closing paren
                    indent = len(last_line) - len(last_line.lstrip())

                    # Determine if this is a simple or complex call
                    if 'json=' in full_call:
                        # Complex call with json parameter
                        # Add comma after json and insert headers
                        call_lines.insert(last_line_idx, f'{" " * indent}headers={{"X-Cohezion-Key": mock_auth_token}}')

                    # Join and add
                    modified_lines.extend(call_lines)
                    i = j + 1
                    continue

        modified_lines.append(line)
        i += 1

    # Write back
    TEST_FILE.write_text('\n'.join(modified_lines))
    print(f"Updated {TEST_FILE}")

if __name__ == "__main__":
    add_auth_to_tests()
