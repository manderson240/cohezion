"""Core sync operations: sync_file, delete_file, move_file."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .client import SurrealClient
from .config import VAULT_ROOT, DIR_TO_ASPECT, WIKI_LINK_RE
from .helpers import (
    parse_frontmatter, compute_activation, compute_stage,
    sanitize_id, is_content_file, content_hash_sans_neural,
    _writeback_paths,
)


def sync_file(db: SurrealClient, abs_path: str, checkpoint: dict | None = None,
              quiet: bool = False) -> bool:
    """Sync a single vault file to SurrealDB."""
    fpath = Path(abs_path).resolve()
    try:
        rel_path = str(fpath.relative_to(VAULT_ROOT))
    except ValueError:
        return False

    if not is_content_file(rel_path):
        return False

    if not fpath.is_file():
        return False

    try:
        text = fpath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False

    # Skip if this file was just written by NeuralWriteBack
    if rel_path in _writeback_paths:
        _writeback_paths.discard(rel_path)
        return True

    # Content hash check — skip if unchanged (excludes neural: block)
    chash = content_hash_sans_neural(text)
    if checkpoint is not None:
        ckpt_entry = checkpoint.get(rel_path)
        if isinstance(ckpt_entry, dict) and ckpt_entry.get("hash") == chash:
            return True  # Already synced

    fm = parse_frontmatter(text)
    links = list(set(WIKI_LINK_RE.findall(text)))
    word_count = len(text.split())

    stat = fpath.stat()
    modified_ts = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    days_since = (datetime.now(timezone.utc) - modified_ts).days

    directory = rel_path.split("/")[0] if "/" in rel_path else ""
    aspect = DIR_TO_ASPECT.get(directory, "connective")

    title = fm.get("title", fpath.stem.replace("-", " ").title())
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    tags_sql = ", ".join(json.dumps(t, ensure_ascii=False) for t in tags)

    # Resolve neuron ID and fetch DB-owned state in a single query
    existing = db.query_result(
        f"SELECT id, activation, stage, content_hash FROM neuron "
        f"WHERE path = {json.dumps(rel_path, ensure_ascii=False)} LIMIT 1;"
    )
    if existing:
        existing_nid = str(existing[0]["id"])
        nid = existing_nid
    else:
        existing_nid = None
        nid = f"neuron:`{sanitize_id(rel_path)}`"

    # Activation: SurrealDB owns this field. On content change, boost.
    if existing_nid and existing:
        old_act = existing[0].get("activation", 0.5)
        stored_hash = existing[0].get("content_hash", "")
        if chash != stored_hash:
            activation = min(1.0, old_act + 0.1)
        else:
            activation = old_act
    else:
        activation = compute_activation(word_count, len(links), days_since)
    stage = compute_stage(len(links), word_count, activation, days_since)

    # 1. Upsert neuron
    sql = (
        f"UPSERT {nid} SET "
        f"path = {json.dumps(rel_path, ensure_ascii=False)}, "
        f"title = {json.dumps(str(title), ensure_ascii=False)}, "
        f'aspect = "{aspect}", '
        f"activation = {activation:.2f}, "
        f'stage = "{stage}", '
        f"last_fired = time::now(), "
        f"cluster_id = {json.dumps(directory, ensure_ascii=False)}, "
        f"synapse_out = {len(links)}, "
        f"word_count = {word_count}, "
        f"tags = [{tags_sql}], "
        f'content_hash = "{chash}", '
        f"directory = {json.dumps(directory, ensure_ascii=False)}, "
        f"modified = time::now();"
    )
    r = db.query(sql)
    if not r or r[0].get("status") != "OK":
        err = r[0].get("result", "?") if r else "no response"
        if not quiet:
            print(f"  FAIL upsert {rel_path}: {str(err)[:120]}", file=sys.stderr)
        return False

    # 2. Replace outbound synapses
    db.query(f"DELETE synapse WHERE in = {nid};")
    filename_index = db.build_filename_index()
    synapse_ok = 0
    for link_target in links:
        target_key = link_target.strip().lower()
        target_nid = filename_index.get(target_key) or filename_index.get(target_key + ".md")
        if target_nid and target_nid != nid:
            sr = db.query(
                f"RELATE {nid}->synapse->{target_nid} SET "
                f"weight = 1.0, link_type = 'explicit', created = time::now();"
            )
            if sr and sr[0].get("status") == "OK":
                synapse_ok += 1

    # 3. Update inbound count
    ib = db.query_result(f"SELECT count() FROM synapse WHERE out = {nid} GROUP ALL;")
    ic = ib[0]["count"] if ib else 0
    db.query(f"UPDATE {nid} SET synapse_in = {ic};")

    # 4. Akashic history entry
    db.query(
        f"CREATE neuron_history CONTENT {{ "
        f"neuron: {nid}, event_type: 'edited', timestamp: time::now(), "
        f"detail: {json.dumps(f'sync {synapse_ok} links {word_count}w', ensure_ascii=False)} }};"
    )

    if checkpoint is not None:
        checkpoint[rel_path] = {"hash": chash, "mtime": stat.st_mtime}

    if not existing_nid:
        db.invalidate_cache()

    if not quiet:
        action = "updated" if existing_nid else "created"
        print(f"  {action}: {rel_path} "
              f"(links:{synapse_ok}/{len(links)} stage:{stage} act:{activation:.2f})",
              file=sys.stderr)

    return True


def delete_file(db: SurrealClient, abs_path: str, checkpoint: dict | None = None,
                quiet: bool = False) -> bool:
    """Remove a neuron when its vault file is deleted."""
    fpath = Path(abs_path).resolve()
    try:
        rel_path = str(fpath.relative_to(VAULT_ROOT))
    except ValueError:
        return False

    nid = db.get_neuron_id_by_path(rel_path)
    if not nid:
        if not quiet:
            print(f"  SKIP delete: no neuron for {rel_path}", file=sys.stderr)
        return False

    db.query(f"DELETE synapse WHERE in = {nid} OR out = {nid};")
    db.query(
        f"CREATE neuron_history CONTENT {{ "
        f"neuron: '{nid}', event_type: 'deleted', timestamp: time::now(), "
        f"detail: {json.dumps(f'file removed: {rel_path}', ensure_ascii=False)} }};"
    )
    db.query(f"DELETE {nid};")
    db.invalidate_cache()

    if checkpoint is not None:
        checkpoint.pop(rel_path, None)

    if not quiet:
        print(f"  deleted: {rel_path}", file=sys.stderr)

    return True


def move_file(db: SurrealClient, old_abs: str, new_abs: str,
              checkpoint: dict | None = None, quiet: bool = False) -> bool:
    """Handle a file rename/move."""
    old_path = Path(old_abs).resolve()
    new_path = Path(new_abs).resolve()

    try:
        old_rel = str(old_path.relative_to(VAULT_ROOT))
    except ValueError:
        return False

    nid = db.get_neuron_id_by_path(old_rel)
    if not nid:
        return sync_file(db, str(new_path), checkpoint=checkpoint, quiet=quiet)

    try:
        new_rel = str(new_path.relative_to(VAULT_ROOT))
    except ValueError:
        return False

    new_dir = new_rel.split("/")[0] if "/" in new_rel else ""
    new_aspect = DIR_TO_ASPECT.get(new_dir, "connective")

    db.query(
        f"UPDATE {nid} SET "
        f"path = {json.dumps(new_rel, ensure_ascii=False)}, "
        f"directory = {json.dumps(new_dir, ensure_ascii=False)}, "
        f"cluster_id = {json.dumps(new_dir, ensure_ascii=False)}, "
        f'aspect = "{new_aspect}";'
    )
    db.query(
        f"CREATE neuron_history CONTENT {{ "
        f"neuron: {nid}, event_type: 'moved', timestamp: time::now(), "
        f"detail: {json.dumps(f'{old_rel} -> {new_rel}', ensure_ascii=False)} }};"
    )
    db.invalidate_cache()

    if checkpoint is not None:
        checkpoint.pop(old_rel, None)
        sync_file(db, str(new_path), checkpoint=checkpoint, quiet=quiet)

    if not quiet:
        print(f"  moved: {old_rel} -> {new_rel}", file=sys.stderr)

    return True
