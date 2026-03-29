"use client";

import React, { useState } from "react";
import katex from "katex";

interface Equation {
  /** LaTeX string */
  latex: string;
  /** Human-readable label */
  label: string;
  /** Optional description below the equation */
  description?: string;
  /** Whether this equation is "active" (highlighted) based on current state */
  active?: boolean;
  /** Optional dynamic value to show alongside */
  value?: string | number;
}

interface EquationPanelProps {
  /** Title of the panel */
  title: string;
  /** Array of equations to display */
  equations: Equation[];
  /** Whether the panel starts collapsed */
  defaultCollapsed?: boolean;
  /** Optional className for positioning */
  className?: string;
}

/**
 * Render LaTeX to HTML using KaTeX.
 *
 * SECURITY NOTE: KaTeX output is safe — it generates only math markup
 * from our own hardcoded LaTeX strings (not user input). KaTeX itself
 * escapes all special characters and never produces executable content.
 * See: https://katex.org/docs/security.html
 */
function KaTeXBlock({ latex }: { latex: string }) {
  let html: string;
  try {
    html = katex.renderToString(latex, {
      throwOnError: false,
      displayMode: true,
      trust: false, // Disable \url, \href, \includegraphics
      strict: "warn",
    });
  } catch {
    html = `<span style="color: #f87171">${latex.replace(/</g, "&lt;")}</span>`;
  }

  // KaTeX output is trusted math markup from our own LaTeX definitions.
  // trust: false prevents any URL/image embedding. Content is not user-supplied.
  return (
    <div
      className="text-white overflow-x-auto text-sm"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}

export default function EquationPanel({
  title,
  equations,
  defaultCollapsed = false,
  className = "",
}: EquationPanelProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <div
      className={`bg-black/90 border border-gray-700 rounded-lg overflow-hidden font-mono ${className}`}
    >
      {/* Header */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center justify-between px-4 py-2 text-sm text-green-400 hover:bg-gray-800/50 transition-colors"
      >
        <span className="font-bold">{title}</span>
        <span className="text-gray-500">{collapsed ? "+" : "-"}</span>
      </button>

      {/* Equations */}
      {!collapsed && (
        <div className="px-4 pb-4 space-y-3">
          {equations.map((eq, i) => (
            <div
              key={i}
              className={`rounded-md p-2 transition-colors ${
                eq.active
                  ? "bg-green-900/20 border border-green-800/50"
                  : "bg-gray-900/30"
              }`}
            >
              {/* Label */}
              <div className="text-[10px] text-gray-500 mb-1">{eq.label}</div>

              {/* LaTeX equation — rendered by KaTeX (trusted output) */}
              <KaTeXBlock latex={eq.latex} />

              {/* Dynamic value */}
              {eq.value !== undefined && (
                <div className="text-[11px] text-cyan-400 mt-1">
                  = {typeof eq.value === "number" ? eq.value.toFixed(4) : eq.value}
                </div>
              )}

              {/* Description */}
              {eq.description && (
                <div className="text-[10px] text-gray-600 mt-1 italic">
                  {eq.description}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// --- Pre-built equation sets for common physics panels ---

export function spinorEquations(data?: {
  charge: number;
  rotation: number;
  precession: number;
  coherence: number;
}): Equation[] {
  return [
    {
      latex: "|\\psi\\rangle = \\alpha|{\\uparrow}\\rangle + \\beta|{\\downarrow}\\rangle",
      label: "Spinor State",
      description: "2-component spinor on the Bloch sphere",
      active: true,
    },
    {
      latex: "U_{\\text{rot}}(\\theta) = e^{-i\\theta\\sigma_x/2}",
      label: "Rotation (Smith)",
      description: "SU(2) rotation around x-axis",
      active: data ? Math.abs(data.rotation) > 0.5 : false,
      value: data?.rotation,
    },
    {
      latex: "U_{\\text{prec}}(\\phi) = e^{-i\\phi\\sigma_y/2}",
      label: "Precession (Smith)",
      description: "SU(2) rotation around y-axis",
      active: data ? Math.abs(data.precession) > 0.5 : false,
      value: data?.precession,
    },
    {
      latex: "Q = \\langle\\psi|\\sigma_z|\\psi\\rangle = |\\alpha|^2 - |\\beta|^2",
      label: "Charge Polarity",
      description: "Brahmagupta's zero: Q = 0 at HIHO equator",
      active: data ? Math.abs(data.charge) < 0.1 : false,
      value: data?.charge,
    },
    {
      latex: "\\text{coherence} = |\\mathbf{r}| = \\sqrt{r_x^2 + r_y^2 + r_z^2}",
      label: "Bloch Vector Purity",
      value: data?.coherence,
    },
  ];
}

export function cosmogonyEquations(data?: {
  temperature: number;
  symmetry: string;
  orderParam: number;
  freeEnergy: number;
}): Equation[] {
  return [
    {
      latex: "\\varnothing \\to SO(12) \\to SO(3)^4 \\to U(1)^4 \\to \\mathbb{Z}_2^4 \\to \\text{HIHO}",
      label: "Symmetry Breaking Chain",
      description: "From Brahmagupta's void to the 12D manifold",
      active: true,
    },
    {
      latex: "F(\\phi, T) = F_0 + a(T - T_c)\\phi^2 + b\\phi^4",
      label: "Landau Free Energy",
      description: "Phase transition thermodynamics",
      value: data?.freeEnergy,
    },
    {
      latex: "\\phi = \\pm\\sqrt{\\frac{a(T_c - T)}{2b}} \\quad (T < T_c)",
      label: "Order Parameter",
      description: "Nonzero below critical temperature",
      active: data ? data.orderParam > 0.01 : false,
      value: data?.orderParam,
    },
    {
      latex: "\\chi = \\frac{1}{2a|T - T_c|}",
      label: "Susceptibility",
      description: "Diverges at phase transitions",
    },
    {
      latex: "\\delta = \\text{coherence} - 0.5 = 0 \\quad \\text{(HIHO)}",
      label: "Brahmagupta's Zero",
      description: "The equilibrium of the turning world",
      active: data?.symmetry === "HIHO",
    },
  ];
}
