export const meta = {
  name: 'docs',
  description: 'Audit cohezion modules for missing/weak docs and generate docstrings + a module reference page',
  whenToUse: 'To improve documentation coverage. Audits public modules/classes/functions for missing or thin docstrings, then writes Google-style docstrings in place and produces a short reference doc. Does not change runtime behavior.',
  phases: [
    { title: 'Audit', detail: 'find public APIs lacking real docstrings' },
    { title: 'Document', detail: 'add docstrings in place, one module per agent' },
    { title: 'Index', detail: 'assemble a reference page from the results' },
  ],
};

// args: optional subpackage to scope to, e.g. "environments". Default: highest-value public surfaces.
const SCOPE = (typeof args === 'string' && args.trim()) ? args.trim() : '';
const MAX_MODULES = 6;

const AUDIT_SCHEMA = {
  type: 'object',
  required: ['modules'],
  properties: {
    modules: {
      type: 'array',
      items: {
        type: 'object',
        required: ['module_path', 'gaps'],
        properties: {
          module_path: { type: 'string' },
          gaps: { type: 'array', items: { type: 'string' }, description: 'public symbols with missing/one-line docstrings' },
          audience: { type: 'string', description: 'who reads this module (user / contributor / internal)' },
        },
      },
    },
  },
};

const DOC_RESULT_SCHEMA = {
  type: 'object',
  required: ['module_path', 'summary', 'documented'],
  properties: {
    module_path: { type: 'string' },
    summary: { type: 'string', description: 'one-paragraph plain-language description of the module' },
    documented: { type: 'array', items: { type: 'string' }, description: 'symbols that received docstrings' },
  },
};

phase('Audit');
const scopeNote = SCOPE
  ? `Scope strictly to \`src/cohezion/${SCOPE}/\`.`
  : `Prioritize user-facing surfaces (environments/, eval/, the public CompoundExecutor/CostAwareRouter APIs).`;

const audit = await agent(
  `Audit Python modules under src/cohezion for documentation gaps. ${scopeNote}\n` +
  `A gap is a public module/class/function (no leading underscore) whose docstring is missing or a useless one-liner. ` +
  `Read the actual files. Return at most ${MAX_MODULES} modules where better docs would most help a newcomer, best first.`,
  { label: 'audit-docs', phase: 'Audit', schema: AUDIT_SCHEMA },
);

const targets = (audit.modules || []).slice(0, MAX_MODULES);
log(`Found ${targets.length} module(s) with doc gaps${SCOPE ? ` in ${SCOPE}` : ''}.`);
if (!targets.length) return { scope: SCOPE || 'repo', documented: [], note: 'No significant doc gaps found.' };

// Each module documented independently, in its own worktree to avoid parallel-edit collisions.
const results = await pipeline(
  targets,
  (t) => agent(
    `Add clear Google-style docstrings to the public symbols in \`${t.module_path}\` (gaps: ${(t.gaps || []).join(', ')}). ` +
    `Audience: ${t.audience || 'contributor'}.\n` +
    `Rules: edit ONLY docstrings/comments — do NOT change code, signatures, or behavior. ` +
    `Describe args, returns, raises, and any non-obvious invariants (e.g. HIHO coherence semantics). Keep it accurate to the code you read; do not invent behavior. ` +
    `Use the Edit tool in place, then return a one-paragraph plain-language summary of the module.`,
    { label: `doc:${t.module_path}`, phase: 'Document', schema: DOC_RESULT_SCHEMA, isolation: 'worktree' },
  ),
);

const documented = results.filter(Boolean);

phase('Index');
const indexPage = await agent(
  `Assemble a concise Markdown module-reference section from these per-module summaries. ` +
  `One subsection per module: heading = import path, body = the summary + the documented symbols as a bullet list. ` +
  `This is meant to drop into docs/ as a reference page. Summaries JSON:\n${JSON.stringify(documented, null, 2)}`,
  { label: 'index', phase: 'Index' },
);

return {
  scope: SCOPE || 'repo',
  attempted: targets.length,
  documented,
  referencePage: indexPage,
  note: 'Docstrings were edited in isolated worktrees (review each diff before merging). The reference page is returned as text — save it under docs/ if useful.',
};
