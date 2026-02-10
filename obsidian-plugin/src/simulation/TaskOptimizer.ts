/**
 * Agent Task Optimizer - Phase 4 Universe Simulation
 *
 * Optimizes task assignment across multiple agents by analyzing historical performance
 * and task dependency DAGs. Provides alternative execution plans with predicted metrics.
 *
 * Architecture:
 * 1. Parse task dependency DAG from .claude/tasks/ (JSON files)
 * 2. Fetch historical agent performance from ~/.claude/history.jsonl
 * 3. Compute optimal task-to-agent assignment (minimize time * weight + cost * weight)
 * 4. Visualize predicted timeline (Gantt chart)
 * 5. Allow user to adjust assignments and re-simulate
 * 6. Compare actual vs optimal (time saved, tokens saved)
 */

import { Notice } from 'obsidian';

// ============================================================================
// TYPES
// ============================================================================

/**
 * Task node from .claude/tasks/ DAG
 */
interface Task {
  id: string;
  subject: string;
  description: string;
  status: 'pending' | 'in_progress' | 'completed';
  owner?: string; // Agent name
  blockedBy?: string[]; // Task IDs
  blocks?: string[]; // Task IDs
  metadata?: any;
}

/**
 * Agent type with historical performance metrics
 */
interface AgentType {
  name: string; // e.g., "haiku", "sonnet", "opus", "specialist-surrealdb"
  cost_per_1k_tokens: number; // USD per 1k tokens
  avg_tokens_per_task: number; // Estimated tokens per task
  avg_completion_time_minutes: number; // Average task completion time
  success_rate: number; // 0.0-1.0
  specialization?: string; // e.g., "database", "ui", "math"
}

/**
 * Task assignment (task -> agent mapping)
 */
interface TaskAssignment {
  task_id: string;
  agent_name: string;
  estimated_tokens: number;
  estimated_cost: number;
  estimated_time_minutes: number;
  confidence: number; // 0.0-1.0 (how confident in this assignment)
}

/**
 * Execution plan (ordered task assignments)
 */
interface ExecutionPlan {
  assignments: TaskAssignment[];
  total_cost: number;
  total_time_minutes: number; // Critical path time (accounts for parallelism)
  total_tokens: number;
  parallelism_score: number; // 0.0-1.0 (how much parallelism achieved)
  gantt_chart_data: GanttChartData;
}

/**
 * Gantt chart visualization data
 */
interface GanttChartData {
  tasks: Array<{
    task_id: string;
    agent_name: string;
    start_minute: number; // Relative to project start
    duration_minutes: number;
    dependencies: string[]; // Task IDs
    status: 'scheduled' | 'running' | 'completed';
  }>;
  critical_path: string[]; // Task IDs on critical path
  makespan_minutes: number; // Total project duration
}

/**
 * Optimization constraints
 */
interface OptimizationConstraints {
  time_weight: number; // 0.0-1.0 (priority on minimizing time)
  cost_weight: number; // 0.0-1.0 (priority on minimizing cost)
  max_parallel_agents: number; // Max concurrent agents
  available_agents: AgentType[]; // Available agent types
}

/**
 * Comparison between actual and optimal execution
 */
interface ActualVsOptimal {
  actual_plan: ExecutionPlan;
  optimal_plan: ExecutionPlan;
  savings: {
    time_minutes: number; // Negative = actual was slower
    cost_usd: number; // Negative = actual was more expensive
    tokens: number; // Negative = actual used more tokens
  };
  bottlenecks: string[]; // Task IDs that were bottlenecks in actual execution
  recommendations: string[]; // Actionable improvements
}

// ============================================================================
// HISTORICAL DATA PARSER
// ============================================================================

/**
 * Parse Claude history.jsonl for agent performance metrics
 */
class HistoryParser {
  /**
   * Parse history file and extract agent metrics
   */
  async parseHistoryFile(filePath: string): Promise<Map<string, AgentType>> {
    // Read file via fetch (assuming local file access)
    const response = await fetch(`file://${filePath}`);
    if (!response.ok) {
      throw new Error(`Failed to read history file: ${response.statusText}`);
    }

    const content = await response.text();
    const lines = content.split('\n').filter((line) => line.trim());

    // Parse JSONL
    const entries = lines.map((line) => {
      try {
        return JSON.parse(line);
      } catch (e) {
        return null;
      }
    }).filter((entry) => entry !== null);

    // Aggregate metrics by agent type
    const agentMetrics = new Map<string, AgentType>();

    for (const entry of entries) {
      const agentName = entry.agent || 'unknown';
      const tokens = entry.tokens || 0;
      const timeMinutes = (entry.duration_ms || 0) / 60000;
      const success = entry.status === 'success';

      if (!agentMetrics.has(agentName)) {
        agentMetrics.set(agentName, {
          name: agentName,
          cost_per_1k_tokens: this.getCostPerToken(agentName),
          avg_tokens_per_task: tokens,
          avg_completion_time_minutes: timeMinutes,
          success_rate: success ? 1.0 : 0.0,
          specialization: entry.specialization,
        });
      } else {
        const agent = agentMetrics.get(agentName)!;
        agent.avg_tokens_per_task = (agent.avg_tokens_per_task + tokens) / 2;
        agent.avg_completion_time_minutes = (agent.avg_completion_time_minutes + timeMinutes) / 2;
        agent.success_rate = (agent.success_rate + (success ? 1.0 : 0.0)) / 2;
      }
    }

    return agentMetrics;
  }

  /**
   * Get cost per 1k tokens for agent type
   */
  private getCostPerToken(agentName: string): number {
    const costs: Record<string, number> = {
      'opus': 15.0, // $15 per 1M tokens
      'sonnet': 3.0, // $3 per 1M tokens
      'haiku': 1.0, // $1 per 1M tokens
      'local-llm': 0.0, // Free (local)
    };

    const normalized = agentName.toLowerCase();
    for (const key in costs) {
      if (normalized.includes(key)) {
        return costs[key] / 1000; // Convert to per 1k tokens
      }
    }

    return 3.0 / 1000; // Default to Sonnet pricing
  }
}

// ============================================================================
// TASK DAG PARSER
// ============================================================================

/**
 * Parse task dependency DAG from .claude/tasks/ directory
 */
class TaskDAGParser {
  /**
   * Load all tasks from tasks directory
   */
  async loadTasks(tasksDir: string): Promise<Map<string, Task>> {
    const tasks = new Map<string, Task>();

    // List task files (assume we have access to filesystem)
    const taskFiles = await this.listTaskFiles(tasksDir);

    for (const file of taskFiles) {
      const content = await this.readTaskFile(`${tasksDir}/${file}`);
      try {
        const task = JSON.parse(content) as Task;
        tasks.set(task.id, task);
      } catch (e) {
        console.warn(`Failed to parse task file ${file}:`, e);
      }
    }

    return tasks;
  }

  /**
   * Build dependency graph (adjacency list)
   */
  buildDependencyGraph(tasks: Map<string, Task>): Map<string, string[]> {
    const graph = new Map<string, string[]>();

    for (const [taskId, task] of tasks) {
      graph.set(taskId, task.blockedBy || []);
    }

    return graph;
  }

  /**
   * Topological sort (returns tasks in executable order)
   */
  topologicalSort(tasks: Map<string, Task>): string[] {
    const graph = this.buildDependencyGraph(tasks);
    const visited = new Set<string>();
    const result: string[] = [];

    const dfs = (taskId: string) => {
      if (visited.has(taskId)) return;
      visited.add(taskId);

      const dependencies = graph.get(taskId) || [];
      for (const depId of dependencies) {
        dfs(depId);
      }

      result.push(taskId);
    };

    for (const taskId of tasks.keys()) {
      dfs(taskId);
    }

    return result;
  }

  /**
   * List task files (stub - would use file system API)
   */
  private async listTaskFiles(dir: string): Promise<string[]> {
    // Stub: In real implementation, would use fs.readdir or equivalent
    // For now, return empty array
    return [];
  }

  /**
   * Read task file (stub - would use file system API)
   */
  private async readTaskFile(filePath: string): Promise<string> {
    // Stub: In real implementation, would use fs.readFile or fetch
    return '{}';
  }
}

// ============================================================================
// OPTIMIZATION ENGINE
// ============================================================================

/**
 * Task assignment optimization engine
 */
class OptimizationEngine {
  /**
   * Compute optimal task assignments
   *
   * Uses greedy algorithm with heuristics:
   * 1. Topological sort tasks (dependency order)
   * 2. For each task, assign to agent with minimum objective function value
   * 3. Objective: time_weight * time + cost_weight * cost
   * 4. Account for agent availability (parallelism)
   */
  optimize(
    tasks: Map<string, Task>,
    agentTypes: Map<string, AgentType>,
    constraints: OptimizationConstraints
  ): ExecutionPlan {
    const parser = new TaskDAGParser();
    const sortedTaskIds = parser.topologicalSort(tasks);

    const assignments: TaskAssignment[] = [];
    const agentTimelines = new Map<string, number>(); // Agent -> earliest available time

    // Initialize agent timelines
    for (const agent of constraints.available_agents) {
      agentTimelines.set(agent.name, 0);
    }

    for (const taskId of sortedTaskIds) {
      const task = tasks.get(taskId)!;

      // Find best agent for this task
      let bestAgent: AgentType | null = null;
      let bestScore = Infinity;
      let bestStartTime = 0;

      for (const agent of constraints.available_agents) {
        // Compute start time (when agent is free + dependencies satisfied)
        const agentFreeTime = agentTimelines.get(agent.name) || 0;
        const depsSatisfiedTime = this.computeDependencySatisfiedTime(
          task,
          tasks,
          assignments
        );
        const startTime = Math.max(agentFreeTime, depsSatisfiedTime);

        // Estimate task metrics for this agent
        const estimatedTokens = this.estimateTokens(task, agent);
        const estimatedCost = (estimatedTokens / 1000) * agent.cost_per_1k_tokens;
        const estimatedTime = agent.avg_completion_time_minutes;

        // Compute objective function
        const score =
          constraints.time_weight * estimatedTime +
          constraints.cost_weight * estimatedCost * 100; // Scale cost to be comparable

        if (score < bestScore) {
          bestScore = score;
          bestAgent = agent;
          bestStartTime = startTime;
        }
      }

      if (!bestAgent) {
        throw new Error(`No available agent for task ${taskId}`);
      }

      // Create assignment
      const estimatedTokens = this.estimateTokens(task, bestAgent);
      const estimatedCost = (estimatedTokens / 1000) * bestAgent.cost_per_1k_tokens;
      const estimatedTime = bestAgent.avg_completion_time_minutes;

      assignments.push({
        task_id: taskId,
        agent_name: bestAgent.name,
        estimated_tokens: estimatedTokens,
        estimated_cost: estimatedCost,
        estimated_time_minutes: estimatedTime,
        confidence: bestAgent.success_rate,
      });

      // Update agent timeline
      agentTimelines.set(bestAgent.name, bestStartTime + estimatedTime);
    }

    // Generate Gantt chart data
    const ganttData = this.generateGanttChart(assignments, tasks);

    // Calculate totals
    const totalCost = assignments.reduce((sum, a) => sum + a.estimated_cost, 0);
    const totalTokens = assignments.reduce((sum, a) => sum + a.estimated_tokens, 0);
    const totalTime = ganttData.makespan_minutes;

    return {
      assignments,
      total_cost: totalCost,
      total_time_minutes: totalTime,
      total_tokens: totalTokens,
      parallelism_score: this.computeParallelismScore(ganttData),
      gantt_chart_data: ganttData,
    };
  }

  /**
   * Compute when all dependencies are satisfied
   */
  private computeDependencySatisfiedTime(
    task: Task,
    tasks: Map<string, Task>,
    assignments: TaskAssignment[]
  ): number {
    if (!task.blockedBy || task.blockedBy.length === 0) {
      return 0; // No dependencies
    }

    let maxTime = 0;

    for (const depId of task.blockedBy) {
      const depAssignment = assignments.find((a) => a.task_id === depId);
      if (depAssignment) {
        maxTime = Math.max(maxTime, depAssignment.estimated_time_minutes);
      }
    }

    return maxTime;
  }

  /**
   * Estimate tokens for task-agent pair
   */
  private estimateTokens(task: Task, agent: AgentType): number {
    // Baseline: agent's historical average
    let estimate = agent.avg_tokens_per_task;

    // Adjust based on task complexity (use description length as proxy)
    const complexityMultiplier = Math.min(2.0, task.description.length / 500);
    estimate *= complexityMultiplier;

    // Adjust based on specialization match
    if (agent.specialization && task.metadata?.specialization === agent.specialization) {
      estimate *= 0.8; // 20% reduction if specialized agent matches task
    }

    return Math.round(estimate);
  }

  /**
   * Generate Gantt chart data
   */
  private generateGanttChart(
    assignments: TaskAssignment[],
    tasks: Map<string, Task>
  ): GanttChartData {
    const ganttTasks: GanttChartData['tasks'] = [];
    const taskStartTimes = new Map<string, number>();
    const agentTimelines = new Map<string, number>();

    for (const assignment of assignments) {
      const task = tasks.get(assignment.task_id)!;

      // Compute start time
      const agentFreeTime = agentTimelines.get(assignment.agent_name) || 0;
      const depsSatisfiedTime = this.computeDepsSatisfiedTimeGantt(
        task,
        taskStartTimes,
        assignments
      );
      const startTime = Math.max(agentFreeTime, depsSatisfiedTime);

      ganttTasks.push({
        task_id: assignment.task_id,
        agent_name: assignment.agent_name,
        start_minute: startTime,
        duration_minutes: assignment.estimated_time_minutes,
        dependencies: task.blockedBy || [],
        status: 'scheduled',
      });

      taskStartTimes.set(assignment.task_id, startTime);
      agentTimelines.set(assignment.agent_name, startTime + assignment.estimated_time_minutes);
    }

    // Compute makespan (project duration)
    const makespan = Math.max(...Array.from(agentTimelines.values()));

    // Compute critical path (longest path through DAG)
    const criticalPath = this.computeCriticalPath(ganttTasks);

    return {
      tasks: ganttTasks,
      critical_path: criticalPath,
      makespan_minutes: makespan,
    };
  }

  /**
   * Compute when dependencies are satisfied (for Gantt chart)
   */
  private computeDepsSatisfiedTimeGantt(
    task: Task,
    taskStartTimes: Map<string, number>,
    assignments: TaskAssignment[]
  ): number {
    if (!task.blockedBy || task.blockedBy.length === 0) {
      return 0;
    }

    let maxEndTime = 0;

    for (const depId of task.blockedBy) {
      const depStartTime = taskStartTimes.get(depId) || 0;
      const depAssignment = assignments.find((a) => a.task_id === depId);
      const depDuration = depAssignment?.estimated_time_minutes || 0;
      maxEndTime = Math.max(maxEndTime, depStartTime + depDuration);
    }

    return maxEndTime;
  }

  /**
   * Compute critical path (longest path through task DAG)
   */
  private computeCriticalPath(ganttTasks: GanttChartData['tasks']): string[] {
    // Simplified: return tasks on the longest sequential chain
    // In a full implementation, would use dynamic programming
    const taskMap = new Map(ganttTasks.map((t) => [t.task_id, t]));
    let longestPath: string[] = [];
    let longestDuration = 0;

    const dfs = (taskId: string, path: string[], duration: number) => {
      const task = taskMap.get(taskId);
      if (!task) return;

      const newPath = [...path, taskId];
      const newDuration = duration + task.duration_minutes;

      if (newDuration > longestDuration) {
        longestDuration = newDuration;
        longestPath = newPath;
      }

      // Find tasks that depend on this one
      for (const [id, t] of taskMap) {
        if (t.dependencies.includes(taskId)) {
          dfs(id, newPath, newDuration);
        }
      }
    };

    // Start DFS from root tasks (no dependencies)
    for (const task of ganttTasks) {
      if (task.dependencies.length === 0) {
        dfs(task.task_id, [], 0);
      }
    }

    return longestPath;
  }

  /**
   * Compute parallelism score (0.0-1.0)
   */
  private computeParallelismScore(ganttData: GanttChartData): number {
    // Parallelism = (sum of all task durations) / makespan
    // Perfect parallelism = 1.0 (all tasks run simultaneously)
    // Zero parallelism = (sum / makespan approaches 1.0)
    const totalTaskTime = ganttData.tasks.reduce((sum, t) => sum + t.duration_minutes, 0);
    const makespan = ganttData.makespan_minutes;

    if (makespan === 0) return 0.0;

    const parallelism = totalTaskTime / makespan / ganttData.tasks.length;
    return Math.min(1.0, parallelism);
  }
}

// ============================================================================
// TASK OPTIMIZER
// ============================================================================

/**
 * Main optimizer class
 */
export class TaskOptimizer {
  private historyParser: HistoryParser;
  private dagParser: TaskDAGParser;
  private optimizationEngine: OptimizationEngine;

  constructor() {
    this.historyParser = new HistoryParser();
    this.dagParser = new TaskDAGParser();
    this.optimizationEngine = new OptimizationEngine();
  }

  /**
   * Optimize task assignments
   */
  async optimize(
    tasksDir: string,
    historyFile: string,
    constraints: OptimizationConstraints
  ): Promise<ExecutionPlan> {
    new Notice('Optimizing task assignments...', 3000);

    try {
      // 1. Load tasks
      const tasks = await this.dagParser.loadTasks(tasksDir);

      // 2. Load historical agent performance
      const agentTypes = await this.historyParser.parseHistoryFile(historyFile);

      // 3. Run optimization
      const plan = this.optimizationEngine.optimize(tasks, agentTypes, constraints);

      new Notice(`Optimization complete: ${plan.total_time_minutes} min, $${plan.total_cost.toFixed(2)}`, 5000);

      return plan;
    } catch (error) {
      new Notice(`Optimization failed: ${error.message}`, 5000);
      throw error;
    }
  }

  /**
   * Compare actual vs optimal execution
   */
  async compareActualVsOptimal(
    actualPlan: ExecutionPlan,
    optimalPlan: ExecutionPlan
  ): Promise<ActualVsOptimal> {
    const timeSaved = actualPlan.total_time_minutes - optimalPlan.total_time_minutes;
    const costSaved = actualPlan.total_cost - optimalPlan.total_cost;
    const tokensSaved = actualPlan.total_tokens - optimalPlan.total_tokens;

    // Identify bottlenecks (tasks on actual critical path that could be parallelized)
    const bottlenecks = this.identifyBottlenecks(actualPlan, optimalPlan);

    // Generate recommendations
    const recommendations = this.generateRecommendations(actualPlan, optimalPlan, bottlenecks);

    return {
      actual_plan: actualPlan,
      optimal_plan: optimalPlan,
      savings: {
        time_minutes: timeSaved,
        cost_usd: costSaved,
        tokens: tokensSaved,
      },
      bottlenecks,
      recommendations,
    };
  }

  /**
   * Identify bottleneck tasks
   */
  private identifyBottlenecks(actual: ExecutionPlan, optimal: ExecutionPlan): string[] {
    const bottlenecks: string[] = [];

    // Tasks on actual critical path that are NOT on optimal critical path
    const actualCritical = new Set(actual.gantt_chart_data.critical_path);
    const optimalCritical = new Set(optimal.gantt_chart_data.critical_path);

    for (const taskId of actualCritical) {
      if (!optimalCritical.has(taskId)) {
        bottlenecks.push(taskId);
      }
    }

    return bottlenecks;
  }

  /**
   * Generate actionable recommendations
   */
  private generateRecommendations(
    actual: ExecutionPlan,
    optimal: ExecutionPlan,
    bottlenecks: string[]
  ): string[] {
    const recommendations: string[] = [];

    // Time savings
    if (optimal.total_time_minutes < actual.total_time_minutes) {
      recommendations.push(
        `Use parallel agents to save ${Math.round(actual.total_time_minutes - optimal.total_time_minutes)} minutes`
      );
    }

    // Cost savings
    if (optimal.total_cost < actual.total_cost) {
      recommendations.push(
        `Switch to cheaper agents (Haiku/local LLMs) to save $${(actual.total_cost - optimal.total_cost).toFixed(2)}`
      );
    }

    // Parallelism
    if (optimal.parallelism_score > actual.parallelism_score) {
      recommendations.push(
        `Increase parallelism from ${(actual.parallelism_score * 100).toFixed(0)}% to ${(optimal.parallelism_score * 100).toFixed(0)}%`
      );
    }

    // Bottlenecks
    if (bottlenecks.length > 0) {
      recommendations.push(`Address bottlenecks in tasks: ${bottlenecks.join(', ')}`);
    }

    return recommendations;
  }

  /**
   * Re-simulate with user-adjusted assignments
   */
  async resimulate(
    tasks: Map<string, Task>,
    customAssignments: Map<string, string> // Task ID -> Agent name
  ): Promise<ExecutionPlan> {
    // TODO: Implement custom assignment simulation
    // For now, return empty plan
    return {
      assignments: [],
      total_cost: 0,
      total_time_minutes: 0,
      total_tokens: 0,
      parallelism_score: 0,
      gantt_chart_data: {
        tasks: [],
        critical_path: [],
        makespan_minutes: 0,
      },
    };
  }
}
