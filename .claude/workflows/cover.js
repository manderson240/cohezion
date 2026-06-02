export const meta = {
  name: 'cover',
  description: 'Find under-tested cohezion modules and write focused pytest tests for them',
  whenToUse: 'To raise test coverage on a subpackage. Discovers source modules with little or no test coverage, then for each one proposes a test plan and writes a pytest file. Verify with `uv run pytest` afterward.',
  phases: [
    { title: 'Discover', detail: 'find src/cohezion modules lacking tests' },
    { title: 'Plan', detail: 'design a focused test plan per module' },
    { title: 'Write', detail: 'write a pytest file per module' },
  ],
};

// args: optional subpackage to scope to, e.g. "compound" or "physics". Default: pick the highest-value gaps repo-wide.
const SCOPE = (typeof args === 'string' && args.trim()) ? args.trim() : '';
// Cap how many modules we tackle per run so the workflow stays bounded.
const MAX_MODULES = 6;

// Forced-schema agents must always emit via StructuredOutput, even when the result is empty —
// otherwise "nothing found" is answered in prose and the result is silently dropped.
const STRUCT = '\n\nIMPORTANT: Report your result by calling the StructuredOutput tool exactly once; never answer in prose. If there is nothing to report, still call it with an empty array.';

const TARGETS_SCHEMA = {
  type: 'object',
  required: ['modules'],
  properties: {
    modules: {
      type: 'array',
      items: {
        type: 'object',
        required: ['module_path', 'reason'],
        properties: {
          module_path: { type: 'string', description: 'import path or file path under src/cohezion' },
          public_api: { type: 'array', items: { type: 'string' }, description: 'key functions/classes worth testing' },
          reason: { type: 'string', description: 'why this is a high-value, low-coverage target' },
        },
      },
    },
  },
};

const PLAN_SCHEMA = {
  type: 'object',
  required: ['test_file', 'cases'],
  properties: {
    test_file: { type: 'string', description: 'target path under tests/ mirroring the module' },
    cases: {
      type: 'array',
      items: {
        type: 'object',
        required: ['name', 'asserts'],
        properties: {
          name: { type: 'string' },
          asserts: { type: 'string', description: 'the behavior/contract this case pins down' },
        },
      },
    },
  },
};

phase('Discover');
const scopeNote = SCOPE
  ? `Scope strictly to \`src/cohezion/${SCOPE}/\`.`
  : `Look across src/cohezion/ and pick the highest-value gaps (pure logic, clear contracts, no heavy I/O).`;

const discovery = await agent(
  `Find Python modules under src/cohezion that are under-tested. ${scopeNote}\n` +
  `Heuristics: a module is a candidate if there is no matching tests/.../test_<name>.py, or the source has many public functions/classes but a tiny/absent test file. ` +
  `Prefer modules that are testable WITHOUT live services (no network, no SurrealDB, no model inference) — pure functions, dataclasses, validators, math/physics helpers. ` +
  `Avoid anything requiring Ollama/lemonade or a running API. Return at most ${MAX_MODULES} modules, best first.` + STRUCT,
  { label: 'discover-gaps', phase: 'Discover', schema: TARGETS_SCHEMA },
);

const targets = (discovery.modules || []).slice(0, MAX_MODULES);
log(`Found ${targets.length} under-tested module(s)${SCOPE ? ` in ${SCOPE}` : ''}.`);
if (!targets.length) return { scope: SCOPE || 'repo', written: [], note: 'No suitable under-tested modules found.' };

// Pipeline each module: plan its tests, then write the file. Worktree isolation so parallel writers never collide.
const written = await pipeline(
  targets,
  (t) => agent(
    `Design a focused pytest plan for \`${t.module_path}\`. Public API of interest: ${(t.public_api || []).join(', ') || '(infer from the source)'}.\n` +
    `Read the actual source first. Cover the happy path plus edge cases (empty/zero/negative/boundary). ` +
    `Tests must run offline (no network/DB/model). Follow the repo's conventions: pytest, async tests via pytest-asyncio, mock live services at their source (see tests/conftest.py for singleton resets).` + STRUCT,
    { label: `plan:${t.module_path}`, phase: 'Plan', schema: PLAN_SCHEMA },
  ),
  (plan, t) => agent(
    `Write the pytest file at \`${plan.test_file}\` for \`${t.module_path}\` implementing these cases:\n${JSON.stringify(plan.cases, null, 2)}\n\n` +
    `Read the source to get imports/signatures exactly right. Use the Write tool to create the file. ` +
    `Then run \`uv run pytest ${plan.test_file} -q\` and iterate until it passes. ` +
    `Report the final path and pass/fail status honestly — do NOT claim success if it does not pass.`,
    { label: `write:${plan.test_file}`, phase: 'Write', isolation: 'worktree' },
  ).then((result) => ({ module: t.module_path, test_file: plan.test_file, result })),
);

return {
  scope: SCOPE || 'repo',
  attempted: targets.length,
  written: written.filter(Boolean),
  note: 'Each test was written in an isolated worktree. Review the diffs, then run `uv run pytest tests/ -q` on the merged result.',
};
