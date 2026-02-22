"""CLI entry point for vault_linker."""

import sys
import argparse
from pathlib import Path
from vault_linker.parser import VaultParser
from vault_linker.resolver import LinkResolver
from vault_linker.tagger import TagPopulator
from vault_linker.stubgen import StubGenerator
from vault_linker.injector import LinkInjector
from vault_linker.report import ReportGenerator


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze and fix broken links in Obsidian vault"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze vault and generate report")
    analyze_parser.add_argument("--vault-path", type=Path, default=Path("."),
                               help="Path to vault root (default: current directory)")

    # Fix command
    fix_parser = subparsers.add_parser("fix", help="Fix broken links and populate tags")
    fix_parser.add_argument("--vault-path", type=Path, default=Path("."),
                           help="Path to vault root (default: current directory)")
    fix_parser.add_argument("--dry-run", action="store_true",
                           help="Preview changes without modifying files")

    # Suggest command
    suggest_parser = subparsers.add_parser(
        "suggest", help="Suggest links for a single vault file"
    )
    suggest_parser.add_argument("file", type=Path, help="Path to the target markdown file")
    suggest_parser.add_argument("--vault-path", type=Path, default=Path("."),
                                help="Path to vault root (default: current directory)")

    # Inject-single command
    inject_single_parser = subparsers.add_parser(
        "inject-single", help="Inject cross-reference links into a single file"
    )
    inject_single_parser.add_argument("file", type=Path, help="Path to the target markdown file")
    inject_single_parser.add_argument("--vault-path", type=Path, default=Path("."),
                                      help="Path to vault root (default: current directory)")
    inject_single_parser.add_argument("--dry-run", action="store_true",
                                      help="Preview changes without modifying files")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    vault_path = args.vault_path.resolve()

    if args.command == "analyze":
        return analyze(vault_path)
    elif args.command == "fix":
        return fix(vault_path, dry_run=args.dry_run)
    elif args.command == "suggest":
        return suggest(vault_path, args.file.resolve())
    elif args.command == "inject-single":
        return inject_single(vault_path, args.file.resolve(), dry_run=args.dry_run)

    return 1


def analyze(vault_path: Path) -> int:
    """
    Analyze vault and generate report.

    Args:
        vault_path: Path to vault root

    Returns:
        Exit code (0 = success)
    """
    print(f"Analyzing vault at: {vault_path}")

    # Parse vault
    vp = VaultParser()
    files_index, link_graph = vp.walk_vault(vault_path)
    broken_links = vp.classify_broken_links(files_index, link_graph)

    # Generate report
    reporter = ReportGenerator(files_index, link_graph, broken_links)
    report = reporter.generate_report()

    # Print report
    print("\n" + report)

    # Save report
    report_file = vault_path / "tools" / "vault_health_report.md"
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report)
    print(f"\n📊 Report saved to: {report_file}")

    return 0


def _is_read_only(file_path: Path, vault_path: Path) -> bool:
    """Check if file is in a read-only directory (parsed but not modified)."""
    try:
        rel = file_path.relative_to(vault_path)
        return rel.parts[0] == "daily"
    except (ValueError, IndexError):
        return False


def fix(vault_path: Path, dry_run: bool = False) -> int:
    """
    Fix broken links and populate tags.

    Args:
        vault_path: Path to vault root
        dry_run: If True, preview changes without modifying files

    Returns:
        Exit code (0 = success)
    """
    if dry_run:
        print(f"🔍 DRY RUN: Previewing changes for vault at: {vault_path}")
        print("(No files will be modified)\n")
    else:
        print(f"🔧 Fixing vault at: {vault_path}\n")

    # Parse vault
    vp = VaultParser()
    files_index, link_graph = vp.walk_vault(vault_path)
    broken_links = vp.classify_broken_links(files_index, link_graph)

    # Collect stats
    changes = {
        "tags_populated": 0,
        "stubs_created": 0,
        "links_injected": 0,
        "links_resolved": 0
    }

    # 1. Populate tags
    print("📝 Populating tags for papers with tags: null...")
    existing_tags = [meta.get("frontmatter", {}).get("tags", [])
                     for meta in files_index.values()
                     if meta.get("frontmatter", {}).get("tags")]
    tagger = TagPopulator(
        existing_concepts=list(files_index.keys()),
        existing_tags=existing_tags,
        files_index=files_index
    )

    for stem, meta in files_index.items():
        if meta.get("frontmatter", {}).get("tags") is None:
            file_path = meta["path"]
            if _is_read_only(file_path, vault_path):
                continue
            updated_content = tagger.populate_tags(file_path)
            if "tags: null" not in updated_content and not dry_run:
                file_path.write_text(updated_content)
                changes["tags_populated"] += 1

    if dry_run:
        null_tags_count = sum(1 for meta in files_index.values()
                              if meta.get("frontmatter", {}).get("tags") is None
                              and not _is_read_only(meta["path"], vault_path))
        print(f"  Would populate tags for {null_tags_count} papers")
    else:
        print(f"  ✓ Populated tags for {changes['tags_populated']} papers")

    # 2. Resolve broken links (rewrite wiki-links with confidence >= 0.8)
    print("\n🔗 Resolving broken links...")
    resolver = LinkResolver(list(files_index.keys()))
    for stem, meta in files_index.items():
        file_path = meta["path"]
        if _is_read_only(file_path, vault_path):
            continue
        content = file_path.read_text(encoding='utf-8')
        updated = content
        for link in meta.get("wiki_links", []):
            link_lower = link.lower()
            if link_lower in files_index:
                continue  # Not broken
            matches = resolver.resolve_link(link)
            if matches and matches[0]["confidence"] >= 0.8:
                target = matches[0]["target"]
                # Rewrite [[broken-link]] to [[resolved-target]]
                updated = updated.replace(f"[[{link}]]", f"[[{target}]]")
                updated = updated.replace(f"[[{link}|", f"[[{target}|")
        if updated != content:
            if not dry_run:
                file_path.write_text(updated, encoding='utf-8')
            changes["links_resolved"] += 1

    if dry_run:
        print(f"  Would resolve links in {changes['links_resolved']} files")
    else:
        print(f"  ✓ Resolved links in {changes['links_resolved']} files")

    # 3. Generate stubs
    print("\n🏗️  Generating concept stubs...")
    stubgen = StubGenerator(vault_path=vault_path)
    if not dry_run:
        stubs = stubgen.generate_stubs(link_graph, files_index)
        changes["stubs_created"] = len(stubs)
        print(f"  ✓ Created {changes['stubs_created']} concept stubs")
    else:
        candidates = stubgen.identify_stub_candidates(link_graph, files_index)
        print(f"  Would create {len(candidates)} concept stubs")

    # 3. Inject cross-reference links
    print("\n🔗 Injecting cross-reference links...")
    injector = LinkInjector(files_index)
    for stem, meta in files_index.items():
        file_path = meta["path"]
        if _is_read_only(file_path, vault_path):
            continue
        original_content = file_path.read_text()
        updated_content = injector.inject_links(file_path, stem)

        if updated_content != original_content:
            if not dry_run:
                file_path.write_text(updated_content)
            changes["links_injected"] += 1

    if dry_run:
        print(f"  Would inject links in {changes['links_injected']} files")
    else:
        print(f"  ✓ Injected links in {changes['links_injected']} files")

    # Summary
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Tags populated: {changes['tags_populated']}")
    print(f"  Links resolved: {changes['links_resolved']}")
    print(f"  Stubs created: {changes['stubs_created']}")
    print(f"  Files with new links: {changes['links_injected']}")
    print("=" * 60)

    if dry_run:
        print("\n✓ Dry run complete. Run without --dry-run to apply changes.")
    else:
        print("\n✓ Vault fixes applied successfully!")

    return 0


def suggest_file(vault_path: Path, file_path: Path) -> str:
    """
    Suggest cross-reference links for a single vault file.

    Uses full walk_vault() to build the link graph (~350ms), then returns
    tag-overlap suggestions and bidirectional gap suggestions for the target file.

    Args:
        vault_path: Root path of the vault
        file_path: Absolute path to the target markdown file

    Returns:
        Human-readable suggestion string (may be empty if no suggestions)
    """
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


def suggest(vault_path: Path, file_path: Path) -> int:
    """
    CLI handler for the suggest subcommand.

    Args:
        vault_path: Root path of the vault
        file_path: Absolute path to the target markdown file

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        return 1

    try:
        output = suggest_file(vault_path, file_path)
        print(output)
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def inject_single(vault_path: Path, file_path: Path, dry_run: bool = False) -> int:
    """
    Inject cross-reference links into a single vault file.

    Runs full VaultParser + LinkInjector but only writes the target file.
    The value is surgical modification (one file write), not speed — indexing
    cost is the same as running 'fix' on the entire vault.

    Args:
        vault_path: Root path of the vault
        file_path: Absolute path to the target markdown file
        dry_run: If True, preview changes without modifying files

    Returns:
        Exit code (0 = success, 1 = error)
    """
    if not file_path.exists():
        print(f"Error: file not found: {file_path}", file=sys.stderr)
        return 1

    if _is_read_only(file_path, vault_path):
        print(f"Error: {file_path.relative_to(vault_path)} is in a read-only directory (daily/)",
              file=sys.stderr)
        return 1

    if dry_run:
        print(f"🔍 DRY RUN: Previewing changes for {file_path.name}")
    else:
        print(f"🔗 Injecting links into {file_path.name}")

    # Build full vault index (same cost as fix, but only writes one file)
    vp = VaultParser()
    files_index, _ = vp.walk_vault(vault_path)

    target_stem = file_path.stem.lower()
    injector = LinkInjector(files_index)

    original_content = file_path.read_text(encoding='utf-8')
    updated_content = injector.inject_links(file_path, target_stem)

    if updated_content == original_content:
        print("  No new links to inject.")
        return 0

    if dry_run:
        # Show diff summary
        orig_lines = set(original_content.splitlines())
        new_lines = set(updated_content.splitlines())
        added = [l for l in new_lines if l not in orig_lines]
        print(f"  Would add {len(added)} line(s):")
        for line in added[:10]:
            print(f"  + {line}")
    else:
        file_path.write_text(updated_content, encoding='utf-8')
        print("  ✓ Links injected successfully.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
