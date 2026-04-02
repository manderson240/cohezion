#!/usr/bin/env node
/**
 * Coherence Guard - Automated toFixed Null Check Fixer
 * 
 * Scans all TypeScript files for unsafe .toFixed() calls
 * and adds null coalescing operators automatically.
 */

const fs = require('fs');
const path = require('path');

const TARGET_DIRS = [
  'apps/webapp/src',
  'apps/morphospace-loom/src',
  'src/web/anima_dashboard/src',
  '.pi/extensions'
];

const EXCLUDE_PATTERNS = [
  /node_modules/,
  /\.venv/,
  /\.git/,
  /dist/,
  /build/
];

// Patterns to fix
const FIX_PATTERNS = [
  {
    name: 'coherence without null check',
    regex: /(?<![?\?\)\]]\s*)\.coherence\.toFixed/g,
    replacement: '.coherence ?? 0).toFixed',
    requiresParens: true
  },
  {
    name: 'entropy without null check', 
    regex: /(?<![?\?\)\]]\s*)\.entropy\.toFixed/g,
    replacement: '.entropy ?? 0).toFixed',
    requiresParens: true
  },
  {
    name: 'variable.toFixed without null check',
    regex: /\{([a-zA-Z_][a-zA-Z0-9_]*)\.toFixed\(/g,
    replacement: '{$1 ?? 0).toFixed(',
    requiresParens: true
  },
  {
    name: 'direct value toFixed',
    regex: /\{value\.toFixed\(/g,
    replacement: '{(value ?? 0).toFixed(',
    requiresParens: false
  }
];

let filesFixed = 0;
let totalIssues = 0;

function shouldProcess(file) {
  return file.endsWith('.ts') || file.endsWith('.tsx');
}

function scanDirectory(dir) {
  const results = [];
  
  function scan(currentPath) {
    if (EXCLUDE_PATTERNS.some(p => p.test(currentPath))) return;
    
    const stat = fs.statSync(currentPath);
    if (stat.isDirectory()) {
      const entries = fs.readdirSync(currentPath);
      for (const entry of entries) {
        scan(path.join(currentPath, entry));
      }
    } else if (shouldProcess(currentPath)) {
      results.push(currentPath);
    }
  }
  
  scan(dir);
  return results;
}

function fixFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf-8');
  let originalContent = content;
  let fileIssues = 0;
  
  // Quick check for any unsafe toFixed
  if (!content.includes('.toFixed(')) return;
  
  // Skip files that already have proper null checks
  const safePatterns = [
    /\?\?\s*0\)\s*\.toFixed/,  // (x ?? 0).toFixed
    /\?\.toFixed\(/,            // x?.toFixed(
    /coherenceVal/,              // already fixed variable
  ];
  
  // Specific fixes for common patterns
  const replacements = [
    // Pattern: object.coherence.toFixed -> (object.coherence ?? 0).toFixed
    {
      from: /(\w+)\.coherence\.toFixed\(/g,
      to: '($1.coherence ?? 0).toFixed('
    },
    // Pattern: object.entropy.toFixed -> (object.entropy ?? 0).toFixed
    {
      from: /(\w+)\.entropy\.toFixed\(/g,
      to: '($1.entropy ?? 0).toFixed('
    },
    // Pattern: object.stability.toFixed -> (object.stability ?? 0).toFixed
    {
      from: /(\w+)\.stability\.toFixed\(/g,
      to: '($1.stability ?? 0).toFixed('
    },
    // Pattern: {value.toFixed -> {(value ?? 0).toFixed
    {
      from: /\{value\.toFixed\(/g,
      to: '{(value ?? 0).toFixed('
    },
    // Pattern: {d1.toFixed -> {(d1 ?? 0).toFixed
    {
      from: /\{d1\.toFixed\(/g,
      to: '{(d1 ?? 0).toFixed('
    },
    // Pattern: {d12.toFixed -> {(d12 ?? 0).toFixed
    {
      from: /\{d12\.toFixed\(/g,
      to: '{(d12 ?? 0).toFixed('
    },
    // Pattern: evo.property.toFixed -> (evo.property ?? 0).toFixed
    {
      from: /evo\.(charge_density|magnetic_helicity|toroidal_moment|coherence)\.toFixed\(/g,
      to: '(evo.$1 ?? 0).toFixed('
    },
    // Pattern: displayData.property.toFixed -> (displayData.property ?? 0).toFixed
    {
      from: /displayData\.(coherence|entropy)\.toFixed\(/g,
      to: '(displayData.$1 ?? 0).toFixed('
    },
    // Pattern: topology.entropy.toFixed -> (topology.entropy ?? 0).toFixed
    {
      from: /topology\.entropy\.toFixed\(/g,
      to: '(topology.entropy ?? 0).toFixed('
    },
    // Pattern: state.property.toFixed -> (state.property ?? 0).toFixed
    {
      from: /state\.(coherence|tick)\.toFixed\(/g,
      to: '(state.$1 ?? 0).toFixed('
    },
    // Pattern: data.coherence.toFixed -> (data.coherence ?? 0).toFixed
    {
      from: /data\.coherence\.toFixed\(/g,
      to: '(data.coherence ?? 0).toFixed('
    },
    // Pattern: p.coherence.toFixed -> (p.coherence ?? 0).toFixed
    {
      from: /p\.coherence\.toFixed\(/g,
      to: '(p.coherence ?? 0).toFixed('
    },
    // Pattern: latestPoint.coherence.toFixed -> latestPoint.coherence?.toFixed
    {
      from: /latestPoint\.coherence\.toFixed\(/g,
      to: 'latestPoint.coherence?.toFixed('
    }
  ];
  
  for (const { from, to } of replacements) {
    const matches = content.match(from);
    if (matches) {
      content = content.replace(from, to);
      fileIssues += matches.length;
    }
  }
  
  if (content !== originalContent) {
    fs.writeFileSync(filePath, content, 'utf-8');
    filesFixed++;
    console.log(`  ✓ Fixed ${fileIssues} issues in ${path.relative(process.cwd(), filePath)}`);
  }
  
  totalIssues += fileIssues;
}

function main() {
  console.log('🔧 Coherence Guard: Fixing toFixed null checks\n');
  
  const baseDir = process.cwd();
  
  for (const targetDir of TARGET_DIRS) {
    const fullPath = path.join(baseDir, targetDir);
    if (!fs.existsSync(fullPath)) {
      console.log(`⚠ Skipping ${targetDir} (not found)`);
      continue;
    }
    
    console.log(`📁 Scanning ${targetDir}...`);
    const files = scanDirectory(fullPath);
    
    for (const file of files) {
      fixFile(file);
    }
  }
  
  console.log(`\n✅ Complete: Fixed ${totalIssues} issues in ${filesFixed} files`);
  
  if (totalIssues > 0) {
    console.log('\n💡 Run "git diff" to review changes, then commit.');
  }
}

main();
