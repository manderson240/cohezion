#!/usr/bin/env python3
import ast
import sys
from pathlib import Path


def extract_models(file_path: str, output_path: str):
    source = Path(file_path).read_text()
    tree = ast.parse(source)

    models = []
    imports = []

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            seg = ast.get_source_segment(source, node)
            if seg:
                imports.append(seg)
        if isinstance(node, ast.ClassDef):
            # Check if it inherits from BaseModel
            for base in node.bases:
                if (isinstance(base, ast.Name) and base.id == "BaseModel") or (
                    isinstance(base, ast.Attribute) and base.attr == "BaseModel"
                ):
                    seg = ast.get_source_segment(source, node)
                    if seg:
                        models.append(seg)
                    break

    content = "from __future__ import annotations\n\n" + "\n".join(imports) + "\n\n" + "\n\n".join(models) + "\n"

    Path(output_path).write_text(content)
    print(f"Extracted {len(models)} models to {output_path}")


if __name__ == "__main__":
    extract_models(sys.argv[1], sys.argv[2])
