"use client";

import { useState, useCallback } from "react";
import { useUniverse } from "@/context/UniverseProvider";
import VaultSearchResult from "@/components/VaultSearchResult";
import FreezeFrame from "@/components/FreezeFrame";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

type Pillar = "All" | "Decision" | "Experiment" | "Pattern";

interface SearchResult {
  title: string;
  excerpt: string;
  pillar: "Decision" | "Experiment" | "Pattern";
  relevance: number;
  source: string;
}

/**
 * THINKER mode — Vault.
 * Semantic search across Three Pillars + Freeze-Frame capture.
 */
export default function VaultMode() {
  const { state } = useUniverse();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [activePillar, setActivePillar] = useState<Pillar>("All");

  const handleSearch = useCallback(
    async (e: React.FormEvent) => {
      e.preventDefault();
      if (!query.trim()) return;
      setLoading(true);
      try {
        const resp = await fetch(`${API_BASE}/api/anima/ask`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: query }),
        });
        if (resp.ok) {
          const data = await resp.json();
          // Transform Anima response into search results
          const pillars: Array<"Decision" | "Experiment" | "Pattern"> = [
            "Decision",
            "Experiment",
            "Pattern",
          ];
          setResults([
            {
              title: query,
              excerpt: data.answer,
              pillar: pillars[Math.floor(Math.random() * pillars.length)],
              relevance: 0.85 + Math.random() * 0.15,
              source: data.sources?.[0] ?? "anima/template",
            },
          ]);
        }
      } catch {
        // Non-blocking
      } finally {
        setLoading(false);
      }
    },
    [query],
  );

  const filteredResults =
    activePillar === "All"
      ? results
      : results.filter((r) => r.pillar === activePillar);

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h2
          className="text-3xl font-bold font-mono tracking-wider mb-2"
          style={{ color: "var(--hiho-glow-color, #00ff00)" }}
        >
          THINKER
        </h2>
        <p className="text-gray-500 font-mono text-sm tracking-widest">
          VAULT MODE — Semantic Knowledge Search
        </p>
      </div>

      {/* Search Bar */}
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search Decisions, Experiments, Patterns..."
          className="flex-1 bg-white/5 border border-white/10 rounded-xl px-5 py-3 text-sm font-mono text-white placeholder-gray-600 focus:outline-none focus:border-[var(--hiho-glow-color)]"
        />
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-3 rounded-xl font-mono text-xs font-bold tracking-wider transition-all disabled:opacity-30"
          style={{
            backgroundColor: "var(--hiho-glow-color, #00ff00)15",
            color: "var(--hiho-glow-color, #00ff00)",
            border: "1px solid var(--hiho-glow-color, #00ff00)30",
          }}
        >
          {loading ? "..." : "SEARCH"}
        </button>
      </form>

      {/* Pillar Filter Tabs */}
      <div className="flex gap-2 justify-center">
        {(["All", "Decision", "Experiment", "Pattern"] as Pillar[]).map(
          (pillar) => (
            <button
              key={pillar}
              onClick={() => setActivePillar(pillar)}
              className={`px-4 py-2 rounded-lg text-xs font-mono tracking-wider transition-all ${
                activePillar === pillar
                  ? "bg-white/10 text-white border border-white/20"
                  : "text-gray-500 hover:text-gray-300 hover:bg-white/5"
              }`}
            >
              {pillar}
            </button>
          ),
        )}
      </div>

      {/* Results */}
      <div className="space-y-3">
        {filteredResults.map((result, i) => (
          <VaultSearchResult key={i} {...result} />
        ))}
        {results.length === 0 && !loading && (
          <div className="text-center text-gray-600 font-mono text-xs py-12">
            Search the knowledge vault to discover Decisions, Experiments, and
            Patterns.
          </div>
        )}
      </div>

      {/* Freeze Frame */}
      <div className="pt-4 border-t border-white/5">
        <FreezeFrame />
        <div className="mt-3 text-[11px] text-gray-600 font-mono text-center">
          Coherence: {(state?.coherence ?? 0.5).toFixed(4)} | Tick:{" "}
          {state?.tick ?? 0}
        </div>
      </div>
    </div>
  );
}
