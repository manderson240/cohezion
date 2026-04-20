#!/usr/bin/env node
/**
 * ERROR-FIXER AGENT - Specialized for toFixed errors
 * This is a DIFFERENT subagent from the previous fix attempts
 */

const fs = require('fs');
const path = require('path');

console.log('🔧 ERROR-FIXER AGENT: Starting comprehensive repair...');

const TARGET_DIRS = [
  'apps',
  'src/web',
  '.pi/extensions'
];

const REPLACEMENTS = [
  // Pattern: object.property.toFixed(n) -> (object.property ?? 0).toFixed(n)
  { from: /(\w+)\.(coherence|entropy|tick|stability)\s*\.toFixed\(/g, to: '($1.$2 ?? 0).toFixed(' },
  // Pattern: nested.property.toFixed
  { from: /(\w+\.\w+)\.(coherence|entropy|tick|stability)\s*\.toFixed\(/g, to: '($1.$2 ?? 0).toFixed(' },
  // Pattern: object.property?.toFixed(n) - ensure it's safe
  { from: /(\w+)\.(coherence|entropy|tick|stability)\?\.toFixed\(/g, to: '($1.$2 ?? 0).toFixed(' },
  // Pattern: standalone variable.toFixed
  { from: /\{(coherence|entropy|tick|stability)\s*\.toFixed\(/g, to: '{($1 ?? 0).toFixed(' },
  // Pattern: evo.property.toFixed
  { from: /evo\.(charge_density|magnetic_helicity|toroidal_moment|coherence)\s*\.toFixed\(/g, to: '(evo.$1 ?? 0).toFixed(' },
  // Pattern: displayData.property.toFixed
  { from: /displayData\.(coherence|entropy|tick|stability)\s*\.toFixed\(/g, to: '(displayData.$1 ?? 0).toFixed(' },
  // Pattern: result.property.toFixed
  { from: /result\.(coherence|entropy|hiho_score)\s*\.toFixed\(/g, to: '(result.$1 ?? 0).toFixed(' },
  // Pattern: state.property.toFixed
  { from: /state\.(coherence|entropy|tick|stability)\s*\.toFixed\(/g, to: '(state.$1 ?? 0).toFixed(' },
  // Pattern: data.property.toFixed
  { from: /data\.(coherence|entropy|hiho_score)\s*\.toFixed\(/g, to: '(data.$1 ?? 0).toFixed(' },
  // Pattern: p.property.toFixed
  { from: /p\.(coherence|entropy|efficiency)\s*\.toFixed\(/g, to: '(p.$1 ?? 0).toFixed(' },
  // Pattern: node.property.toFixed
  { from: /node\.(coherence|connectivity|cross_domain)\s*\.toFixed\(/g, to: '(node.$1 ?? 0).toFixed(' },
  // Pattern: v => v.toFixed
  { from: /v\s*=>\s*v\.toFixed\(/g, to: 'v => (v ?? 0).toFixed(' },
];

let totalFixed = 0;
let filesFixed = 0;

function scanDir(dir) {
  if (!fs.existsSync(dir)) return [];
  const results = [];
  
  function scan(current) {
    if (!fs.existsSync(current)) return;
    const stat = fs.statSync(current);
    if (stat.isDirectory()) {
      if (current.includes('node_modules') || current.includes('.venv')) return;
      const entries = fs.readdirSync(current);
      for (const entry of entries) {
        scan(path.join(current, entry));
      }
    } else if (current.endsWith('.ts') || current.endsWith('.tsx')) {
      results.push(current);
    }
  }
  
  scan(dir);
  return results;
}

function fixFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf-8');
  let original = content;
  let fixes = 0;
  
  for (const { from, to } of REPLACEMENTS) {
    const matches = content.match(from);
    if (matches) {
      content = content.replace(from, to);
      fixes += matches.length;
    }
  }
  
  if (fixes > 0 && content !== original) {
    fs.writeFileSync(filePath, content, 'utf-8');
    totalFixed += fixes;
    filesFixed++;
    console.log(`  ✓ Fixed ${fixes} issues in ${path.basename(filePath)}`);
  }
}

console.log('\n📁 Scanning all TypeScript files...\n');

for (const target of TARGET_DIRS) {
  const fullPath = path.join(process.cwd(), target);
  if (fs.existsSync(fullPath)) {
    const files = scanDir(fullPath);
    for (const file of files) {
      fixFile(file);
    }
  }
}

console.log(`\n✅ ERROR-FIXER AGENT COMPLETE`);
console.log(`   Fixed: ${totalFixed} unsafe .toFixed() calls`);
console.log(`   Files: ${filesFixed} modified`);

if (totalFixed > 0) {
  console.log(`\n💡 NEXT STEPS:`);
  console.log(`   1. Run: git add -A && git commit -m "fix: ERROR-FIXER AGENT toFixed repairs"`);
  console.log(`   2. Restart application to apply fixes`);
  process.exit(1); // Signal that fixes were made
} else {
  console.log(`\n✅ No unsafe .toFixed() calls found`);
  process.exit(0);
}
