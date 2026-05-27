#!/usr/bin/env python3
"""
Vault Integrity Verification Suite

Validates:
1. Markdown file format correctness
2. Document metadata consistency
3. Orphaned/unreferenced documents
4. Duplicate entries
5. Cross-document references
6. Git history integrity
7. Stale TODOs and incomplete sections
8. Backup/recovery procedures
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class VaultIntegrityChecker:
    """Comprehensive vault data integrity validator"""

    def __init__(self, vault_path: str | None = None):
        if vault_path is None:
            vault_path = Path.cwd() / "cloud-vault-mcp" / "vault"
        self.vault_path = Path(vault_path)
        self.issues = []
        self.warnings = []
        self.stats = {
            "total_files": 0,
            "total_documents": 0,
            "files_by_category": defaultdict(int),
            "metadata_quality": defaultdict(int),
        }
        self.documents = {}  # path -> content
        self.references = defaultdict(set)  # file -> referenced_files
        self.metadata_index = {}  # path -> metadata

    def run_all_checks(self) -> dict:
        """Run complete integrity verification suite"""
        print("[*] Starting Vault Integrity Verification")
        print(f"[*] Vault path: {self.vault_path}")
        print()

        # Phase 1: Load and parse
        print("[Phase 1] Loading vault documents...")
        self._load_documents()
        print(f"  Loaded {self.stats['total_documents']} documents")

        # Phase 2: Format validation
        print("\n[Phase 2] Validating markdown format...")
        self._validate_markdown_format()

        # Phase 3: Metadata consistency
        print("\n[Phase 3] Checking metadata consistency...")
        self._validate_metadata()

        # Phase 4: References
        print("\n[Phase 4] Analyzing cross-document references...")
        self._analyze_references()

        # Phase 5: Duplicates
        print("\n[Phase 5] Detecting duplicates and conflicts...")
        self._detect_duplicates()

        # Phase 6: Git integrity
        print("\n[Phase 6] Validating git history...")
        self._validate_git_integrity()

        # Phase 7: TODOs and incomplete sections
        print("\n[Phase 7] Scanning for stale TODOs...")
        self._find_stale_todos()

        # Phase 8: Backup/recovery
        print("\n[Phase 8] Checking backup/recovery procedures...")
        self._check_recovery_readiness()

        # Generate report
        print("\n" + "=" * 60)
        return self._generate_report()

    def _load_documents(self):
        """Load and index all vault documents"""
        md_pattern = re.compile(r"\.md$")

        for root, dirs, files in os.walk(self.vault_path):
            # Skip .git and .obsidian
            dirs[:] = [d for d in dirs if d not in {".git", ".obsidian"}]

            for file in files:
                if md_pattern.search(file):
                    file_path = Path(root) / file
                    rel_path = file_path.relative_to(self.vault_path)

                    try:
                        with open(file_path, encoding="utf-8") as f:
                            content = f.read()
                        self.documents[str(rel_path)] = content
                        self.stats["total_documents"] += 1

                        # Count by category
                        category = str(rel_path).split("/")[0]
                        self.stats["files_by_category"][category] += 1
                    except Exception as e:
                        self.issues.append(f"ERROR: Cannot read {rel_path}: {e}")

    def _validate_markdown_format(self):
        """Validate markdown file format"""
        for doc_path, content in self.documents.items():
            issues = []

            # Check for basic markdown structure
            has_heading = bool(re.search(r"^#+ ", content, re.MULTILINE))
            if not has_heading and not doc_path.endswith("_template.md"):
                issues.append("No heading found")

            # Check for unclosed code blocks
            code_fence_count = content.count("```")
            if code_fence_count % 2 != 0:
                issues.append("Unclosed code block (odd number of ```)")

            # Check for unclosed brackets
            if content.count("[") != content.count("]"):
                issues.append(
                    f"Mismatched brackets: [{content.count('[')} vs ]{content.count(']')}"
                )

            # Check for valid YAML frontmatter
            if content.startswith("---"):
                fm_match = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
                if fm_match:
                    fm_content = fm_match.group(1)
                    # Basic YAML validation
                    if not all(":" in line or not line.strip() for line in fm_content.split("\n")):
                        issues.append("Invalid YAML frontmatter")

            # Check for orphaned links
            links = re.findall(r"\[([^\]]+)\]\(([^)]+)\)", content)
            for link_text, link_url in links:
                if link_url.endswith(".md"):
                    # Internal reference
                    self.references[doc_path].add(link_url)

            if issues:
                self.warnings.append(f"{doc_path}: {'; '.join(issues)}")

    def _validate_metadata(self):
        """Check metadata consistency across documents"""
        required_fields = {
            "decisions": {"date", "status"},
            "experiments": {"date", "status"},
            "patterns": {"category"},
            "projects": {"status"},
        }

        for doc_path in self.documents:
            # Determine category from path
            category = doc_path.split("/")[0]

            # Extract frontmatter if present
            content = self.documents[doc_path]
            fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)

            if fm_match and category in required_fields:
                fm_content = fm_match.group(1)
                metadata = {}
                for line in fm_content.split("\n"):
                    if ":" in line:
                        key, val = line.split(":", 1)
                        metadata[key.strip().lower()] = val.strip()

                self.metadata_index[doc_path] = metadata

                # Check required fields
                missing = required_fields[category] - set(metadata.keys())
                if missing:
                    self.warnings.append(f"{doc_path}: Missing metadata: {missing}")

                # Track metadata quality
                if metadata:
                    self.stats["metadata_quality"][category] += 1

    def _analyze_references(self):
        """Analyze cross-document references"""
        all_docs = set(self.documents.keys())

        for source, targets in self.references.items():
            for target in targets:
                # Normalize path
                if not target.endswith(".md"):
                    target += ".md"

                # Check if target exists
                found = False
                for doc in all_docs:
                    if doc.endswith(target):
                        found = True
                        break

                if not found:
                    self.issues.append(f"BROKEN REFERENCE: {source} -> {target} (target not found)")

    def _detect_duplicates(self):
        """Detect duplicate or conflicting documents"""
        # Check for duplicate content
        content_hashes = {}
        for doc_path, content in self.documents.items():
            # Simple content hash for detection
            content_sig = content[:200].lower()  # First 200 chars normalized

            if content_sig in content_hashes:
                self.warnings.append(
                    f"POTENTIAL DUPLICATE: {doc_path} vs {content_hashes[content_sig]}"
                )
            else:
                content_hashes[content_sig] = doc_path

        # Check for conflicting decisions/experiments
        dates = defaultdict(list)
        for doc_path, metadata in self.metadata_index.items():
            if "date" in metadata:
                date_key = metadata["date"]
                dates[date_key].append(doc_path)

        for date_key, docs in dates.items():
            if len(docs) > 1:
                # Multiple docs same date - check if conflicting
                topics = set()
                for doc in docs:
                    title = Path(doc).stem
                    topics.add(title)

                if len(topics) < len(docs):
                    self.warnings.append(
                        f"POTENTIAL CONFLICT: Multiple documents on {date_key}: {docs}"
                    )

    def _validate_git_integrity(self):
        """Validate git history integrity"""
        git_dir = self.vault_path / ".git"

        if not git_dir.exists():
            self.issues.append("CRITICAL: Vault .git directory missing")
            return

        # Check critical git objects
        objects_dir = git_dir / "objects"
        if not objects_dir.exists():
            self.issues.append("CRITICAL: Git objects directory missing")

        # Check refs
        refs_dir = git_dir / "refs"
        heads_dir = refs_dir / "heads"

        if heads_dir.exists():
            branches = list(heads_dir.iterdir())
            if not branches:
                self.warnings.append("WARNING: No branches found in vault git")
        else:
            self.issues.append("CRITICAL: Git refs/heads directory missing")

        # Validate git config
        config_path = git_dir / "config"
        if config_path.exists():
            try:
                with open(config_path) as f:
                    config = f.read()
                    if "repositoryformatversion" not in config:
                        self.warnings.append("WARNING: Git config missing version")
            except Exception as e:
                self.issues.append(f"ERROR: Cannot read git config: {e}")

    def _find_stale_todos(self):
        """Scan for stale TODOs and incomplete sections"""
        todo_pattern = re.compile(r"(TODO|FIXME|XXX|HACK|NOTE):\s*(.+?)(?=\n|$)", re.IGNORECASE)
        incomplete_pattern = re.compile(r"\[incomplete\]|\[wip\]|\[draft\]", re.IGNORECASE)

        for doc_path, content in self.documents.items():
            todos = todo_pattern.findall(content)
            if todos:
                for todo_type, todo_text in todos:
                    # Check if date is old (>30 days)
                    self.warnings.append(f"{doc_path}: {todo_type}: {todo_text[:60]}...")

            if incomplete_pattern.search(content):
                self.warnings.append(f"{doc_path}: Marked as incomplete/draft/WIP")

    def _check_recovery_readiness(self):
        """Verify backup and recovery procedures"""
        # Check for backup documentation
        recovery_docs = [
            doc for doc in self.documents if "backup" in doc.lower() or "recovery" in doc.lower()
        ]

        if not recovery_docs:
            self.warnings.append("No recovery/backup documentation found in vault")

        # Check if vault structure allows regeneration
        essential_dirs = ["decisions", "experiments", "patterns", "projects"]
        for dir_name in essential_dirs:
            dir_path = self.vault_path / dir_name
            if not dir_path.exists():
                self.issues.append(f"CRITICAL: Missing directory: {dir_name}")

    def _generate_report(self) -> dict:
        """Generate comprehensive integrity report"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "vault_path": str(self.vault_path),
            "statistics": dict(self.stats),
            "status": "PASS" if not self.issues else "FAIL",
            "critical_issues": self.issues,
            "warnings": self.warnings,
            "recommendations": self._generate_recommendations(),
        }

        # Print summary
        print(f"\n{'=' * 60}")
        print(f"VAULT INTEGRITY REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'=' * 60}\n")

        print(f"Status: {report['status']}")
        print("\nStatistics:")
        print(f"  Total Documents: {self.stats['total_documents']}")
        print("  Documents by Category:")
        for cat, count in self.stats["files_by_category"].items():
            print(f"    - {cat}: {count}")

        if self.issues:
            print(f"\n[CRITICAL] Issues Found: {len(self.issues)}")
            for issue in self.issues:
                print(f"  - {issue}")

        if self.warnings:
            print(f"\n[WARNING] Warnings: {len(self.warnings)}")
            for warning in self.warnings[:10]:  # Show first 10
                print(f"  - {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")

        print("\nRecommendations:")
        for rec in report["recommendations"]:
            print(f"  - {rec}")

        return report

    def _generate_recommendations(self) -> list[str]:
        """Generate recommendations based on findings"""
        recommendations = []

        if self.issues:
            recommendations.append("Address CRITICAL issues before committing to main branch")

        if len(self.documents) < 100:
            recommendations.append(
                f"Vault appears sparse ({len(self.documents)} docs). Verify Phase 5B files were committed."
            )

        if self.warnings:
            recommendations.append("Review and address warnings for data consistency")

        if not any("recovery" in d.lower() for d in self.documents):
            recommendations.append("Document backup and recovery procedures in vault")

        recommendations.append("Run vault integrity checks before each major commit")
        recommendations.append("Consider automated validation in pre-commit hooks")

        return recommendations

    def export_report(self, output_path: str | None = None):
        """Export detailed report to JSON"""
        if output_path is None:
            output_path = self.vault_path.parent / "vault_integrity_report.json"

        report = self.run_all_checks()

        with open(output_path, "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n[*] Full report exported to: {output_path}")
        return report


if __name__ == "__main__":
    checker = VaultIntegrityChecker()
    report = checker.export_report()

    # Exit with error code if critical issues
    sys.exit(1 if report["status"] == "FAIL" else 0)
