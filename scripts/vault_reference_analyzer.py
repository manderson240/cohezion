#!/usr/bin/env python3
"""
Vault Reference Integrity Analyzer

Analyzes cross-document references, wiklinks, and dependency graphs
to detect:
- Broken references
- Orphaned documents
- Circular dependencies
- Missing category indices
- Inconsistent naming conventions
"""

import json
import os
import re
from collections import defaultdict
from pathlib import Path


class VaultReferenceAnalyzer:
    """Analyze cross-document references and dependencies"""

    def __init__(self, vault_path: str | None = None):
        if vault_path is None:
            vault_path = Path.cwd() / "cloud-vault-mcp" / "vault"
        self.vault_path = Path(vault_path)

        self.documents = {}  # path -> content
        self.references = defaultdict(set)  # source -> {targets}
        self.inverse_refs = defaultdict(set)  # target -> {sources}
        self.issues = []
        self.graph_nodes = set()
        self.missing_targets = defaultdict(set)

    def run_analysis(self) -> dict:
        """Run complete reference analysis"""
        print("[*] Vault Reference Integrity Analysis")
        print(f"[*] Vault path: {self.vault_path}\n")

        # Load documents
        print("[1] Loading documents...")
        self._load_documents()
        print(f"    Loaded {len(self.documents)} documents")

        # Extract references
        print("\n[2] Extracting references...")
        self._extract_references()
        print(f"    Found {sum(len(v) for v in self.references.values())} references")

        # Analyze graph
        print("\n[3] Analyzing reference graph...")
        self._analyze_graph()

        # Detect orphaned documents
        print("\n[4] Detecting orphaned documents...")
        self._find_orphaned()

        # Check circular dependencies
        print("\n[5] Checking for circular dependencies...")
        self._detect_cycles()

        # Validate naming conventions
        print("\n[6] Validating naming conventions...")
        self._check_conventions()

        # Generate report
        print("\n" + "=" * 60)
        return self._generate_report()

    def _load_documents(self):
        """Load all vault documents"""
        for root, dirs, files in os.walk(self.vault_path):
            dirs[:] = [d for d in dirs if d not in {".git", ".obsidian"}]

            for file in files:
                if file.endswith(".md"):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.vault_path)

                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()
                        self.documents[str(rel_path)] = content
                        self.graph_nodes.add(str(rel_path))
                    except Exception as e:
                        self.issues.append(f"ERROR: Cannot load {rel_path}: {e}")

    def _extract_references(self):
        """Extract all references from documents"""
        # Wikilink pattern: [[link]]
        wikilink_pattern = re.compile(r"\[\[([^\]]+)\]\]")

        # Markdown link pattern: [text](path)
        mdlink_pattern = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")

        for doc_path, content in self.documents.items():
            # Extract wikilinks
            for match in wikilink_pattern.finditer(content):
                link = match.group(1)
                self.references[doc_path].add(link)

            # Extract markdown links (to .md files)
            for match in mdlink_pattern.finditer(content):
                link_url = match.group(2)
                if link_url.endswith(".md") or link_url.endswith(".md)"):
                    # Normalize
                    link = link_url.replace(".md)", "").replace(".md", "")
                    self.references[doc_path].add(link)

        # Build inverse index
        for source, targets in self.references.items():
            for target in targets:
                self.inverse_refs[target].add(source)

    def _analyze_graph(self):
        """Analyze reference graph structure"""
        # Check for missing targets
        all_files = set(self.documents.keys())

        for source, targets in self.references.items():
            for target in targets:
                found = False

                # Try exact match
                if target in all_files:
                    found = True
                else:
                    # Try with .md extension
                    if target.endswith(".md"):
                        candidate = target
                    else:
                        candidate = target + ".md"

                    if candidate in all_files:
                        found = True
                    else:
                        # Try fuzzy match (just filename)
                        target_name = Path(target).name
                        for doc_file in all_files:
                            if doc_file.endswith(target_name):
                                found = True
                                break

                if not found:
                    self.missing_targets[source].add(target)

    def _find_orphaned(self):
        """Detect documents with no incoming references"""
        orphaned = []

        for doc in self.documents.keys():
            # Skip templates and index files
            if "_template" in doc or "README" in doc or "INDEX" in doc:
                continue

            if doc not in self.inverse_refs or len(self.inverse_refs[doc]) == 0:
                orphaned.append(doc)

        if orphaned:
            print(f"\n  WARNING: Found {len(orphaned)} orphaned documents:")
            for doc in orphaned[:10]:
                print(f"    - {doc}")
            if len(orphaned) > 10:
                print(f"    ... and {len(orphaned) - 10} more")

    def _detect_cycles(self):
        """Detect circular dependencies in reference graph"""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node, path):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in self.references.get(node, set()):
                if neighbor not in self.documents:
                    continue

                if neighbor not in visited:
                    if dfs(neighbor, path + [neighbor]):
                        return True
                elif neighbor in rec_stack:
                    # Cycle detected
                    cycle_start = path.index(neighbor) if neighbor in path else 0
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True

            rec_stack.remove(node)
            return False

        for node in self.documents.keys():
            if node not in visited:
                dfs(node, [node])

        if cycles:
            print(f"\n  WARNING: Found {len(cycles)} circular dependencies:")
            for cycle in cycles[:5]:
                print(f"    {' -> '.join(cycle)}")

    def _check_conventions(self):
        """Validate naming conventions"""
        issues = []

        for doc_path in self.documents.keys():
            # Skip special files
            if "_template" in doc_path or doc_path == "README.md":
                continue

            filename = Path(doc_path).stem

            # Check kebab-case for regular files
            if not re.match(r"^\d{4}-\d{2}-\d{2}[-a-z0-9]*$", filename):
                # Allow date prefix format
                if not re.match(r"^[a-z][-a-z0-9]*$", filename):
                    issues.append(f"{doc_path}: Non-kebab-case filename")

        if issues:
            print(f"\n  NAMING ISSUES: {len(issues)} files")
            for issue in issues[:5]:
                print(f"    - {issue}")

    def _generate_report(self) -> dict:
        """Generate comprehensive reference integrity report"""
        report = {
            "total_documents": len(self.documents),
            "total_references": sum(len(v) for v in self.references.values()),
            "missing_references": {
                source: list(targets) for source, targets in self.missing_targets.items() if targets
            },
            "orphaned_documents": [
                doc
                for doc in self.documents.keys()
                if doc not in self.inverse_refs or len(self.inverse_refs[doc]) == 0
            ],
            "high_connectivity": self._find_hubs(),
            "issues": self.issues,
        }

        # Print summary
        print("\nREFERENCE INTEGRITY REPORT")
        print("=" * 60)
        print(f"Total Documents: {report['total_documents']}")
        print(f"Total References: {report['total_references']}")

        if report["missing_references"]:
            print(f"\nBroken References: {len(report['missing_references'])}")
            for source, targets in list(report["missing_references"].items())[:5]:
                print(f"  {source}:")
                for target in targets[:3]:
                    print(f"    -> {target}")

        if report["orphaned_documents"]:
            print(f"\nOrphaned Documents: {len(report['orphaned_documents'])}")
            for doc in report["orphaned_documents"][:5]:
                print(f"  - {doc}")

        if report["high_connectivity"]:
            print("\nHigh-connectivity Hubs (well-integrated):")
            for doc, count in report["high_connectivity"][:5]:
                print(f"  - {doc}: {count} incoming references")

        return report

    def _find_hubs(self) -> list[tuple[str, int]]:
        """Find well-connected hub documents"""
        hubs = [
            (doc, len(self.inverse_refs[doc]))
            for doc in self.documents.keys()
            if self.inverse_refs[doc]
        ]
        hubs.sort(key=lambda x: x[1], reverse=True)
        return hubs[:10]

    def export_report(self, output_path: str | None = None) -> dict:
        """Export detailed reference report"""
        if output_path is None:
            output_path = self.vault_path.parent / "vault_reference_report.json"

        report = self.run_analysis()

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n[*] Full report exported to: {output_path}")
        return report


if __name__ == "__main__":
    analyzer = VaultReferenceAnalyzer()
    analyzer.export_report()
