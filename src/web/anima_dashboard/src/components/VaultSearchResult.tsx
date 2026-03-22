"use client";

import { useState } from "react";
import ProvenanceTag from "@/components/ProvenanceTag";

interface VaultSearchResultProps {
  title: string;
  excerpt: string;
  pillar: "Decision" | "Experiment" | "Pattern";
  relevance: number;
  source: string;
}

const PILLAR_COLORS = {
  Decision: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/20" },
  Experiment: { bg: "bg-blue-500/10", text: "text-blue-400", border: "border-blue-500/20" },
  Pattern: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
};

export default function VaultSearchResult({
  title,
  excerpt,
  pillar,
  relevance,
  source,
}: VaultSearchResultProps) {
  const [expanded, setExpanded] = useState(false);
  const colors = PILLAR_COLORS[pillar];

  return (
    <div
      className={`p-4 ${colors.bg} border ${colors.border} rounded-xl cursor-pointer transition-all hover:bg-white/5`}
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 text-[9px] font-mono font-bold tracking-wider ${colors.text} ${colors.bg} border ${colors.border} rounded`}>
            {pillar.toUpperCase()}
          </span>
          <ProvenanceTag source={source}>
            <h4 className="text-sm font-mono font-bold text-white">{title}</h4>
          </ProvenanceTag>
        </div>
        <span className="text-[10px] font-mono text-gray-500">
          {(relevance * 100).toFixed(0)}%
        </span>
      </div>
      <p className={`text-xs font-mono text-gray-400 leading-relaxed ${expanded ? "" : "line-clamp-2"}`}>
        {excerpt}
      </p>
    </div>
  );
}
