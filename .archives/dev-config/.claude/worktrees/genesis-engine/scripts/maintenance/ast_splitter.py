#!/usr/bin/env python3
"""AST-based file splitter for oversized Python modules.

Task 1001-2000: Identifies large files and splits top-level classes/functions
into separate modules while preserving imports.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path


class Splitter:
    def __init__(self, file_path: str, threshold: int = 50, dry_run: bool = True):
        self.path = Path(file_path)
        self.threshold = threshold
        self.dry_run = dry_run
        self.source = self.path.read_text()
        self.tree = ast.parse(self.source)

    def run(self):
        lines = self.source.splitlines()
        print(f"Analyzing {self.path} ({len(lines)} lines)")

        # 1. Identify top-level nodes
        imports = []
        items = []
        other_nodes = []

        for node in self.tree.body:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(node)
            elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                items.append(node)
            else:
                other_nodes.append(node)

        # 2. Extract import text
        import_lines = []
        for imp in imports:
            seg = ast.get_source_segment(self.source, imp)
            if seg:
                import_lines.append(seg)

        # 3. Process items
        new_files = {}
        split_names = []
        remaining_source_parts = []

        # Start with docstring if exists
        first_node = self.tree.body[0] if self.tree.body else None
        if (
            isinstance(first_node, ast.Expr)
            and isinstance(first_node.value, ast.Constant)
            and isinstance(first_node.value.value, str)
        ):
            remaining_source_parts.append(f'"""{first_node.value.value}"""')

        remaining_source_parts.extend(import_lines)

        for item in items:
            item_len = item.end_lineno - item.lineno
            # Heuristic: split if item > 50 lines OR if it's a Pydantic model in a crowded __init__
            should_split = item_len > 50 or (self.path.name == "__init__.py" and item_len > 20)

            if should_split:
                item.name.lower()
                suffix = item.name.lower()
                # Avoid collision if filename already contains the suffix
                if suffix in self.path.stem:
                    new_path = self.path.parent / f"{suffix}.py"
                else:
                    new_path = self.path.parent / f"{self.path.stem}_{suffix}.py"

                # If __init__.py, just use the name
                if self.path.name == "__init__.py":
                    new_path = self.path.parent / f"{suffix}.py"

                item_seg = ast.get_source_segment(self.source, item)
                if item_seg:
                    content = "from __future__ import annotations\n\n" + "\n".join(import_lines) + "\n\n" + item_seg
                    new_files[new_path] = content
                    split_names.append(item.name)
                    print(f"  -> Target: {new_path} ({item_len} lines)")
            else:
                item_seg = ast.get_source_segment(self.source, item)
                if item_seg:
                    remaining_source_parts.append(item_seg)

        for node in other_nodes:
            # Skip the docstring which we already added
            if node == first_node:
                continue
            seg = ast.get_source_segment(self.source, node)
            if seg:
                remaining_source_parts.append(seg)

        # 4. Write new files and update original
        if not self.dry_run:
            for p, content in new_files.items():
                p.write_text(content)
                print(f"  Written {p}")

            # Add imports for split items to original file
            for item_name in split_names:
                # This is a simplification, assumes local import
                # Find which file it went to
                for p in new_files:
                    if item_name.lower() in p.name:
                        remaining_source_parts.insert(len(import_lines) + 1, f"from . {p.stem} import {item_name}")
                        break

            self.path.write_text("\n\n".join(remaining_source_parts))
            print(f"  Updated {self.path}")
        else:
            print(f"  DRY RUN: Would create {len(new_files)} files and update {self.path}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: ast_splitter.py <file_path> [--execute]")
        sys.exit(1)

    execute = "--execute" in sys.argv
    file_path = sys.argv[1]

    splitter = Splitter(file_path, dry_run=not execute)
    splitter.run()
