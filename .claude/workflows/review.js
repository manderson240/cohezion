export const meta = {
  name: 'review',
  description: 'Multi-dimension code review of the current diff with adversarial verification',
  whenToUse: 'Before opening a PR, or to review the changes on the current branch. Fans out one reviewer per dimension (correctness, security, performance, simplification, tests), then adversarially verifies each finding so only real issues survive.',
  phases: [
    { title: 'Scan', detail: 'collect the changed files + diff vs the base ref' },
    { title: 'Review', detail: 'one reviewer per dimension over the diff' },
    { title: 'Verify', detail: 'adversarially refute each finding (majority vote)' },
    { title: 'Synthesize', detail: 'compile the surviving findings into a report' },
  ],
};

// args: optional base ref to diff against (default "origin/main").
const BASE = (typeof args === 'string' && args.trim()) ? args.trim() : 'origin/main';

const FINDINGS_SCHEMA = {
  type: 'object',
  required: ['findings'],
  properties: {
    findings: {
      type: 'array',
      items: {
        type: 'object',
        required: ['title', 'file', 'severity', 'detail'],
        properties: {
          title: { type: 'string' },
          file: { type: 'string', description: 'path:line when known' },
          severity: { type: 'string', enum: ['critical', 'high', 'medium', 'low'] },
          detail: { type: 'string', description: 'what is wrong and why it matters' },
          suggestion: { type: 'string', description: 'concrete fix' },
        },
      },
    },
  },
};

const VERDICT_SCHEMA = {
  type: 'object',
  required: ['real', 'reason'],
  properties: {
    real: { type: 'boolean', description: 'true only if this is a genuine issue worth fixing' },
    reason: { type: 'string' },
  },
};

const DIMENSIONS = [
  { key: 'correctness', prompt: 'logic bugs, off-by-one, wrong async/await, unhandled None/error paths, broken invariants (esp. HIHO coherence semantics)' },
  { key: 'security', prompt: 'injection, unsafe subprocess/eval, secret leakage, bare-except swallowing, unsafe deserialization' },
  { key: 'performance', prompt: 'needless O(n^2), blocking I/O in async paths, repeated work that should be cached, large allocations' },
  { key: 'simplification', prompt: 'duplicated logic (DRY), dead code, over-abstraction, functions that do >1 thing, clearer equivalents' },
  { key: 'tests', prompt: 'changed behavior lacking a test, missing edge cases (empty/zero/negative/max), assertions that do not actually check the new behavior' },
];

phase('Scan');
const scan = await agent(
  `Run \`git --no-pager diff --stat ${BASE}...HEAD\` and \`git --no-pager diff ${BASE}...HEAD\` to see the changes on this branch. ` +
  `Summarize the changed files and the substance of the diff so reviewers can focus. ` +
  `If the diff is empty, say so explicitly.`,
  { label: 'scan-diff', phase: 'Scan' },
);
log(`Scanned diff vs ${BASE}.`);

// Pipeline: each dimension reviews, then its findings are verified as soon as they land.
const reviewed = await pipeline(
  DIMENSIONS,
  (d) => agent(
    `You are reviewing the changes on this branch (diff vs ${BASE}). Focus ONLY on: ${d.prompt}.\n\n` +
    `Diff context from the scout:\n${scan}\n\n` +
    `Re-run \`git --no-pager diff ${BASE}...HEAD\` yourself if you need exact lines. ` +
    `Report concrete, file:line-anchored findings. Be terse; do not invent issues.`,
    { label: `review:${d.key}`, phase: 'Review', schema: FINDINGS_SCHEMA, agentType: 'code-reviewer' },
  ),
  (review, d) => parallel(
    (review.findings || []).map((f) => () =>
      agent(
        `Adversarially verify this ${d.key} finding. Default to real=false unless you can confirm it from the actual code.\n\n` +
        `Finding: ${f.title}\nFile: ${f.file}\nClaim: ${f.detail}\n\n` +
        `Open the file and check. A finding is only "real" if a competent maintainer would fix it.`,
        { label: `verify:${f.file}`, phase: 'Verify', schema: VERDICT_SCHEMA },
      ).then((v) => ({ ...f, dimension: d.key, verdict: v }))
    ),
  ),
);

const confirmed = reviewed.flat().filter(Boolean).filter((f) => f.verdict && f.verdict.real);

phase('Synthesize');
const order = { critical: 0, high: 1, medium: 2, low: 3 };
confirmed.sort((a, b) => (order[a.severity] ?? 9) - (order[b.severity] ?? 9));

const report = await agent(
  `Write a concise PR-review report in Markdown from these verified findings (already confirmed real). ` +
  `Group by severity, keep each item to file:line + one-line problem + one-line fix. ` +
  `If empty, say the diff looks clean. Findings JSON:\n${JSON.stringify(confirmed, null, 2)}`,
  { label: 'synthesize', phase: 'Synthesize' },
);

return { base: BASE, confirmedCount: confirmed.length, findings: confirmed, report };
