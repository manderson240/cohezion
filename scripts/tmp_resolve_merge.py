"""Resolve remaining 9 conflicted files for merge of origin/main into branch.

Decisions (usage-verified + two local-model consults):
- unified_hybrid_router.py: hunk1 ours+theirs; hunk2 theirs+ours (dual EVI paths, distinct APIs)
- telegram_bot.py: hunk1 ours (handlers /agy //mode exist); hunk2 theirs (dup method deleted on main)
- compound_server.py: theirs (both sides converged on identical semantic change; theirs is ruff-formatted)
- oom_guard.py: hunk1 ours minus duplicate shmem_gb (declared in common block); hunk2 ours (constants used at :128-130)
- KEY_LEARNINGS.md: theirs (harvest-audit annotation)
- pyproject.toml: union of mypy excludes (main's structural regex + ours' entries)
- mypy_ratchet.py: ours (signature engine, supports --self-test/--write-baseline that main's CI calls)
- mypy_baseline.txt: ours (will re-baseline after pyproject resolves)
- uv.lock: origin/main's copy, then regenerate
"""
import re
import subprocess

MARKER_RE = re.compile(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n?>>>>>>> origin/main\n', re.S)


def read(path):
    return open(path).read()


def apply(path, choices):
    s = read(path)
    hs = MARKER_RE.findall(s)
    if not hs:
        print(f"skip {path} (no markers — already resolved)")
        return
    assert len(hs) == len(choices), f"{path}: {len(hs)} hunks vs {len(choices)} choices"
    it = iter(choices)

    def repl(m):
        return next(it)

    s = MARKER_RE.sub(repl, s, count=len(hs))
    assert '<<<<<<<' not in s and '>>>>>>> origin/main' not in s, f"{path}: markers remain"
    open(path, 'w').write(s)
    print(f"resolved {path} ({len(hs)} hunks)")


def git_show(ref, path):
    return subprocess.run(['git', 'show', f'{ref}:{path}'], capture_output=True, text=True,
                          check=True).stdout


# 1. unified_hybrid_router.py — dual EVI paths; both hunks keep both sides
f = 'src/cohezion/inference/unified_hybrid_router.py'
hs = MARKER_RE.findall(read(f))
if not hs:
    print("skip router (no markers — already resolved)")
else:
    apply(f, [hs[0][0] + hs[0][1], hs[1][1] + hs[1][0]])

# 2. telegram_bot.py — hunk1 ours, hunk2 theirs
f = 'src/cohezion/integrations/telegram_bot.py'
hs = MARKER_RE.findall(read(f))
apply(f, [hs[0][0], hs[1][1]])

# 3. compound_server.py — theirs (converged semantics, ruff-formatted)
f = 'src/cohezion/mcp/compound_server.py'
hs = MARKER_RE.findall(read(f))
apply(f, [hs[0][1]])

# 4. oom_guard.py — hunk1 ours minus dup shmem_gb; hunk2 ours
f = 'src/cohezion/reliability/oom_guard.py'
hs = MARKER_RE.findall(read(f))
apply(f, [hs[0][0].replace('    shmem_gb: float = 0.0\n', ''), hs[1][0]])

# 5. KEY_LEARNINGS.md — theirs
f = 'src/cohezion/knowledge_graph/KEY_LEARNINGS.md'
hs = MARKER_RE.findall(read(f))
apply(f, [hs[0][1]])

# 6. pyproject.toml — union of mypy excludes
f = 'pyproject.toml'
hs = MARKER_RE.findall(read(f))
assert len(hs) == 1, f"pyproject: {len(hs)} hunks"
ours_exclude = re.findall(r'"([^"]+)",?\s*(?:#[^\n]*)?\n', hs[0][0])
theirs_text = hs[0][1]
extra = [e for e in ours_exclude
         if e not in theirs_text and e not in ('baml_client',)]
# insert extras after the structural regex line inside theirs
merged = re.sub(r'(exclude\s*=\s*"[^"]+"\n)',
                r'\1' + ''.join(f'    "{e}",\n' for e in extra),
                theirs_text, count=1)
s = read(f)
marker = '<<<<<<< HEAD\n' + hs[0][0] + '\n=======\n' + hs[0][1] + '\n>>>>>>> origin/main\n'
assert marker in s, "pyproject marker not found"
s = s.replace(marker, merged, 1)
assert '<<<<<<<' not in s
open(f, 'w').write(s)
print("resolved pyproject.toml (union excludes)")

# 7. mypy_ratchet.py + baseline — ours
for f in ['scripts/ci/mypy_ratchet.py', 'scripts/ci/mypy_baseline.txt']:
    hs = MARKER_RE.findall(read(f))
    apply(f, [hs[0][0] for _ in hs])

print("ALL FILES RESOLVED")