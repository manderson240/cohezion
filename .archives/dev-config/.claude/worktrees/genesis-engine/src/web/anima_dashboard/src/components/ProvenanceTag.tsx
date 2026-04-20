"use client";

import { useState, type ReactNode } from "react";

interface ProvenanceTagProps {
  /** The physics engine source path, e.g. "HIHOStabilizationEngine.apply_hiho_loop()" */
  source: string;
  children: ReactNode;
}

/**
 * Provenance Tag (FR16).
 * Wraps any data point with a hover tooltip showing its physics engine source.
 */
export default function ProvenanceTag({ source, children }: ProvenanceTagProps) {
  const [show, setShow] = useState(false);

  return (
    <span
      className="relative inline-block cursor-help"
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      {children}
      {show && (
        <span
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-1.5 bg-black/95 border rounded-lg text-[10px] font-mono whitespace-nowrap z-50 shadow-lg"
          style={{ borderColor: "var(--hiho-glow-color, #00ff00)40" }}
        >
          <span className="text-gray-500">src:</span>{" "}
          <span style={{ color: "var(--hiho-glow-color, #00ff00)" }}>
            {source}
          </span>
        </span>
      )}
    </span>
  );
}
