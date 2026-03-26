"use client";

import React from "react";

interface TimelineStage {
  stage: number;
  symmetry: string;
  label: string;
  temperature: number;
  description: string;
  equation: string;
  color: string;
}

const STAGES: TimelineStage[] = [
  {
    stage: -1,
    symmetry: "void",
    label: "The Void",
    temperature: 200,
    description: "Brahmagupta's zero. Awareness of nothing.",
    equation: "∅",
    color: "#333333",
  },
  {
    stage: 0,
    symmetry: "SO(12)",
    label: "Symmetric Vacuum",
    temperature: 100,
    description: "Full rotational symmetry. All dimensions equivalent.",
    equation: "SO(12)",
    color: "#ffffff",
  },
  {
    stage: 1,
    symmetry: "SO(3)^4",
    label: "Fabric Differentiation",
    temperature: 10,
    description: "Four fabrics emerge: Space, Field, Control, Precipitation.",
    equation: "SO(12) → SO(3)⁴",
    color: "#4488ff",
  },
  {
    stage: 2,
    symmetry: "U(1)^4",
    label: "Axis Selection",
    temperature: 1.0,
    description: "Each fabric develops a preferred direction.",
    equation: "SO(3)⁴ → U(1)⁴",
    color: "#ffaa22",
  },
  {
    stage: 3,
    symmetry: "Z_2^4",
    label: "SPIN Discretization",
    temperature: 0.1,
    description: "Up or down. Charge polarity emerges.",
    equation: "U(1)⁴ → Z₂⁴",
    color: "#22ff88",
  },
  {
    stage: 4,
    symmetry: "HIHO",
    label: "HIHO Attractor",
    temperature: 0.01,
    description: "The still point. δ = 0. The dance begins.",
    equation: "Z₂⁴ → HIHO(0.5)",
    color: "#00ff00",
  },
];

interface CosmogonyTimelineProps {
  currentStage: number;
  currentTemperature: number;
  className?: string;
}

export default function CosmogonyTimeline({
  currentStage,
  currentTemperature,
  className = "",
}: CosmogonyTimelineProps) {
  return (
    <div className={`bg-black/90 border border-gray-700 rounded-lg p-4 font-mono ${className}`}>
      <h3 className="text-sm text-green-400 font-bold mb-4">Cosmogony</h3>

      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-3 top-0 bottom-0 w-px bg-gray-700" />

        {/* Stages */}
        <div className="space-y-3">
          {STAGES.map((s) => {
            const isActive = currentStage >= s.stage;
            const isCurrent = currentStage === s.stage;

            return (
              <div key={s.stage} className="relative pl-8">
                {/* Dot */}
                <div
                  className={`absolute left-1.5 top-1 w-3 h-3 rounded-full border-2 transition-colors ${
                    isCurrent
                      ? "border-green-400 bg-green-400 shadow-[0_0_6px_rgba(0,255,0,0.5)]"
                      : isActive
                        ? "border-green-600 bg-green-900"
                        : "border-gray-600 bg-gray-900"
                  }`}
                />

                {/* Content */}
                <div className={`transition-opacity ${isActive ? "opacity-100" : "opacity-40"}`}>
                  <div className="flex items-center gap-2">
                    <span
                      className="text-[11px] font-bold"
                      style={{ color: isActive ? s.color : "#666" }}
                    >
                      {s.label}
                    </span>
                    <span className="text-[9px] text-gray-600">
                      T_c = {s.temperature}
                    </span>
                  </div>

                  <div className="text-[10px] text-yellow-400/80 mt-0.5">
                    {s.equation}
                  </div>

                  {isCurrent && (
                    <div className="text-[10px] text-gray-400 mt-0.5 italic">
                      {s.description}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Temperature indicator */}
      <div className="mt-4 pt-3 border-t border-gray-800 text-[10px] text-gray-500">
        T = <span className="text-cyan-400">{currentTemperature.toFixed(2)}</span>
      </div>
    </div>
  );
}
