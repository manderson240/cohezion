#!/usr/bin/env python3
"""Audit docstring and typing coverage across Cohezion codebase."""

import ast
import os

def audit_directory(src_dir="src/cohezion"):
    total_modules = 0
    modules_with_doc = 0
    total_funcs = 0
    funcs_with_doc = 0
    funcs_with_types = 0
    total_classes = 0
    classes_with_doc = 0

    for root, _, files in os.walk(src_dir):
        for f in files:
            if f.endswith(".py") and not f.startswith("__"):
                path = os.path.join(root, f)
                total_modules += 1
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        tree = ast.parse(file.read(), filename=path)
                except Exception:
                    continue

                if ast.get_docstring(tree):
                    modules_with_doc += 1

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith("_"):
                            total_funcs += 1
                            if ast.get_docstring(node):
                                funcs_with_doc += 1
                            # Check typing
                            has_ret = node.returns is not None
                            has_args = all(arg.annotation is not None for arg in node.args.args if arg.arg != "self" and arg.arg != "cls")
                            if has_ret and has_args:
                                funcs_with_types += 1
                    elif isinstance(node, ast.ClassDef):
                        if not node.name.startswith("_"):
                            total_classes += 1
                            if ast.get_docstring(node):
                                classes_with_doc += 1

    print("=== COHEZION CODEBASE DOCUMENTATION & TYPING AUDIT ===")
    print(f"  • Total Modules Audited    : {total_modules}")
    print(f"  • Module Docstring Coverage : {modules_with_doc}/{total_modules} ({modules_with_doc/max(1, total_modules)*100:.1f}%)")
    print(f"  • Public Classes with Docs : {classes_with_doc}/{total_classes} ({classes_with_doc/max(1, total_classes)*100:.1f}%)")
    print(f"  • Public Functions with Docs: {funcs_with_doc}/{total_funcs} ({funcs_with_doc/max(1, total_funcs)*100:.1f}%)")
    print(f"  • Strict Type Annotations  : {funcs_with_types}/{total_funcs} ({funcs_with_types/max(1, total_funcs)*100:.1f}%)")

if __name__ == "__main__":
    audit_directory()
