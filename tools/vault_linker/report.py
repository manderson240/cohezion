"""Report generator for vault health metrics."""

from typing import Dict, List, Any
from collections import Counter


class ReportGenerator:
    """Generates vault health reports."""

    def __init__(self, files_index: Dict[str, Any],
                 link_graph: Dict[str, Dict[str, set]],
                 broken_links: Dict[str, List[str]]):
        """
        Initialize report generator.

        Args:
            files_index: Files index from vault parser
            link_graph: Link graph from vault parser
            broken_links: Broken links classified by category
        """
        self.files_index = files_index
        self.link_graph = link_graph
        self.broken_links = broken_links

    def generate_report(self) -> str:
        """
        Generate vault health report.

        Returns:
            Markdown formatted report
        """
        # Calculate metrics
        total_files = len(self.files_index)

        # Count papers with null tags (only files in papers/ directory)
        null_tags_count = sum(1 for meta in self.files_index.values()
                              if meta.get("frontmatter", {}).get("tags") is None
                              and "papers" in str(meta.get("path", "")).split("/"))

        # Count broken links by category
        total_broken = sum(len(links) for links in self.broken_links.values())
        date_prefixed = len(self.broken_links.get("date_prefixed", []))
        external = len(self.broken_links.get("external", []))
        missing = len(self.broken_links.get("missing", []))

        # Count total links
        all_targets = set()
        for node_links in self.link_graph.values():
            all_targets.update(node_links.get("outgoing", set()))
        total_links = len(all_targets)
        valid_links = total_links - total_broken

        # Build report
        report = f"""# Vault Health Report

## Summary

| Metric | Value |
|--------|-------|
| Total Files | {total_files} |
| Total Link Targets | {total_links} |
| Valid Links | {valid_links} ({valid_links*100//total_links if total_links else 0}%) |
| Broken Links | {total_broken} ({total_broken*100//total_links if total_links else 0}%) |
| Papers with null tags | {null_tags_count} |

## Broken Links by Category

| Category | Count | Description |
|----------|-------|-------------|
| Date-prefixed | {date_prefixed} | Links with YYYY-MM-DD- prefix (references to dated artifacts) |
| External references | {external} | Links to external systems/code (underscores, .py/.js files) |
| Missing concepts | {missing} | Genuinely missing concept files |

## Top Broken Links (by reference count)

"""

        # Find most referenced broken links
        broken_ref_counts = Counter()
        for stem, links_data in self.link_graph.items():
            for target in links_data.get("outgoing", set()):
                if target not in self.files_index:
                    broken_ref_counts[target] += 1

        for link, count in broken_ref_counts.most_common(20):
            # Classify the link
            if any(link in self.broken_links.get(cat, []) for cat in ["date_prefixed", "external"]):
                category = "date/external"
            else:
                category = "missing"
            report += f"- `{link}` ({count} references) - {category}\n"

        report += f"""
## Recommendations

1. **Populate tags:** {null_tags_count} papers need tags
2. **Create concept stubs:** {min(20, len([l for l in broken_ref_counts if broken_ref_counts[l] >= 3]))} frequently-referenced concepts should get stub files
3. **Add cross-references:** Papers and concepts need Related sections populated

Run `python -m vault_linker fix` to apply automated fixes.
"""

        return report
