# How Cohezion was built

Cohezion was written almost entirely by AI coding agents. I directed them. This document is
about that process: how the work is organized, how agent output is checked, what went wrong,
and what I changed because of it. All numbers come from this repository's git history and file
tree as of 2026-10-23.

## The short version

- **2,302 commits and 201 merged PRs in about eleven months**, by one person directing agents.
- **The agents write the code; I own the system around them.** That means the operating
  contract, the specialist roles, the CI gates, the landing process, and every merge.
- **Green tests turned out not to be enough.** The biggest lesson was that agent-written code
  can pass thousands of unit tests while being disconnected end to end. Most of the
  engineering here is about catching that.
- **Every failure becomes a rule or a scanner.** There are 17 custom CI scanners now, most of
  them written after a specific incident.

## Who does what

| Role | Who | What they own |
|---|---|---|
| Lead | Me | Direction, the agent contract, which gates exist, merge decisions, retrospectives |
| Implementers | Claude Code (Opus, Sonnet, Haiku), Gemini CLI, opencode, local models | Code, tests and docs for a scoped task, delivered as a PR |
| Specialists | 21 agent definitions in [`.claude/agents/`](../.claude/agents/) | Narrow jobs such as code review, test running, performance or MCP work |
| Reviewers | Claude Code Review on every PR; Gemini review on demand; a separate "assume it's broken" agent for load-bearing changes | Independent review of a change, never by the agent that wrote it |
| Gates | CI pipeline, pre-commit, [`automerge_guard.sh`](../scripts/ci/automerge_guard.sh) | Mechanical checks nobody can argue with |

Commit trailers show the mix of models over the year. The largest named sets of co-authored
commits are Claude (407 untagged), Claude Haiku 4.5 (127), Claude Opus 4.6 (79), Claude Opus
4.8 (35) and Claude Sonnet 4.5 (26). Many commits carry no trailer, so these are lower bounds.

## The operating contract

Agents start every session with no memory of the last one, so whatever they need to know has to
be written down where they will read it.

- [`CLAUDE.md`](../CLAUDE.md) and [`AGENTS.md`](../AGENTS.md) hold the standing rules: never
  print secrets, always use `uv`, keep MCP stdio servers silent on stdout, load deferred tools
  before calling them. Many entries cite the session where the lesson was learned.
- [`.claude/rules/`](../.claude/rules/) holds rules that grew out of incidents, with the
  incident written next to the rule so an agent understands why it exists.
- 229 versioned PRIME skills in [`src/cohezion/skills/`](../src/cohezion/skills/) are loaded on
  demand, so agents get specialized know-how without carrying all of it in context.
- Session hooks validate the agent configuration itself, because an invalid field in
  `settings.json` silently disables every setting.

## How a change lands

1. I scope a task and hand it to an agent, or to a team of agents for larger campaigns.
2. The agent works on a branch and opens a PR with conventional-commit messages. Across the
   history that is 881 `feat`, 492 `fix`, 332 `docs`, 169 `chore` and 81 `test` commits.
3. Pre-commit runs 19 hooks: format, lint, secret detection, bandit, large-file and LFS guards,
   and a guard against hardcoded home-directory paths.
4. CI runs lint, the test suite, type-check ratchets and the custom scanners.
5. Claude Code Review comments on the PR. For load-bearing changes a second agent is told to
   assume the change is broken and to try to prove it.
6. [`automerge_guard.sh`](../scripts/ci/automerge_guard.sh) re-validates the PR merged on top of
   the current tip of `main` in a temporary worktree. It serializes landings and blocks only on
   failures the PR caused, by comparing against a clean control worktree of `main`.
7. After a significant session, the retrospective turns anything surprising into a new rule,
   skill or scanner.

## What went wrong, and what changed

### Green tests, dormant system

In June 2026 a session that followed a strict V-model process still shipped backwards routing,
a quality gate that measured a constant, and an evaluation chain that was wired up component by
component but never ran end to end. Every unit test was green.

The root cause was that the tests checked the bottom rung only: mocked boundaries, tests written
by the same agent that wrote the code, and invariants that asserted a symbol existed rather
than that something used it. I wrote down the correction as a standing rule,
[`verification-depth.md`](../.claude/rules/verification-depth.md):

1. **Test the claim, not the component.** Before saying "fixed", state the claim in one sentence
   and run the command that would falsify it.
2. **Consumption, not declaration.** A capability is wired only when a production caller reads
   it and acts on it. No caller means it is dormant, however green the tests are.
3. **One un-mocked smoke test per real boundary.** Mocks make a wrong port or an empty model
   reply invisible.
4. **Break the author-test correlation.** The agent that writes a change cannot be the one that
   verifies it.

Then I made the rule enforceable. [`dormancy_scan.py`](../scripts/ci/dormancy_scan.py) became a
blocking CI gate in July 2026, and a family of sibling scanners followed, each asking one
question agents tend to get wrong:

| Scanner | Question |
|---|---|
| `dormancy_scan.py` | Does anything outside the tests call this? |
| `falsifiability_scan.py` | Can this invariant ever fail? |
| `false_contract_scan.py` | Does the function do what its name says? |
| `phantom_attr_scan.py` | Is code reading an attribute the class never defines, masked by a `getattr` default? |
| `declared_field_scan.py` | Does a persisted record write every field it declares? |
| `unrestricted_exec_scan.py` | Does generated code ever run with full builtins? |

Most of them have a `--self-test` mode that proves the gate can go red before it is trusted to
report green.

### A dead port that no test could see

The routing layer had a gate that was supposed to probe a world-model service before routing a
task. It probed port `:13306`, which was offline, instead of the router on `:13305`. The gate
therefore never ran, and nothing failed, because every test mocked the network call. It was
found only by an adversarial review against the live system. The fix was one line. The lasting
change was the rule that every real boundary gets an un-mocked smoke test, plus
[`check_inference_port_bypass.sh`](../scripts/ci/check_inference_port_bypass.sh), which fails CI
when code bypasses the single router endpoint.

### Agents describing tools that did not exist

The rules file referred to a port-bypass checker script and an allow-list entry, and neither
existed anywhere in the repository. The documentation had gotten ahead of the code, and agents
reading it were trusting a check that never ran. The script was rebuilt from scratch, and
[`doc_code_consistency.py`](../scripts/ci/doc_code_consistency.py) now checks that the docs
describe code that actually exists.

### A detector nobody called

A regression of a known bad pattern, a bare `except` that hides errors, came back even though
a working detector for it already existed. The detector had no CI caller. The fix was to wire it
into CI ([`check_stealth_excepts.py`](../scripts/ci/check_stealth_excepts.py)), and the general
lesson went into the dormancy rule: a guardrail that nothing runs is not a guardrail.

### A router that was fooled by luck

The first tier predictor sent a task to the cheapest tier that had succeeded often enough. A
few lucky cheap successes could pin hard tasks to a weak model, and an even three-way split
defaulted to the most expensive tier. It now uses a Wilson lower confidence bound on clean
successes ([`difficulty_estimator.py`](../src/cohezion/compound/difficulty_estimator.py)),
which was validated across 400 random seeds, and health signals are only allowed to escalate a
task, never make it cheaper.

### A repository that grew too fast

Agent output piles up. The git bundle reached 14 GB before a migration to Git LFS brought it to
182 MB, and pre-commit now blocks large binaries that are not in LFS. Lint, type and mutation
debt are held by ratchets ([`ruff_ratchet.py`](../scripts/ci/ruff_ratchet.py),
[`mypy_ratchet.py`](../scripts/ci/mypy_ratchet.py),
[`mutation_ratchet.py`](../scripts/ci/mutation_ratchet.py)): existing debt is allowed, but no
change may add to it.

## Running agents cheaply

Most routine model calls run on one AMD Strix Halo workstation (Ryzen AI MAX+ 395, Radeon
8060S, 128 GB unified memory) through a single router on `:13305`, which spreads work across
the NPU, iGPU and CPU. Cloud models are the fallback when local quality gates fail. Because
local inference is effectively free per call, there is no cost excuse to skip a second,
independent review agent.

A proper cost and latency comparison between Claude-only, local-only and hybrid setups is the
next measurement to finish. The harness is in
[`scripts/benchmark_fleet.py`](../scripts/benchmark_fleet.py), and only a pilot run exists so
far, so I make no savings claim yet.

## What I would tell a team adopting coding agents

1. **Assume green means "not yet known to be broken".** Agents optimize for the checks you have.
   Check what the system does, not what the tests say.
2. **Separate the writer from the verifier.** Different agent, fresh context, told to break it.
3. **Write rules down where agents will read them, with the reason attached.** Context resets
   every session, and a rule without its story gets argued away.
4. **Turn every surprise into a mechanical check.** Advice decays; a CI gate does not.
5. **Ratchet debt instead of demanding zero.** At agent speed, "no new debt" is enforceable and
   "no debt" is not.

My background is ten years in data quality and data engineering. The instinct that job
builds, distrusting a pipeline until you have tested the claim it makes, turned out to be the
core skill for directing agents too.
