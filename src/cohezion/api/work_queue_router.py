"""Work queue API — human-in-the-loop approval gate for research and improvement tasks.

Endpoints:
  GET  /api/work-queue          — list items (filterable by status/type)
  POST /api/work-queue          — add an item manually
  PATCH /api/work-queue/{id}    — update status, add feedback/notes
  GET  /kanban                  — serve the Kanban HTML UI
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

router = APIRouter()

WORK_QUEUE_FILE = Path.home() / ".cohezion" / "work-queue.json"
WORK_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)


# ── Storage helpers ───────────────────────────────────────────────────────────
def _load() -> dict:
    if WORK_QUEUE_FILE.exists():
        try:
            return json.loads(WORK_QUEUE_FILE.read_text())
        except Exception:
            pass
    return {"items": [], "version": 1}


def _save(q: dict) -> None:
    WORK_QUEUE_FILE.write_text(json.dumps(q, indent=2, default=str))


# ── Pydantic schemas ──────────────────────────────────────────────────────────
class WorkItemCreate(BaseModel):
    type: str = "task"  # research | improvement | task
    title: str
    description: str = ""
    url: str = ""
    relevance: str = "APPLY"
    domain: str = ""
    notes: str = ""


class WorkItemPatch(BaseModel):
    status: str | None = None  # pending_review | approved | rejected | in_progress | done
    feedback: str | None = None
    notes: str | None = None
    priority: int | None = None  # 0=low 1=normal 2=high


# ── Endpoints ─────────────────────────────────────────────────────────────────
@router.get("/api/work-queue")
def list_items(
    status: str | None = Query(None),
    type_: str | None = Query(None, alias="type"),
    relevance: str | None = Query(None),
):
    q = _load()
    items = q.get("items", [])
    if status:
        items = [i for i in items if i.get("status") == status]
    if type_:
        items = [i for i in items if i.get("type") == type_]
    if relevance:
        items = [i for i in items if i.get("relevance") == relevance]
    # newest first
    items = sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)
    return {"items": items, "total": len(items)}


@router.post("/api/work-queue", status_code=201)
def create_item(body: WorkItemCreate):
    q = _load()
    item: dict[str, Any] = {
        "id": uuid.uuid4().hex[:12],
        "type": body.type,
        "title": body.title,
        "description": body.description,
        "url": body.url,
        "relevance": body.relevance,
        "domain": body.domain,
        "notes": body.notes,
        "status": "pending_review",
        "priority": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "approved_at": None,
        "feedback": "",
    }
    q["items"].append(item)
    _save(q)
    return item


@router.patch("/api/work-queue/{item_id}")
def patch_item(item_id: str, body: WorkItemPatch):
    q = _load()
    for item in q["items"]:
        if item.get("id") == item_id:
            if body.status is not None:
                item["status"] = body.status
                if body.status == "approved":
                    item["approved_at"] = datetime.now(timezone.utc).isoformat()
            if body.feedback is not None:
                item["feedback"] = body.feedback
            if body.notes is not None:
                item["notes"] = body.notes
            if body.priority is not None:
                item["priority"] = body.priority
            _save(q)
            return item
    raise HTTPException(status_code=404, detail=f"Item {item_id} not found")


@router.delete("/api/work-queue/{item_id}")
def delete_item(item_id: str):
    q = _load()
    before = len(q["items"])
    q["items"] = [i for i in q["items"] if i.get("id") != item_id]
    if len(q["items"]) == before:
        raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
    _save(q)
    return {"deleted": item_id}


# ── Kanban HTML UI ─────────────────────────────────────────────────────────────
_KANBAN_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cohezion Kanban</title>
<style>
  :root {
    --bg: #0d1117; --surface: #161b22; --border: #30363d;
    --text: #e6edf3; --muted: #8b949e; --accent: #58a6ff;
    --apply: #3fb950; --monitor: #d29922; --skip: #8b949e;
    --approved: #58a6ff; --done: #3fb950; --rejected: #f85149;
    --in-progress: #bc8cff;
    --radius: 6px; --gap: 12px;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font: 13px/1.5 "SF Mono","Fira Mono",monospace; }
  header { padding: 16px 20px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; gap: 12px; }
  header h1 { font-size: 16px; font-weight: 600; color: var(--accent); }
  header .stats { margin-left: auto; color: var(--muted); font-size: 12px; }
  .controls { padding: 10px 20px; display: flex; gap: 8px; border-bottom: 1px solid var(--border); }
  .controls button { background: var(--surface); border: 1px solid var(--border);
    color: var(--text); padding: 4px 12px; border-radius: var(--radius);
    cursor: pointer; font-size: 12px; }
  .controls button:hover { border-color: var(--accent); }
  .controls button.active { border-color: var(--accent); color: var(--accent); }
  .board { display: flex; gap: var(--gap); padding: var(--gap) 20px;
    overflow-x: auto; min-height: calc(100vh - 100px); align-items: flex-start; }
  .col { background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); min-width: 280px; max-width: 320px; flex-shrink: 0; }
  .col-header { padding: 10px 12px; border-bottom: 1px solid var(--border);
    font-size: 12px; font-weight: 600; display: flex; align-items: center; gap: 6px; }
  .col-header .count { background: var(--border); border-radius: 10px;
    padding: 1px 6px; font-size: 11px; margin-left: auto; }
  .col-body { padding: 8px; display: flex; flex-direction: column; gap: 6px; }
  .card { background: var(--bg); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 10px; cursor: pointer;
    transition: border-color .15s; }
  .card:hover { border-color: var(--accent); }
  .card .rel { font-size: 10px; font-weight: 700; padding: 1px 5px;
    border-radius: 3px; display: inline-block; margin-bottom: 4px; }
  .rel-APPLY { background: #163021; color: var(--apply); }
  .rel-MONITOR { background: #2d1f00; color: var(--monitor); }
  .rel-SKIP, .rel-task { background: #1a1a2e; color: var(--skip); }
  .card .title { font-size: 12px; color: var(--text); margin-bottom: 4px; line-height: 1.4; }
  .card .meta { font-size: 11px; color: var(--muted); }
  .card .actions { margin-top: 8px; display: flex; gap: 4px; flex-wrap: wrap; }
  .card .actions button { font-size: 11px; padding: 2px 8px; border-radius: 3px;
    border: 1px solid var(--border); background: var(--surface); color: var(--text); cursor: pointer; }
  .card .actions .btn-approve { border-color: var(--apply); color: var(--apply); }
  .card .actions .btn-reject { border-color: var(--rejected); color: var(--rejected); }
  .card .actions .btn-approve:hover { background: #163021; }
  .card .actions .btn-reject:hover { background: #2d0a0a; }
  .empty { color: var(--muted); font-size: 12px; text-align: center; padding: 20px 0; }
  /* modal */
  .modal-bg { display: none; position: fixed; inset: 0; background: rgba(0,0,0,.7);
    z-index: 100; align-items: center; justify-content: center; }
  .modal-bg.open { display: flex; }
  .modal { background: var(--surface); border: 1px solid var(--border);
    border-radius: 8px; padding: 20px; max-width: 540px; width: 90%; max-height: 80vh; overflow-y: auto; }
  .modal h2 { font-size: 14px; margin-bottom: 12px; }
  .modal label { font-size: 12px; color: var(--muted); display: block; margin-bottom: 4px; }
  .modal textarea { width: 100%; background: var(--bg); border: 1px solid var(--border);
    color: var(--text); border-radius: var(--radius); padding: 6px; font-size: 12px;
    font-family: inherit; resize: vertical; }
  .modal input { width: 100%; background: var(--bg); border: 1px solid var(--border);
    color: var(--text); border-radius: var(--radius); padding: 6px; font-size: 12px;
    font-family: inherit; }
  .modal .modal-row { margin-bottom: 12px; }
  .modal .modal-actions { display: flex; gap: 8px; justify-content: flex-end; margin-top: 12px; }
  .modal .modal-actions button { padding: 6px 16px; border-radius: var(--radius);
    border: 1px solid var(--border); background: var(--bg); color: var(--text); cursor: pointer; }
  .modal .modal-actions .btn-primary { background: var(--accent); color: #000; border-color: var(--accent); }
  .status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
  .dot-pending { background: var(--monitor); }
  .dot-approved { background: var(--approved); }
  .dot-in_progress { background: var(--in-progress); }
  .dot-done { background: var(--done); }
  .dot-rejected { background: var(--rejected); }
  #add-form { display: none; }
  #add-form.open { display: block; }
</style>
</head>
<body>
<header>
  <h1>⬡ Cohezion Kanban</h1>
  <div class="stats" id="stats">Loading…</div>
</header>
<div class="controls">
  <button onclick="filterType('')" class="active" id="btn-all">All</button>
  <button onclick="filterType('research')" id="btn-research">Research</button>
  <button onclick="filterType('improvement')" id="btn-improvement">Improvement</button>
  <button onclick="filterType('task')" id="btn-task">Task</button>
  <button onclick="toggleAddForm()" style="margin-left:auto">+ Add Task</button>
  <button onclick="loadItems()">⟳ Refresh</button>
</div>
<div id="add-panel" style="padding:12px 20px;border-bottom:1px solid #30363d;display:none">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:700px">
    <div><label style="font-size:12px;color:#8b949e">Title</label>
      <input id="new-title" placeholder="Task description…" style="width:100%;background:#0d1117;border:1px solid #30363d;color:#e6edf3;border-radius:6px;padding:6px;font-size:12px"></div>
    <div><label style="font-size:12px;color:#8b949e">URL (optional)</label>
      <input id="new-url" placeholder="https://…" style="width:100%;background:#0d1117;border:1px solid #30363d;color:#e6edf3;border-radius:6px;padding:6px;font-size:12px"></div>
    <div style="grid-column:1/-1"><label style="font-size:12px;color:#8b949e">Notes</label>
      <textarea id="new-notes" rows="2" placeholder="Context, requirements…" style="width:100%;background:#0d1117;border:1px solid #30363d;color:#e6edf3;border-radius:6px;padding:6px;font-size:12px;font-family:inherit"></textarea></div>
  </div>
  <div style="margin-top:8px;display:flex;gap:8px">
    <button onclick="submitNew()" style="background:#58a6ff;color:#000;border:none;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px">Add</button>
    <button onclick="toggleAddForm()" style="background:#161b22;border:1px solid #30363d;color:#e6edf3;padding:6px 16px;border-radius:6px;cursor:pointer;font-size:12px">Cancel</button>
  </div>
</div>
<div class="board" id="board">Loading…</div>

<!-- Feedback modal -->
<div class="modal-bg" id="modal" onclick="closeModal(event)">
  <div class="modal">
    <h2 id="modal-title">Item Details</h2>
    <div class="modal-row"><label>Feedback / Instructions</label>
      <textarea id="modal-feedback" rows="4" placeholder="Instructions for the agent…"></textarea></div>
    <div class="modal-row"><label>Notes</label>
      <textarea id="modal-notes" rows="3" placeholder="Personal notes…"></textarea></div>
    <div id="modal-abstract" style="font-size:11px;color:#8b949e;margin-bottom:8px"></div>
    <div id="modal-url" style="font-size:11px;margin-bottom:12px"></div>
    <div class="modal-actions">
      <button onclick="closeModal()">Cancel</button>
      <button class="btn-primary" onclick="saveModal()">Save Notes</button>
    </div>
  </div>
</div>

<script>
const API = '/api/work-queue';
let allItems = [];
let currentType = '';
let modalId = null;

const COLS = [
  {key: 'pending_review', label: '🔍 Pending Review', dot: 'pending'},
  {key: 'approved',       label: '✅ Approved',       dot: 'approved'},
  {key: 'in_progress',    label: '⚡ In Progress',    dot: 'in_progress'},
  {key: 'done',           label: '✓ Done',            dot: 'done'},
  {key: 'rejected',       label: '✗ Rejected',        dot: 'rejected'},
];

async function loadItems() {
  const url = currentType ? `${API}?type=${currentType}` : API;
  const resp = await fetch(url);
  const data = await resp.json();
  allItems = data.items || [];
  render();
  const total = allItems.length;
  const pending = allItems.filter(i => i.status === 'pending_review').length;
  const apply = allItems.filter(i => i.relevance === 'APPLY' && i.status === 'pending_review').length;
  document.getElementById('stats').textContent =
    `${total} items · ${pending} pending review · ${apply} APPLY`;
}

function render() {
  const board = document.getElementById('board');
  board.innerHTML = '';
  for (const col of COLS) {
    const items = allItems.filter(i => i.status === col.key);
    const div = document.createElement('div');
    div.className = 'col';
    div.innerHTML = `<div class="col-header">
      <span class="status-dot dot-${col.dot}"></span>${col.label}
      <span class="count">${items.length}</span>
    </div><div class="col-body" id="col-${col.key}"></div>`;
    board.appendChild(div);
    const body = div.querySelector('.col-body');
    if (!items.length) {
      body.innerHTML = '<div class="empty">empty</div>';
      continue;
    }
    for (const item of items) {
      body.appendChild(makeCard(item));
    }
  }
}

function makeCard(item) {
  const card = document.createElement('div');
  card.className = 'card';
  const rel = item.relevance || item.type || 'task';
  const domain = item.domain ? ` · ${item.domain}` : '';
  const age = timeAgo(item.created_at);
  card.innerHTML = `
    <span class="rel rel-${rel}">${rel}</span>
    <div class="title">${esc(item.title)}</div>
    <div class="meta">${age}${domain}</div>
    <div class="actions">
      ${item.status === 'pending_review' ? `
        <button class="btn-approve" onclick="approve('${item.id}',event)">Approve</button>
        <button class="btn-reject" onclick="reject('${item.id}',event)">Reject</button>
      ` : ''}
      <button onclick="openModal('${item.id}',event)">Notes</button>
      ${item.url ? `<button onclick="window.open('${item.url}','_blank')">Open ↗</button>` : ''}
    </div>
  `;
  return card;
}

async function approve(id, e) {
  e.stopPropagation();
  await fetch(`${API}/${id}`, {method:'PATCH',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status:'approved'})});
  loadItems();
}

async function reject(id, e) {
  e.stopPropagation();
  await fetch(`${API}/${id}`, {method:'PATCH',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status:'rejected'})});
  loadItems();
}

function openModal(id, e) {
  if (e) e.stopPropagation();
  modalId = id;
  const item = allItems.find(i => i.id === id);
  if (!item) return;
  document.getElementById('modal-title').textContent = item.title;
  document.getElementById('modal-feedback').value = item.feedback || '';
  document.getElementById('modal-notes').value = item.notes || '';
  document.getElementById('modal-abstract').textContent = item.abstract || item.description || '';
  const urlEl = document.getElementById('modal-url');
  urlEl.innerHTML = item.url ? `<a href="${item.url}" target="_blank" style="color:#58a6ff">${item.url}</a>` : '';
  document.getElementById('modal').classList.add('open');
}

function closeModal(e) {
  if (e && e.target !== document.getElementById('modal')) return;
  document.getElementById('modal').classList.remove('open');
  modalId = null;
}

async function saveModal() {
  if (!modalId) return;
  const feedback = document.getElementById('modal-feedback').value;
  const notes = document.getElementById('modal-notes').value;
  await fetch(`${API}/${modalId}`, {method:'PATCH',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({feedback, notes})});
  document.getElementById('modal').classList.remove('open');
  loadItems();
}

function filterType(t) {
  currentType = t;
  document.querySelectorAll('.controls button[id^=btn]').forEach(b => b.classList.remove('active'));
  document.getElementById(`btn-${t || 'all'}`).classList.add('active');
  loadItems();
}

function toggleAddForm() {
  const p = document.getElementById('add-panel');
  p.style.display = p.style.display === 'none' ? 'block' : 'none';
}

async function submitNew() {
  const title = document.getElementById('new-title').value.trim();
  if (!title) return;
  const url = document.getElementById('new-url').value.trim();
  const notes = document.getElementById('new-notes').value.trim();
  await fetch(API, {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({title, url, notes, type:'task', relevance:'APPLY'})});
  document.getElementById('new-title').value = '';
  document.getElementById('new-url').value = '';
  document.getElementById('new-notes').value = '';
  document.getElementById('add-panel').style.display = 'none';
  loadItems();
}

function esc(s) {
  return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function timeAgo(iso) {
  if (!iso) return '';
  const diff = (Date.now() - new Date(iso)) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff/3600)}h ago`;
  return `${Math.floor(diff/86400)}d ago`;
}

// Auto-refresh every 30s
loadItems();
setInterval(loadItems, 30000);
</script>
</body>
</html>
"""


@router.get("/kanban", response_class=HTMLResponse)
def kanban_ui():
    return HTMLResponse(content=_KANBAN_HTML)
