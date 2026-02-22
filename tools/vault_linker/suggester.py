"""Suggest cross-reference links for individual vault files."""

from pathlib import Path

from vault_linker.parser import VaultParser


def suggest_file(vault_path: Path, file_path: Path) -> str:
    """Suggest cross-reference links for a single vault file using tag overlap and bidirectional gaps."""
    vp = VaultParser()
    files_index, link_graph = vp.walk_vault(vault_path)

    target_stem = file_path.stem.lower()
    target_meta = files_index.get(target_stem, {})
    target_tags = set(target_meta.get("frontmatter", {}).get("tags") or [])
    existing_links = {lnk.lower() for lnk in target_meta.get("wiki_links", [])}

    # No tags and no incoming links → helpful message
    incoming = link_graph.get(target_stem, {}).get('incoming', set())
    if not target_tags and not incoming:
        return "📎 No suggestions available (add tags to get link suggestions)"

    # Tag-overlap suggestions (up to 5 total across both categories)
    MAX_SUGGESTIONS = 5
    tag_suggestions: list[str] = []
    if target_tags:
        for stem, meta in files_index.items():
            if stem == target_stem:
                continue
            if stem in existing_links:
                continue
            other_tags = set(meta.get("frontmatter", {}).get("tags") or [])
            if target_tags & other_tags:
                tag_suggestions.append(stem)
            if len(tag_suggestions) >= MAX_SUGGESTIONS:
                break

    # Bidirectional gap suggestions
    bidi_gaps = vp.find_bidirectional_gaps(link_graph, target_stem)
    # Remove gaps already captured in tag suggestions or already linked
    bidi_suggestions = [g for g in bidi_gaps if g not in existing_links and g not in tag_suggestions]

    if not tag_suggestions and not bidi_suggestions:
        return "📎 No new suggestions found"

    lines = [f"📎 Suggested links for {file_path.name}:"]
    if tag_suggestions:
        lines.append("  Tag overlap:")
        for stem in tag_suggestions[:MAX_SUGGESTIONS]:
            lines.append(f"  - [[{stem}]]")
    if bidi_suggestions:
        remaining = MAX_SUGGESTIONS - len(tag_suggestions)
        lines.append("  Bidirectional gaps (links to you):")
        for stem in bidi_suggestions[:remaining]:
            lines.append(f"  - [[{stem}]]")

    return "\n".join(lines)
