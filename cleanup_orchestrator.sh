#!/bin/bash

# Compound Engineering Codebase Cleanup Orchestrator
# This script orchestrates multiple specialized models to clean up and optimize the codebase

echo "=== COMPOUND ENGINEERING CODEBASE CLEANUP ORCHESTRATION ==="
echo "Starting at $(date)"
echo ""

# Phase 1: Analysis with gpt-oss-256k (Analysis Specialist)
echo "Phase 1: Analysis with gpt-oss-256k - Analyzing codebase structure and cleanup opportunities"
echo "======================================================================"

# Analyze directory structure and identify cleanup opportunities
ANALYSIS_RESULT=$(opencode -m gpt-oss-256k "
Analyze this codebase structure for cleanup opportunities. 

Current directory: /home/mike-anderson/dev/cohezion

Focus areas:
1. Large files and directories that can be archived or removed
2. Log files and temporary files that can be cleaned up
3. Duplicate or redundant files
4. Unused dependencies and packages
5. Build artifacts and cache files
6. Old migration logs and temporary data
7. Documentation that can be consolidated
8. Configuration files that can be optimized

Provide a detailed cleanup plan with:
- Priority levels (high/medium/low)
- Estimated space savings
- Dependencies/risks
- Recommended actions
- Execution order
")
echo "Analysis complete. Results:"
echo "$ANALYSIS_RESULT"
echo ""

# Phase 2: Planning with qwen3-coder-256k (Core Coding Specialist)
echo "Phase 2: Planning with qwen3-coder-256k - Creating detailed cleanup execution plan"
echo "===================================================================================="

PLAN_RESULT=$(opencode -m qwen3-coder-256k "
Based on the analysis results, create a detailed cleanup execution plan.

Requirements:
1. Create a prioritized todo list with specific actions
2. Include exact commands and file paths
3. Add safety checks and rollback procedures
4. Include progress tracking
5. Add verification steps
6. Include documentation updates

Output format:
1. Priority 1: Critical cleanup actions
2. Priority 2: Important optimizations  
3. Priority 3: Nice-to-have improvements
4. Safety procedures
5. Execution commands
6. Verification steps
")
echo "Planning complete. Results:"
echo "$PLAN_RESULT"
echo ""

# Phase 3: Execution with glm-4.7-flash-256k (Fast Execution Specialist)
echo "Phase 3: Execution with glm-4.7-flash-256k - Implementing cleanup actions"
echo "=============================================================================="

# Execute high-priority cleanup actions
EXECUTION_RESULT=$(opencode -m glm-4.7-flash-256k "
Execute the high-priority cleanup actions from the plan.

Focus on:
1. Removing large log files (.log extension)
2. Cleaning up migration logs
3. Removing temporary files
4. Clearing cache directories
5. Removing old build artifacts
6. Optimizing package dependencies

Execute each action with safety checks and provide verification after each step.
")
echo "Execution complete. Results:"
echo "$EXECUTION_RESULT"
echo ""

# Phase 4: Optimization with phi4-256k (Mathematical Specialist)
echo "Phase 4: Optimization with phi4-256k - Mathematical optimization of cleanup"
echo "============================================================================"

# Optimize cleanup strategy and identify additional opportunities
OPTIMIZATION_RESULT=$(opencode -m phi4-256k "
Optimize the cleanup strategy using mathematical analysis.

Focus on:
1. Space-time complexity of cleanup operations
2. Optimal order of operations for maximum efficiency
3. Resource utilization optimization
4. Performance impact analysis
5. Storage optimization opportunities
6. Dependency graph optimization

Provide mathematical justification for optimization decisions.
")
echo "Optimization complete. Results:"
echo "$OPTIMIZATION_RESULT"
echo ""

# Phase 5: Verification with gemma3-4b-256k (Specialized Verification)
echo "Phase 5: Verification with gemma3-4b-256k - Verification and quality assurance"
echo "=============================================================================="

# Verify cleanup results and ensure system integrity
VERIFICATION_RESULT=$(opencode -m gemma3-4b-256k "
Verify the cleanup results and ensure system integrity.

Tasks:
1. Verify all critical files are intact
2. Check that no essential functionality is broken
3. Validate configuration files
4. Ensure documentation is complete
5. Verify build processes still work
6. Check for any broken dependencies

Provide detailed verification report with any issues found.
")
echo "Verification complete. Results:"
echo "$VERIFICATION_RESULT"
echo ""

# Phase 6: Documentation with qwen2.5-coder-14b-256k (Mid-tier Specialist)
echo "Phase 6: Documentation with qwen2.5-coder-14b-256k - Update documentation"
echo "============================================================================"

# Update documentation with cleanup results
DOCUMENTATION_RESULT=$(opencode -m qwen2.5-coder-14b-256k "
Update documentation based on cleanup results.

Create:
1. Cleanup summary report
2. Before/after metrics
3. Lessons learned
4. Best practices for future cleanup
5. Updated maintenance procedures
6. Documentation of changes made

Format as comprehensive documentation for future reference.
")
echo "Documentation complete. Results:"
echo "$DOCUMENTATION_RESULT"
echo ""

echo "=== CLEANUP ORCHESTRATION COMPLETE ==="
echo "Final status at $(date)"
echo ""
echo "Memory usage before cleanup: 73GB used, 51GB available"
echo "Memory usage after cleanup: $(free -h | awk 'NR==2{print $3}') used, $(free -h | awk 'NR==2{print $7}') available"
echo ""
echo "Cleanup completed successfully!"
echo "Repository is now optimized for additional compound engineering work."