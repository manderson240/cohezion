"use client";

import React, { useState, useCallback } from "react";
import dynamic from "next/dynamic";

// Import bindings (side-effect: registers all components)
import "@/a2ui/componentBindings";

import experience from "@/a2ui/experiences/genesis-cosmogony.json";
import { validateExperience } from "@/a2ui/A2UIRenderer";
import catalog from "@/a2ui/catalog.json";
import type { A2UIInspection } from "@/a2ui/A2UIRenderer";

const A2UIRenderer = dynamic(() => import("@/a2ui/A2UIRenderer"), { ssr: false });

export default function A2UIDemoPage() {
  const [inspection, setInspection] = useState<A2UIInspection | null>(null);
  const [actions, setActions] = useState<Array<{ event: string; data?: unknown }>>([]);

  // Validate catalog on load
  const validation = validateExperience(experience as Parameters<typeof validateExperience>[0], catalog as Parameters<typeof validateExperience>[1]);

  const handleAction = useCallback((eventName: string, data?: unknown) => {
    setActions((prev) => [...prev.slice(-19), { event: eventName, data }]);
  }, []);

  const handleInspect = useCallback((data: A2UIInspection) => {
    setInspection(data);
  }, []);

  return (
    <div className="min-h-screen bg-[#020208] text-gray-200 font-mono p-6">
      <h1 className="text-xl text-green-400 font-bold mb-2">A2UI Demo — Genesis Cosmogony</h1>
      <p className="text-xs text-gray-500 mb-6">
        Declarative rendering via A2UI component catalog. Agent-inspectable state below.
      </p>

      {/* Validation status */}
      <div className={`mb-4 text-xs px-3 py-2 rounded border ${
        validation.valid
          ? "border-green-800 text-green-400 bg-green-900/20"
          : "border-red-800 text-red-400 bg-red-900/20"
      }`}>
        Catalog validation: {validation.valid ? "PASSED" : `FAILED (${validation.errors.join(", ")})`}
        {" "}| Components: {Object.keys(catalog.components).length}
        {" "}| Scenes: {experience.scenes.length}
      </div>

      {/* A2UI Renderer */}
      <div className="bg-black/50 border border-gray-800 rounded-lg p-4 mb-6 min-h-[200px]">
        <A2UIRenderer
          experience={experience as Parameters<typeof validateExperience>[0]}
          onAction={handleAction}
          onInspect={handleInspect}
        />
      </div>

      {/* Agent inspection panel */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-black/50 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm text-cyan-400 font-bold mb-2">Inspection State</h2>
          {inspection ? (
            <pre className="text-[10px] text-gray-400 overflow-auto max-h-[300px]">
              {JSON.stringify(inspection, null, 2)}
            </pre>
          ) : (
            <p className="text-xs text-gray-600">Waiting for render...</p>
          )}
        </div>

        <div className="bg-black/50 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm text-yellow-400 font-bold mb-2">Action Log</h2>
          {actions.length === 0 ? (
            <p className="text-xs text-gray-600">No actions yet. Click the void to begin.</p>
          ) : (
            <div className="space-y-1 max-h-[300px] overflow-auto">
              {actions.map((a, i) => (
                <div key={i} className="text-[10px] text-gray-400">
                  <span className="text-green-400">{a.event}</span>
                  {a.data && <span className="text-gray-600"> {JSON.stringify(a.data)}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Catalog reference */}
      <details className="mt-6">
        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
          Full Catalog JSON
        </summary>
        <pre className="text-[9px] text-gray-600 mt-2 overflow-auto max-h-[400px]">
          {JSON.stringify(catalog, null, 2)}
        </pre>
      </details>
    </div>
  );
}
