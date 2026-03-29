"use client";

import React from "react";

interface PipelineStep {
  name: string;
  status: "pending" | "active" | "complete" | "error";
  description: string;
  duration_ms?: number;
  token_count?: number;
}

const PIPELINE_STEPS: PipelineStep[] = [
  { name: "Vault Query", status: "pending", description: "Search vault for similar past experiences" },
  { name: "Template Match", status: "pending", description: "Find reusable PRIME skill templates" },
  { name: "Alignment Check", status: "pending", description: "RequestAlignmentAnalyzer: coherence/completeness/drift" },
  { name: "Plan Generation", status: "pending", description: "PlanExecutor creates tactical execution plan" },
  { name: "Task Execution", status: "pending", description: "Execute task with model routing and caching" },
  { name: "Quality Gate", status: "pending", description: "DegradationDetector: thermal and quality thresholds" },
  { name: "Journey Track", status: "pending", description: "JourneyTracker: record 12D manifold position" },
  { name: "Metrics Collect", status: "pending", description: "GlobalMetricsAggregator: record instance metrics" },
  { name: "Retrospection", status: "pending", description: "RetrospectionEngine: extract learnings, flag anomalies" },
  { name: "Skill Refine", status: "pending", description: "SkillRefiner: update PRIME skill definitions" },
  { name: "Consensus Vote", status: "pending", description: "SkillConsensusVoter: multi-agent validation" },
];

const STATUS_COLORS = {
  pending: "border-gray-700 bg-gray-900/30 text-gray-500",
  active: "border-yellow-500 bg-yellow-900/20 text-yellow-400 animate-pulse",
  complete: "border-green-600 bg-green-900/20 text-green-400",
  error: "border-red-600 bg-red-900/20 text-red-400",
};

const STATUS_DOTS = {
  pending: "bg-gray-600",
  active: "bg-yellow-400 shadow-[0_0_6px_rgba(234,179,8,0.5)]",
  complete: "bg-green-500",
  error: "bg-red-500",
};

interface CompoundPipelineVizProps {
  steps?: PipelineStep[];
  activeStep?: number;
  className?: string;
}

export default function CompoundPipelineViz({
  steps,
  activeStep = -1,
  className = "",
}: CompoundPipelineVizProps) {
  const displaySteps = steps || PIPELINE_STEPS.map((s, i) => ({
    ...s,
    status: i < activeStep ? "complete" as const
      : i === activeStep ? "active" as const
      : "pending" as const,
  }));

  const completedCount = displaySteps.filter((s) => s.status === "complete").length;
  const progress = (completedCount / displaySteps.length) * 100;

  return (
    <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 font-mono ${className}`}>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm text-green-400 font-bold">Compound Engineering Pipeline</h3>
        <span className="text-[10px] text-gray-500">
          {completedCount}/{displaySteps.length} steps
        </span>
      </div>

      {/* Progress bar */}
      <div className="w-full h-1 bg-gray-800 rounded-full mb-4">
        <div
          className="h-full bg-green-500 rounded-full transition-all duration-300"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Steps */}
      <div className="space-y-1.5">
        {displaySteps.map((step, i) => (
          <div
            key={i}
            className={`flex items-center gap-3 px-3 py-1.5 rounded border transition-colors ${STATUS_COLORS[step.status]}`}
          >
            {/* Status dot */}
            <div className={`w-2 h-2 rounded-full flex-shrink-0 ${STATUS_DOTS[step.status]}`} />

            {/* Step info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold truncate">{step.name}</span>
                {step.duration_ms !== undefined && (
                  <span className="text-[9px] text-gray-600 ml-2">{step.duration_ms}ms</span>
                )}
              </div>
              {step.status === "active" && (
                <div className="text-[9px] text-gray-500 truncate">{step.description}</div>
              )}
            </div>

            {/* Token count */}
            {step.token_count !== undefined && (
              <span className="text-[9px] text-cyan-600 flex-shrink-0">
                {step.token_count} tok
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-3 pt-2 border-t border-gray-800 text-[9px] text-gray-600">
        <span className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-gray-600" /> Pending
        </span>
        <span className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-yellow-400" /> Active
        </span>
        <span className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500" /> Complete
        </span>
        <span className="flex items-center gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-red-500" /> Error
        </span>
      </div>
    </div>
  );
}
