#!/usr/bin/env python3
"""
Module metacognition indexer.

Scans src/cohezion/ packages, generates descriptions via Lemonade :13305 (NPU, $0),
UPSERTs code_module records into SurrealDB, and writes vault notes.

Usage:
    uv run python scripts/metacog/index_modules.py            # index new/missing only
    uv run python scripts/metacog/index_modules.py --force    # re-index all
    uv run python scripts/metacog/index_modules.py --dry-run  # preview only
    uv run python scripts/metacog/index_modules.py --module compound  # one module
"""

import argparse
import json
import time
from pathlib import Path

import requests

REPO = Path(__file__).parent.parent.parent
SRC = REPO / "src" / "cohezion"
VAULT_MODULES = Path.home() / "vaults" / "cohezion-vault" / "modules"

SURREAL_URL = "http://localhost:8001/sql"
SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
}
SURREAL_AUTH = ("root", "root")

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
LEMONADE_MODEL = "llama3.2-1b-FLM"

SCHEMA_SQL = """
DEFINE TABLE IF NOT EXISTS code_module SCHEMAFULL;
DEFINE FIELD IF NOT EXISTS name          ON code_module TYPE string;
DEFINE FIELD IF NOT EXISTS path          ON code_module TYPE string;
DEFINE FIELD IF NOT EXISTS description   ON code_module TYPE string;
DEFINE FIELD IF NOT EXISTS key_classes   ON code_module TYPE array;
DEFINE FIELD IF NOT EXISTS last_reviewed ON code_module TYPE datetime;
DEFINE INDEX IF NOT EXISTS idx_code_module_name ON code_module FIELDS name UNIQUE;
"""


def surreal(sql: str) -> list:
    r = requests.post(
        SURREAL_URL, headers=SURREAL_HEADERS, auth=SURREAL_AUTH, data=sql, timeout=10
    )
    r.raise_for_status()
    return r.json()


def get_key_classes(pkg_path: Path) -> list[str]:
    classes: list[str] = []
    for py_file in sorted(pkg_path.glob("*.py"))[:6]:
        try:
            for line in py_file.read_text(errors="replace").splitlines():
                if line.startswith("class ") and "(" in line:
                    name = line.split("(")[0].replace("class ", "").strip()
                    if name and name[0].isupper() and name.isidentifier():
                        classes.append(name)
        except OSError:
            pass
    return classes[:10]


def get_description(module_name: str, key_classes: list[str]) -> str:
    classes_str = ", ".join(key_classes[:5]) or "no public classes"
    prompt = (
        f"In exactly one sentence, describe what the Python package cohezion.{module_name} "
        f"does in the Cohezion compound AI orchestration system. "
        f"Key classes: {classes_str}. Be specific about its role."
    )
    try:
        r = requests.post(
            LEMONADE_URL,
            json={
                "model": LEMONADE_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 80,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"].strip()
    except (requests.RequestException, KeyError, IndexError):
        pass
    return f"Provides {module_name} capabilities for the Cohezion compound AI system."


def upsert_module(name: str, path: str, description: str, key_classes: list[str]) -> None:
    safe_desc = description.replace("'", "`").replace("\\", "\\\\")
    safe_path = path.replace("'", "`")
    classes_json = json.dumps(key_classes)
    sql = (
        f"UPSERT code_module:{name} SET "
        f"name = '{name}', "
        f"path = '{safe_path}', "
        f"description = '{safe_desc}', "
        f"key_classes = {classes_json}, "
        f"last_reviewed = time::now();"
    )
    surreal(sql)


def write_vault_note(name: str, path: str, description: str, key_classes: list[str]) -> None:
    VAULT_MODULES.mkdir(parents=True, exist_ok=True)
    note = VAULT_MODULES / f"{name}.md"
    classes_list = "\n".join(f"- `{c}`" for c in key_classes) or "- (none found)"
    note.write_text(
        f"---\n"
        f"type: code_module\n"
        f"name: {name}\n"
        f"surreal_id: code_module:{name}\n"
        f"path: {path}\n"
        f"tags: [code_module, cohezion]\n"
        f"---\n\n"
        f"# cohezion.{name}\n\n"
        f"{description}\n\n"
        f"## Key Classes\n\n"
        f"{classes_list}\n\n"
        f"## Source\n\n"
        f"`{path}`\n\n"
        f"## Related\n\n"
        f"<!-- Add [[wikilinks]] to decisions, experiments, and patterns -->\n"
    )


def lemonade_ok() -> bool:
    try:
        r = requests.get("http://localhost:13305/api/v1/health", timeout=3)
        return r.status_code == 200
    except requests.RequestException:
        return False


def get_existing_names() -> set[str]:
    try:
        result = surreal("SELECT name FROM code_module;")
        if result and result[0].get("status") == "OK":
            return {row["name"] for row in result[0].get("result", []) if "name" in row}
    except (requests.RequestException, KeyError, IndexError):
        pass
    return set()


def main() -> None:
    parser = argparse.ArgumentParser(description="Index Cohezion modules into SurrealDB + vault")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-index all, even if already indexed")
    parser.add_argument("--module", help="Index only this module name")
    args = parser.parse_args()

    if not args.dry_run:
        try:
            surreal(SCHEMA_SQL)
        except requests.RequestException as e:
            print(f"SurrealDB unreachable: {e}")
            return

    has_lemonade = lemonade_ok()
    if not has_lemonade:
        print("⚠ Lemonade :13305 unreachable — using fallback descriptions")

    existing = get_existing_names() if (not args.force and not args.dry_run) else set()

    packages = sorted(
        p for p in SRC.iterdir()
        if p.is_dir()
        and not p.name.startswith(("_", "."))
        and (p / "__init__.py").exists()
    )
    if args.module:
        packages = [p for p in packages if p.name == args.module]

    total = len(packages)
    print(f"Found {total} packages under src/cohezion/  (already indexed: {len(existing)})")

    indexed = 0
    for i, pkg in enumerate(packages, 1):
        name = pkg.name
        if name in existing:
            print(f"  [{i}/{total}] {name} — skip (indexed)")
            continue

        key_classes = get_key_classes(pkg)

        if args.dry_run:
            print(f"  [{i}/{total}] {name}: classes={key_classes[:3]}")
            continue

        description = (
            get_description(name, key_classes)
            if has_lemonade
            else f"Provides {name} capabilities for the Cohezion compound AI system."
        )

        upsert_module(name, f"src/cohezion/{name}/", description, key_classes)
        write_vault_note(name, f"src/cohezion/{name}/", description, key_classes)
        print(f"  [{i}/{total}] {name} ✓  {description[:72]}")
        indexed += 1

        time.sleep(0.05)  # stay well under 42 TPS limit

    if not args.dry_run:
        print(f"\n✓ Indexed {indexed} new modules. Total in DB: {len(existing) + indexed}")
        print(f"  Vault: {VAULT_MODULES}")
        print(f"  Query: SELECT name, description FROM code_module ORDER BY name;")


if __name__ == "__main__":
    main()
