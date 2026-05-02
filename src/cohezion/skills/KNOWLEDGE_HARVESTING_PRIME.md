---
name: knowledge-harvesting-prime
description: "Agentic Archaeology & Data Recovery. Specializes in recovering semantic value from \"Ghost Files\" (files deleted from disk but present in git index) and untracked artifacts before destruction."
metadata:
  version: "v1.0 (Born from the 17.3M File Flood of Feb 2026)"
  concepts: ["Ghost Harvest", "Semantic Ingestion", "Safe Pruning"]
  source: "src/cohezion/skills/KNOWLEDGE_HARVESTING_PRIME.md"
---

# SKILL: KNOWLEDGE_HARVESTING_PRIME

## DOMAIN EXPERTISE
**Agentic Archaeology & Data Recovery**. Specializes in recovering semantic value from "Ghost Files" (files deleted from disk but present in git index) and untracked artifacts before destruction.

## KEY TEXTS & CONCEPTS
- **Ghost Harvest**: Using `git ls-files -d --stage` and `git cat-file --batch` to read file content directly from the git object database without checking out the files to disk.
- **Semantic Ingestion**: Classifying files as `Learning` (Insight/Retrospective) or `Journey` (Plan/Thought) and storing them in a Vector Database (SurrealDB).
- **Safe Pruning**: Only deleting (or finalizing deletion of) files AFTER confirmed ingestion.

## INSTRUCTION

### 1. The Ghost Protocol (Recovering Deleted Files)
If files are missing from disk (`D` in `git status`) but were tracked:

```python
import subprocess
from pathlib import Path

def harvest_ghosts(root_dir="."):
    # 1. Stream deleted files from Index
    ls = subprocess.Popen(["git", "ls-files", "-d", "--stage"], stdout=subprocess.PIPE, text=True)
    
    # 2. Pipe to cat-file for content
    cat = subprocess.Popen(["git", "cat-file", "--batch"], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    
    for line in ls.stdout:
        # line: "100644 <OID> 0\t<PATH>"
        meta, path_str = line.split('\t', 1)
        oid = meta.split()[1]
        
        # Request content
        cat.stdin.write(f"{oid}\n".encode())
        cat.stdin.flush()
        
        # Read Header: "<OID> <TYPE> <SIZE>"
        header = cat.stdout.readline().decode()
        if "missing" in header: continue
        size = int(header.split()[2])
        
        # Read Content
        content = cat.stdout.read(size)
        cat.stdout.read(1) # trailing newline
        
        # ... Ingest content ...
```

### 2. The Living Harvest (Untracked Files)
For massive untracked sets, avoid `git ls-files` if >1M files. Use `os.scandir`:
```python
def find_bloat(root):
    for entry in os.scandir(root):
        if entry.is_dir() and entry.name not in ['.git', 'node_modules']:
             # Recursive scan
             pass
```

## VERSION
v1.0 (Born from the 17.3M File Flood of Feb 2026)

## SEE ALSO
- [SYSTEM_HARDENING_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SYSTEM_HARDENING_PRIME.md)
- `src/cohezion/maintenance/harvester.py`
