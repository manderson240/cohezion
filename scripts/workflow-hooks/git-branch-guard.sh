#!/usr/bin/env bash
# PreToolUse[Bash] hook — stop the agent from committing on main/master or pushing
# directly to main/master. Reads Claude Code hook JSON on stdin (.tool_input.command).
# Exit 2 = BLOCK (stderr shown to the model); exit 0 = allow.
#
# THREAT MODEL (honest, per adversarial review 2026-07-23): this is a GUARDRAIL against
# an HONEST agent's drift/mistakes, NOT a security sandbox. A command-string check cannot
# stop a determined or compromised actor (base64+eval, a subprocess that runs git
# internally, a direct syscall). For that, pair this with the authoritative server-side
# layer — GitHub branch-protection rulesets and/or a git-native pre-push hook. This hook
# catches the common, accidental main-writes cheaply and deterministically.
#
# Escape hatch: CZ_ALLOW_MAIN=1 (deliberate, human-authorized; logged to stderr, not silent).
# Fail-OPEN on internal error so a hook bug never wedges the agent (a guardrail must not
# become a denial-of-service on itself).
set -uo pipefail

input=$(cat 2>/dev/null || true)
cmd=$(printf '%s' "$input" | python3 -c '
import sys, json
try:
    print(json.load(sys.stdin).get("tool_input", {}).get("command", "") or "")
except Exception:
    print("")
' 2>/dev/null || true)
[ -n "$cmd" ] || exit 0

# Classify: is a `git commit` / `git push` present within a single command segment?
# [^;&|]* tolerates `-c key=val`, `-C dir`, and arbitrary flags/values between `git` and
# the subcommand — closing the `git -c protocol.version=2 push` anchor bypass — while the
# segment boundary (;&|) avoids matching e.g. `git log | grep commit`.
is_commit=no; is_push=no
printf '%s' "$cmd" | grep -Eq '\bgit\b[^;&|]* commit\b' && is_commit=yes
printf '%s' "$cmd" | grep -Eq '\bgit\b[^;&|]* push\b'   && is_push=yes
[ "$is_commit" = yes ] || [ "$is_push" = yes ] || exit 0

if [ "${CZ_ALLOW_MAIN:-0}" = 1 ]; then
  echo "branch-guard: CZ_ALLOW_MAIN=1 — main-branch protection bypassed (audit) for: ${cmd%%$'\n'*}" >&2
  exit 0
fi

branch=$(git branch --show-current 2>/dev/null || true)

# Case A — committing while checked out on main/master.
if [ "$is_commit" = yes ]; then
  case "$branch" in
    main|master)
      echo "branch-guard: refusing 'git commit' on '$branch'. Create a feat/|fix/|chore/ branch first, or set CZ_ALLOW_MAIN=1 to override." >&2
      exit 2 ;;
  esac
fi

# Case B — pushing to main/master (explicit refspec, positional ref incl. +force/refs/heads/
# and quoting, --all/--mirror, or bare push on main).
if [ "$is_push" = yes ]; then
  to_main=no
  cmdq=$(printf '%s' "$cmd" | sed "s/[\"']//g")   # strip quotes so "main"/'main' can't hide the target
  # explicit refspec into main/master:  HEAD:main | :master | src:refs/heads/main  (a leading +force keeps the colon)
  printf '%s' "$cmdq" | grep -Eq ':(refs/heads/)?(main|master)([[:space:]]|$)' && to_main=yes
  # positional main/master push arg, optional +force and/or refs/heads/ full ref:  origin main | +main | refs/heads/main
  printf '%s' "$cmdq" | grep -Eq 'push([[:space:]]+[^[:space:]]+)*[[:space:]]+\+?(refs/heads/)?(main|master)([[:space:]]|$)' && to_main=yes
  # push --all / --mirror pushes every local branch (incl. main) to the remote
  printf '%s' "$cmdq" | grep -Eq 'push([[:space:]]+[^[:space:]]+)*[[:space:]]--(all|mirror)\b' && to_main=yes
  # bare push while sitting on main/master (pushes the current, main-tracking branch)
  if [ "$to_main" = no ]; then
    case "$branch" in main|master) to_main=yes ;; esac
  fi
  if [ "$to_main" = yes ]; then
    echo "branch-guard: refusing direct push to main/master. Land via the gated [land:ready] flow (local gates + adversarial review + semver + fast-forward), or set CZ_ALLOW_MAIN=1 to override." >&2
    exit 2
  fi
fi

exit 0
