import argparse
import os
import pathlib
import re
import sys


def verify_file_exists(path: str):
    print(f"Verifying {path}...")
    if not os.path.exists(path):
        print(f"❌ Error: {path} not found.")
        return False
    print(f"✅ {path} exists.")
    return True


def verify_header_exists(path: str, header: str):
    path_obj = pathlib.Path(path)
    content = path_obj.read_text()
    if header in content:
        print(f"✅ Header '{header}' found in {path_obj.name}.")
        return True
    else:
        print(f"❌ Error: Header '{header}' not found in {path_obj.name}.")
        return False


def verify_no_placeholders(path: str):
    path_obj = pathlib.Path(path)
    content = path_obj.read_text()

    # Define actual placeholders that shouldn't be there
    placeholders = ["${", "[TBD]", "TODO", "FIXME"]

    # Exceptions that are valid
    exceptions = ["${skill}"]

    found = []
    for p in placeholders:
        if p in content:
            # Check if it's an exception
            is_exception = any(ex in content for ex in exceptions if p in ex)
            if p == "${" and content.count(p) == content.count("${skill}"):
                continue
            found.append(p)

    if found:
        print(f"❌ Error: Placeholders {found} found in {path_obj.name}.")
        return False
    return True


def verify_12d_vectors(path: str):
    print(f"Auditing 12D vectors in {path}...")
    content = pathlib.Path(path).read_text()
    # Pattern: 12D state vectors (3 Spatial + 1 Time + 8 Brane)
    pattern = r"12D state vectors \(3 Spatial \+ 1 Time \+ 8 Brane\)"
    if re.search(pattern, content):
        print(f"✅ 12D Vector signature validated in {os.path.basename(path)}.")
        return True
    else:
        print(f"❌ Error: Malformed or missing 12D vector signature in {os.path.basename(path)}.")
        return False


def verify_links(path: str):
    print(f"Checking link integrity in {path}...")
    content = pathlib.Path(path).read_text()
    # Find all file:/// links
    links = re.findall(r"file://(/[^\s\)\>]+)", content)
    dead_links = []
    for link in links:
        # Remote line fragments like #L123
        clean_link = link.split("#")[0]
        if not os.path.exists(clean_link):
            dead_links.append(link)

    if dead_links:
        print(f"❌ Error: Found {len(dead_links)} dead links: {dead_links}")
        return False
    return True


def verify_adversarial(path: str):
    print(f"Running adversarial stress test on {path}...")
    content = pathlib.Path(path).read_text()

    # 1. Glitch detection (Zero-width spaces/Unicode tricks)
    glitches = ["\u200b", "\u200c", "\u200d", "\ufeff"]
    for g in glitches:
        if g in content:
            print(
                f"❌ Error: Malicious 'glitch' character detected (Unicode {hex(ord(g))}) in {os.path.basename(path)}."
            )
            return False

    # 2. Protocol hijacking (javascript: or data: in links)
    if re.search(r"\[.*\]\((javascript:|data:).*\)", content):
        print(f"❌ Error: Malicious protocol (javascript:/data:) detected in {os.path.basename(path)}.")
        return False

    print(f"✅ Adversarial audit PASSED for {os.path.basename(path)}.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Cohezion Context Validation Suite")
    parser.add_argument("--adversarial", action="store_true", help="Run intense adversarial audits")
    args = parser.parse_args()

    print("--- Cohezion Context Validation Suite (Hardened) ---")

    critical_files = [
        "GEMINI.md",
        ".agent/CONSTITUTION.md",
        ".agent/CODING_STANDARDS.md",
        ".agent/EVOLUTION_PROTOCOL.md",
        ".agent/CAPABILITY_MAP.md",
        "src/cohezion/knowledge_graph/MISSION_JOURNAL.md",
        "src/cohezion/knowledge_graph/KEY_LEARNINGS.md",
    ]

    all_passed = True

    # 1. Existence Check
    for f in critical_files:
        if not verify_file_exists(f):
            all_passed = False

    # 2. Structural & Content Integrity
    if all_passed:
        # Custom header checks
        verify_header_exists("GEMINI.md", "# GEMINI.md - Cohezion Orchestration Layer")
        verify_header_exists(".agent/CONSTITUTION.md", "## 3. The 0.5 Coherence Rule (HIHO Stability)")
        verify_header_exists(".agent/EVOLUTION_PROTOCOL.md", "## 1. Continuous Experience Mining")

        # 3. Vector & Link Audits
        for f in [
            ".agent/CAPABILITY_MAP.md",
            "src/cohezion/knowledge_graph/KEY_LEARNINGS.md",
            "GEMINI.md",
        ]:
            if not verify_12d_vectors(f):
                all_passed = False
            if not verify_links(f):
                all_passed = False

        # 4. Mandatory Placeholder & Adversarial Checks
        for f in critical_files:
            if "CAPABILITY_MAP" not in f:
                if not verify_no_placeholders(f):
                    all_passed = False

            if args.adversarial:
                if not verify_adversarial(f):
                    all_passed = False

    if all_passed:
        print("\n✨ All context validations PASSED.")
        sys.exit(0)
    else:
        print("\n❌ Context validation FAILED.")
        sys.exit(1)


if __name__ == "__main__":
    main()
