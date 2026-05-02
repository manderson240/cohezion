#!/usr/bin/env python3
import ast
import sys
from pathlib import Path


def extract_routes(file_path: str, output_path: str):
    source = Path(file_path).read_text()
    tree = ast.parse(source)

    routes = []
    imports = []

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            seg = ast.get_source_segment(source, node)
            if seg:
                imports.append(seg)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Check if it has an @app. decorator
            for decorator in node.decorator_list:
                if isinstance(decorator, (ast.Call, ast.Attribute)):
                    # Handle both @app.get() and @app.get
                    target = decorator.func if isinstance(decorator, ast.Call) else decorator
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "app"
                    ):
                        seg = ast.get_source_segment(source, node)
                        if seg:
                            # Replace @app. with @router.
                            seg = seg.replace("@app.", "@router.")
                            routes.append(seg)
                        break

    content = (
        "from __future__ import annotations\n\n"
        + "from fastapi import APIRouter, HTTPException, Request, Response\n"
        + "from .models import *\n\n"
        + "\n".join([imp for imp in imports if "fastapi" not in imp])
        + "\n\n"
        + "router = APIRouter()\n\n"
        + "\n\n".join(routes)
        + "\n"
    )

    Path(output_path).write_text(content)
    print(f"Extracted {len(routes)} routes to {output_path}")


if __name__ == "__main__":
    extract_routes(sys.argv[1], sys.argv[2])
