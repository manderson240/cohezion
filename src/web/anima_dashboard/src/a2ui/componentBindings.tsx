"use client";

/**
 * A2UI Component Bindings for the Cohezion Genesis Engine.
 *
 * Maps catalog component names to existing React/R3F implementations.
 * Call registerAllComponents() once at app init to wire everything up.
 *
 * This is the "resolution" step in the A2UI pipeline:
 *   Generation → Transport → Resolution → Rendering
 *                            ^^^^^^^^^^^^
 *   catalog.json names → actual React components
 */

import React from "react";
import { registerComponent } from "./A2UIRenderer";

// --- Placeholder renderers for catalog components ---
// These bridge A2UI instances to actual GenesisScene sub-components.
// Full integration would import from ../components/genesis/ but those
// components are tightly coupled to the imperative scene graph.
// These stubs provide agent-inspectable HTML placeholders.

registerComponent("cohezion-void-sphere", ({ instance, onAction }) => (
  <div
    data-a2ui-id={instance.id}
    data-a2ui-component="cohezion-void-sphere"
    className="flex items-center justify-center cursor-pointer"
    onClick={() => onAction("void_click")}
    role="button"
    tabIndex={0}
    aria-label="Click the void to begin the cosmogony"
  >
    <div className="w-4 h-4 rounded-full bg-white/20 animate-pulse" />
  </div>
));

registerComponent("cohezion-explosion", ({ instance }) => (
  <div
    data-a2ui-id={instance.id}
    data-a2ui-component="cohezion-explosion"
    data-phase={instance.phase as string}
    className="text-[10px] font-mono text-gray-500"
  >
    [Particles: {instance.phase as string}]
  </div>
));

registerComponent("cohezion-bloch-sphere", ({ instance }) => (
  <div
    data-a2ui-id={instance.id}
    data-a2ui-component="cohezion-bloch-sphere"
    className="text-[10px] font-mono text-cyan-500"
  >
    [Bloch: θ={String(instance.theta)}, φ={String(instance.phi)}]
  </div>
));

registerComponent("cohezion-narration", ({ instance }) => {
  const text = instance.text as string;
  if (!text) return null;
  return (
    <div
      data-a2ui-id={instance.id}
      data-a2ui-component="cohezion-narration"
      className="text-center font-mono italic text-white/80 text-sm px-8 py-4"
      style={{
        background: "rgba(0,0,0,0.4)",
        backdropFilter: "blur(8px)",
      }}
    >
      &ldquo;{text}&rdquo;
    </div>
  );
});

registerComponent("cohezion-sound-engine", ({ instance }) => (
  <div
    data-a2ui-id={instance.id}
    data-a2ui-component="cohezion-sound-engine"
    data-phase={instance.phase as string}
    data-muted={String(instance.muted)}
    className="hidden" // Audio engine has no visual representation
  />
));

registerComponent("cohezion-cosmogony-timeline", ({ instance }) => (
  <div
    data-a2ui-id={instance.id}
    data-a2ui-component="cohezion-cosmogony-timeline"
    className="font-mono text-xs text-gray-400"
  >
    Stage: {String(instance.currentStage)} | T={String(instance.currentTemperature)}
  </div>
));

registerComponent("cohezion-equation-panel", ({ instance }) => (
  <div
    data-a2ui-id={instance.id}
    data-a2ui-component="cohezion-equation-panel"
    className="font-mono text-xs text-green-400"
  >
    [{instance.title as string}]
  </div>
));

registerComponent("cohezion-temperature-slider", ({ instance, onAction }) => (
  <div
    data-a2ui-id={instance.id}
    data-a2ui-component="cohezion-temperature-slider"
  >
    <input
      type="range"
      min={Number(instance.min) || 0.005}
      max={Number(instance.max) || 200}
      defaultValue={Number(instance.value) || 200}
      onChange={(e) => onAction("temperature_change", { value: parseFloat(e.target.value) })}
      className="w-full accent-green-500"
    />
  </div>
));

// No explicit registerAllComponents needed — side-effect imports handle registration
