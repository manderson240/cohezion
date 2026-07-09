export const meta = {
  name: 'compound',
  description: 'Compound-engineering meta-workflow: review the diff, harden the riskiest area with tests, document it, then retrospect on how to improve the collaborators themselves',
  whenToUse: 'After a substantial change, when you want the full compound loop in one shot. Chains review -> cover -> docs over the affected subpackage and produces a combined report plus a retrospection that proposes improvements to the review/cover/docs workflows. Heavy: it runs three sub-workflows, so opt in deliberately.',
  phases: [
    { title: 'Review', detail: 'run the review workflow over the diff' },
    { title: 'Harden', detail: 'run cover on the most-affected subpackage' },
    { title: 'Document', detail: 'run docs on the most-affected subpackage' },
    { title: 'Retrospect', detail: 'synthesize + propose collaborator improvements' },
  ],
};

// args: optional base ref to diff against (default "origin/main").
const BASE = (typeof args === 'string' && args.trim()) ? args.trim() : 'origin/main';

// --- Review -------------------------------------------------------------
phase('Review');
let review;
try {
  review = await workflow('review', BASE);
} catch (e) {
  review = { findings: [], report: 'review workflow unavailable: ' + (e && e.message) };
}
const findings = review.findings || [];
log(`Review surfaced ${findings.length} confirmed finding(s).`);

// Derive the most-affected subpackage from finding file paths: src/cohezion/<pkg>/...
function pkgOf(file) {
  const m = /src\/cohezion\/([^/]+)\//.exec(file || '');
  return m ? m[1] : null;
}
const pkgCounts = {};
for (const f of findings) {
  const p = pkgOf(f.file);
  if (p) pkgCounts[p] = (pkgCounts[p] || 0) + 1;
}
const topPkg = Object.keys(pkgCounts).sort((a, b) => pkgCounts[b] - pkgCounts[a])[0] || null;

// --- Harden + Document (only if we identified a target) -----------------
// Both edit files in isolated worktrees, so they can run concurrently.
let cover = null;
let docsResult = null;
if (topPkg) {
  log(`Most-affected subpackage: ${topPkg} (${pkgCounts[topPkg]} finding(s)). Hardening + documenting it.`);
  phase('Harden');
  [cover, docsResult] = await parallel([
    () => workflow('cover', topPkg).catch((e) => ({ error: String(e && e.message) })),
    () => workflow('docs', topPkg).catch((e) => ({ error: String(e && e.message) })),
  ]);
} else {
  log('No src/cohezion subpackage implicated by review findings — skipping harden/document.');
}

// --- Retrospect (the compounding step) ----------------------------------
phase('Retrospect');
const retrospective = await agent(
  'You are the compound-engineering retrospector closing the loop on a change. ' +
  'Using the three collaborator outputs below, produce Markdown with exactly these sections:\n' +
  '1. **Summary** — 3-5 lines on the change\'s health (what review found, what was hardened/documented).\n' +
  '2. **Open risks** — anything still unresolved a maintainer must look at.\n' +
  '3. **Compounding improvements** — 2-3 concrete, specific upgrades to the review/cover/docs workflows ' +
  'themselves that would have caught more or done better next time (this is what makes the loop compound). ' +
  'Be honest; if a sub-workflow was skipped or errored, say so.\n\n' +
  `REVIEW REPORT:\n${review.report || '(none)'}\n\n` +
  `COVER RESULT:\n${JSON.stringify(cover, null, 2)}\n\n` +
  `DOCS RESULT:\n${docsResult ? (docsResult.referencePage || JSON.stringify(docsResult)) : '(skipped)'}`,
  { label: 'retrospect', phase: 'Retrospect' },
);

return {
  base: BASE,
  review_findings: findings.length,
  hardened_pkg: topPkg,
  cover,
  docs: docsResult,
  retrospective,
  note: 'Compound loop complete. cover/docs edited files in isolated worktrees — review those diffs before merging. The retrospective proposes how to improve the collaborators next round.',
};
