/**
 * Demo Script for Phase 4 Universe Simulation Features
 *
 * Demonstrates all three simulation components:
 * 1. DecisionForkSimulator - "What if we chose Alternative 2?"
 * 2. TaskOptimizer - Optimal task-to-agent assignments
 * 3. KnowledgeGapExplorer - Hypothetical paper impact analysis
 */

import { DecisionForkSimulator } from './DecisionForkSimulator';
import { TaskOptimizer } from './TaskOptimizer';
import { KnowledgeGapExplorer } from './GapExplorer';

// ============================================================================
// DEMO 1: DECISION FORK SIMULATOR
// ============================================================================

async function demoDecisionForkSimulator() {
  console.log('=== DEMO 1: DECISION FORK SIMULATOR ===\n');

  // Load graph data (from .obsidian/3d-graph-data.json)
  const graphData = await loadGraphData();

  // Initialize simulator
  const simulator = new DecisionForkSimulator(graphData);

  // Example: Simulate alternative for "12D Graph Refined Plan"
  const decisionId = '2026-02-09-12d-graph-refined-plan';
  const alternativeIndex = 1; // Alternative 2

  console.log(`Simulating alternative decision for: ${decisionId}`);
  console.log(`Alternative index: ${alternativeIndex}\n`);

  try {
    const simulatedUniverse = await simulator.simulateFork(decisionId, alternativeIndex);

    console.log('SIMULATED UNIVERSE RESULTS:');
    console.log(`Alternative: ${simulatedUniverse.alternative_name}`);
    console.log(`Description: ${simulatedUniverse.alternative_description}\n`);

    console.log('HYPOTHETICAL ARTIFACTS:');
    console.log(`  Papers: ${simulatedUniverse.hypothetical_papers.length}`);
    console.log(`  Patterns: ${simulatedUniverse.hypothetical_patterns.length}\n`);

    console.log('MODIFIED EDGES:');
    console.log(`  Added: ${simulatedUniverse.modified_edges.filter(e => e.edge_type === 'added').length}`);
    console.log(`  Removed: ${simulatedUniverse.modified_edges.filter(e => e.edge_type === 'removed').length}\n`);

    console.log('IMPACT METRICS:');
    console.log(`  Patterns Affected: ${simulatedUniverse.impact.patterns_affected}`);
    console.log(`  Papers Affected: ${simulatedUniverse.impact.papers_affected}`);
    console.log(`  Token Cost Delta: ${simulatedUniverse.impact.token_cost_delta > 0 ? '+' : ''}${simulatedUniverse.impact.token_cost_delta}`);
    console.log(`  Time Delta (hours): ${simulatedUniverse.impact.time_delta_hours > 0 ? '+' : ''}${simulatedUniverse.impact.time_delta_hours}`);
    console.log(`  Cross-Domain Connectivity Delta: ${simulatedUniverse.impact.cross_domain_connectivity_delta > 0 ? '+' : ''}${simulatedUniverse.impact.cross_domain_connectivity_delta}`);
    console.log(`  Knowledge Gaps: ${simulatedUniverse.impact.knowledge_gap_changes.join(', ')}\n`);

    // Generate comparison view
    console.log('Generating side-by-side comparison view...');
    const comparisonView = await simulator.generateComparisonView(decisionId, alternativeIndex);

    console.log('COMPARISON VIEW:');
    console.log(`  Nodes Added: ${comparisonView.diff_summary.nodes_added}`);
    console.log(`  Edges Added: ${comparisonView.diff_summary.edges_added}`);
    console.log(`  Edges Removed: ${comparisonView.diff_summary.edges_removed}`);
    console.log(`  Token Cost Delta: $${comparisonView.diff_summary.quantified_metrics.token_cost_delta.toFixed(2)}`);
    console.log(`  Time Delta: ${comparisonView.diff_summary.quantified_metrics.time_delta_hours.toFixed(1)} hours\n`);
  } catch (error) {
    console.error('Demo failed:', error);
  }
}

// ============================================================================
// DEMO 2: TASK OPTIMIZER
// ============================================================================

async function demoTaskOptimizer() {
  console.log('\n=== DEMO 2: TASK OPTIMIZER ===\n');

  // Initialize optimizer
  const optimizer = new TaskOptimizer();

  // Define optimization constraints
  const constraints = {
    time_weight: 0.7, // Prioritize speed
    cost_weight: 0.3, // Lower priority on cost
    max_parallel_agents: 4,
    available_agents: [
      {
        name: 'haiku',
        cost_per_1k_tokens: 0.001,
        avg_tokens_per_task: 2000,
        avg_completion_time_minutes: 5,
        success_rate: 0.95,
      },
      {
        name: 'sonnet',
        cost_per_1k_tokens: 0.003,
        avg_tokens_per_task: 5000,
        avg_completion_time_minutes: 15,
        success_rate: 0.98,
      },
      {
        name: 'opus',
        cost_per_1k_tokens: 0.015,
        avg_tokens_per_task: 8000,
        avg_completion_time_minutes: 30,
        success_rate: 0.99,
      },
      {
        name: 'local-llm',
        cost_per_1k_tokens: 0.0,
        avg_tokens_per_task: 3000,
        avg_completion_time_minutes: 10,
        success_rate: 0.90,
      },
    ],
  };

  const tasksDir = '/home/mike-anderson/.claude/tasks/12d-graph-implementation';
  const historyFile = '/home/mike-anderson/.claude/history.jsonl';

  try {
    console.log('Analyzing task dependency DAG...');
    console.log('Loading historical agent performance...\n');

    const optimalPlan = await optimizer.optimize(tasksDir, historyFile, constraints);

    console.log('OPTIMAL EXECUTION PLAN:');
    console.log(`  Total Cost: $${optimalPlan.total_cost.toFixed(2)}`);
    console.log(`  Total Time: ${optimalPlan.total_time_minutes.toFixed(0)} minutes (${(optimalPlan.total_time_minutes / 60).toFixed(1)} hours)`);
    console.log(`  Total Tokens: ${optimalPlan.total_tokens.toLocaleString()}`);
    console.log(`  Parallelism Score: ${(optimalPlan.parallelism_score * 100).toFixed(0)}%\n`);

    console.log('TASK ASSIGNMENTS:');
    for (const assignment of optimalPlan.assignments.slice(0, 5)) {
      console.log(`  Task: ${assignment.task_id}`);
      console.log(`    Agent: ${assignment.agent_name}`);
      console.log(`    Estimated Time: ${assignment.estimated_time_minutes.toFixed(0)} min`);
      console.log(`    Estimated Cost: $${assignment.estimated_cost.toFixed(3)}`);
      console.log(`    Confidence: ${(assignment.confidence * 100).toFixed(0)}%\n`);
    }
    if (optimalPlan.assignments.length > 5) {
      console.log(`  ... and ${optimalPlan.assignments.length - 5} more tasks\n`);
    }

    console.log('GANTT CHART DATA:');
    console.log(`  Makespan: ${optimalPlan.gantt_chart_data.makespan_minutes.toFixed(0)} minutes`);
    console.log(`  Critical Path Length: ${optimalPlan.gantt_chart_data.critical_path.length} tasks`);
    console.log(`  Critical Path: ${optimalPlan.gantt_chart_data.critical_path.slice(0, 3).join(' → ')}...\n`);

    // Simulate actual vs optimal comparison
    console.log('Simulating actual vs optimal comparison...');

    // Create a mock "actual" plan (less optimal)
    const actualPlan = {
      ...optimalPlan,
      total_cost: optimalPlan.total_cost * 1.5, // 50% more expensive
      total_time_minutes: optimalPlan.total_time_minutes * 1.3, // 30% slower
      total_tokens: optimalPlan.total_tokens * 1.4, // 40% more tokens
      parallelism_score: optimalPlan.parallelism_score * 0.7, // 30% less parallel
      gantt_chart_data: {
        ...optimalPlan.gantt_chart_data,
        makespan_minutes: optimalPlan.gantt_chart_data.makespan_minutes * 1.3,
        critical_path: [...optimalPlan.gantt_chart_data.critical_path, 'extra-task-1', 'extra-task-2'],
      },
    };

    const comparison = await optimizer.compareActualVsOptimal(actualPlan, optimalPlan);

    console.log('ACTUAL VS OPTIMAL:');
    console.log(`  Time Saved: ${comparison.savings.time_minutes.toFixed(0)} minutes (${(comparison.savings.time_minutes / 60).toFixed(1)} hours)`);
    console.log(`  Cost Saved: $${comparison.savings.cost_usd.toFixed(2)}`);
    console.log(`  Tokens Saved: ${comparison.savings.tokens.toLocaleString()}\n`);

    console.log('RECOMMENDATIONS:');
    for (const recommendation of comparison.recommendations) {
      console.log(`  • ${recommendation}`);
    }
    console.log();
  } catch (error) {
    console.error('Demo failed:', error);
  }
}

// ============================================================================
// DEMO 3: KNOWLEDGE GAP EXPLORER
// ============================================================================

async function demoKnowledgeGapExplorer() {
  console.log('\n=== DEMO 3: KNOWLEDGE GAP EXPLORER ===\n');

  // Load graph data
  const graphData = await loadGraphData();

  // Initialize explorer
  const explorer = new KnowledgeGapExplorer(graphData);

  // Example hypothetical paper
  const hypothetical = {
    title: 'Quantum-Enhanced Multi-Agent Systems for Real-Time Decision Making',
    abstract:
      'This paper explores the intersection of quantum computing and multi-agent AI systems. ' +
      'We propose a novel architecture where quantum superposition enables agents to explore ' +
      'multiple decision paths simultaneously, achieving exponential speedup in collaborative ' +
      'problem-solving tasks. Applications include financial trading, autonomous vehicle ' +
      'coordination, and distributed sensor networks.',
    tags: ['quantum-computing', 'multi-agent', 'ai'],
  };

  try {
    console.log('Exploring hypothetical paper:');
    console.log(`  Title: ${hypothetical.title}`);
    console.log(`  Abstract: ${hypothetical.abstract.substring(0, 100)}...\n`);

    const result = await explorer.explorePaper(hypothetical);

    console.log('GHOST NODE:');
    console.log(`  ID: ${result.ghost_node.id}`);
    console.log(`  Predicted Position: (${result.ghost_node.predicted_position.x.toFixed(2)}, ${result.ghost_node.predicted_position.y.toFixed(2)}, ${result.ghost_node.predicted_position.z.toFixed(2)})`);
    console.log(`  Confidence: ${(result.ghost_node.confidence * 100).toFixed(0)}%`);
    console.log(`  Predicted Tags: ${result.ghost_node.predicted_tags.join(', ')}\n`);

    console.log('NEAREST NEIGHBORS:');
    for (const neighbor of result.ghost_node.nearest_neighbors.slice(0, 5)) {
      console.log(`  • ${neighbor.label} (similarity: ${(neighbor.similarity * 100).toFixed(0)}%)`);
    }
    console.log();

    console.log('IMPACT METRICS:');
    console.log(`  Cross-Domain Connections Added: ${result.impact.cross_domain_connections_added}`);
    console.log(`  Orphaned Papers Connected: ${result.impact.orphaned_papers_connected}`);
    console.log(`  Knowledge Density Improvement: ${(result.impact.knowledge_density_improvement * 100).toFixed(2)}%`);
    console.log(`  Cluster Bridging Score: ${(result.impact.cluster_bridging_score * 100).toFixed(0)}%`);
    console.log(`  New Research Directions: ${result.impact.new_research_directions.slice(0, 3).join(', ')}...\n`);

    // Explore multiple scenarios
    console.log('Exploring scenario with multiple hypothetical papers...');

    const scenario = await explorer.exploreScenario('Quantum AI Research Expansion', [
      hypothetical,
      {
        title: 'Quantum Machine Learning for Agent Coordination',
        abstract: 'Applying quantum ML algorithms to optimize multi-agent coordination protocols.',
        tags: ['quantum-computing', 'machine-learning', 'multi-agent'],
      },
      {
        title: 'Distributed Quantum Computing Infrastructure for AI',
        abstract: 'Designing distributed quantum computing clusters for large-scale AI workloads.',
        tags: ['quantum-computing', 'infrastructure', 'distributed-systems'],
      },
    ]);

    console.log('SCENARIO RESULTS:');
    console.log(`  Scenario Name: ${scenario.scenario_name}`);
    console.log(`  Hypothetical Papers: ${scenario.hypothetical_papers.length}\n`);

    console.log('COMBINED IMPACT:');
    console.log(`  Total Cross-Domain Connections: ${scenario.combined_impact.cross_domain_connections_added}`);
    console.log(`  Total Orphans Connected: ${scenario.combined_impact.orphaned_papers_connected}`);
    console.log(`  Density Improvement: ${(scenario.combined_impact.knowledge_density_improvement * 100).toFixed(2)}%`);
    console.log(`  Avg Cluster Bridging Score: ${(scenario.combined_impact.cluster_bridging_score * 100).toFixed(0)}%`);
    console.log(`  Unique Research Directions: ${scenario.combined_impact.new_research_directions.length}\n`);

    console.log('COMPARISON TO BASELINE:');
    console.log(`  Connectivity Delta: +${scenario.comparison_to_baseline.connectivity_delta}`);
    console.log(`  Density Delta: +${(scenario.comparison_to_baseline.density_delta * 100).toFixed(2)}%`);
    console.log(`  Cluster Count Delta: ${scenario.comparison_to_baseline.cluster_count_delta}\n`);

    // Validate prediction accuracy
    console.log('Validating prediction accuracy (5 sample papers)...');
    const validation = await explorer.batchValidate(5);

    console.log('VALIDATION RESULTS:');
    console.log(`  Average Accuracy: ${(validation.average_accuracy * 100).toFixed(0)}%`);
    console.log(`  Average Similarity Error: ${(validation.average_error * 100).toFixed(1)}%`);
    console.log(`  Sample Size: ${validation.results.length} papers\n`);

    for (const result of validation.results.slice(0, 3)) {
      console.log(`  Paper: ${result.test_paper_id}`);
      console.log(`    Accuracy: ${(result.accuracy * 100).toFixed(0)}%`);
      console.log(`    Mean Error: ${(result.mean_similarity_error * 100).toFixed(1)}%`);
    }
  } catch (error) {
    console.error('Demo failed:', error);
  }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Load graph data from file
 */
async function loadGraphData(): Promise<any> {
  const graphPath = '/home/mike-anderson/vaults/cohezion-vault/.obsidian/3d-graph-data.json';

  try {
    const response = await fetch(`file://${graphPath}`);
    if (!response.ok) {
      throw new Error(`Failed to load graph data: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Failed to load graph data:', error);
    // Return mock data for demo
    return {
      meta: { nodes_count: 84, edges_count: 575 },
      nodes: generateMockNodes(84),
      edges: generateMockEdges(84, 575),
    };
  }
}

/**
 * Generate mock nodes for testing
 */
function generateMockNodes(count: number): any[] {
  const nodes = [];
  for (let i = 0; i < count; i++) {
    nodes.push({
      id: `paper-${i}`,
      label: `Paper ${i}`,
      type: 'paper',
      x: Math.random() * 100 - 50,
      y: Math.random() * 100 - 50,
      z: Math.random() * 100 - 50,
      tags: ['ai', 'quantum', 'distributed-systems'][Math.floor(Math.random() * 3)],
      description: `Description for paper ${i}`,
    });
  }
  return nodes;
}

/**
 * Generate mock edges for testing
 */
function generateMockEdges(nodeCount: number, edgeCount: number): any[] {
  const edges = [];
  for (let i = 0; i < edgeCount; i++) {
    const source = Math.floor(Math.random() * nodeCount);
    const target = Math.floor(Math.random() * nodeCount);
    if (source !== target) {
      edges.push({
        source: `paper-${source}`,
        target: `paper-${target}`,
      });
    }
  }
  return edges;
}

// ============================================================================
// MAIN
// ============================================================================

/**
 * Run all demos
 */
export async function runAllDemos() {
  console.log('╔══════════════════════════════════════════════════════════════╗');
  console.log('║  Phase 4 Universe Simulation - Comprehensive Demo Suite     ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');

  await demoDecisionForkSimulator();
  await demoTaskOptimizer();
  await demoKnowledgeGapExplorer();

  console.log('\n╔══════════════════════════════════════════════════════════════╗');
  console.log('║  All Demos Complete!                                         ║');
  console.log('╚══════════════════════════════════════════════════════════════╝\n');
}

// Run demos if executed directly
if (typeof require !== 'undefined' && require.main === module) {
  runAllDemos().catch(console.error);
}
