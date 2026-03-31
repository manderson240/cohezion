"use client";

/**
 * A2UI Renderer for the Cohezion Genesis Engine.
 *
 * Bridges A2UI's declarative component catalog to React Three Fiber components.
 * Reads an experience script (JSON) and instantiates the corresponding R3F
 * components from a catalog of trusted implementations.
 *
 * Design: Security-first (no executable code in JSON), framework-native rendering.
 * Follows A2UI v0.9 simplified format.
 */

import React, { useMemo, useState, useCallback, useEffect } from "react";
import catalog from "./catalog.json";

// --- Types matching A2UI spec ---

interface A2UIComponentInstance {
  id: string;
  component: string;
  [key: string]: unknown; // component-specific props
}

interface A2UIScene {
  id: string;
  description?: string;
  duration: number | null;
  trigger?: { type: string; target?: string };
  transition?: { from: string; auto: boolean };
  entryNarration?: string;
  components: A2UIComponentInstance[];
}

interface A2UIExperience {
  experienceId: string;
  version: string;
  catalogRef: string;
  description: string;
  dataModel: Record<string, { type: string; initial: unknown }>;
  scenes: A2UIScene[];
}

// --- Catalog validation ---

type CatalogDefinition = typeof catalog;

/** Validates that a component type exists in the catalog */
function isValidComponent(
  componentType: string,
  cat: CatalogDefinition
): boolean {
  return componentType in cat.components;
}

/** Validates an entire experience script against the catalog */
export function validateExperience(
  experience: A2UIExperience,
  cat: CatalogDefinition = catalog
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  for (const scene of experience.scenes) {
    for (const comp of scene.components) {
      if (!isValidComponent(comp.component, cat)) {
        errors.push(
          `Scene "${scene.id}": Unknown component "${comp.component}" (not in catalog)`
        );
      }
    }
  }

  // Check scene transitions form a valid chain
  const sceneIds = new Set(experience.scenes.map((s) => s.id));
  for (const scene of experience.scenes) {
    if (scene.transition?.from && !sceneIds.has(scene.transition.from)) {
      errors.push(
        `Scene "${scene.id}": Transition from unknown scene "${scene.transition.from}"`
      );
    }
  }

  return { valid: errors.length === 0, errors };
}

// --- Renderer state ---

interface RendererState {
  currentSceneId: string;
  dataModel: Record<string, unknown>;
  sceneStartTime: number;
  elapsed: number;
}

// --- Component registry (maps catalog names to React components) ---

type ComponentRenderer = React.FC<{
  instance: A2UIComponentInstance;
  state: RendererState;
  onAction: (eventName: string, data?: unknown) => void;
}>;

const componentRegistry: Record<string, ComponentRenderer> = {};

/** Register a React component to render an A2UI catalog component */
export function registerComponent(
  catalogName: string,
  renderer: ComponentRenderer
): void {
  componentRegistry[catalogName] = renderer;
}

// --- A2UI Inspector (for agent testing) ---

export interface A2UIInspection {
  experienceId: string;
  currentScene: string;
  activeComponents: Array<{
    id: string;
    component: string;
    props: Record<string, unknown>;
  }>;
  dataModel: Record<string, unknown>;
  elapsed: number;
  catalogValid: boolean;
}

// --- Main Renderer ---

interface A2UIRendererProps {
  experience: A2UIExperience;
  onAction?: (eventName: string, data?: unknown) => void;
  /** Expose inspection data for agent testing */
  onInspect?: (inspection: A2UIInspection) => void;
  /** Override initial scene */
  initialScene?: string;
}

export default function A2UIRenderer({
  experience,
  onAction,
  onInspect,
  initialScene,
}: A2UIRendererProps) {
  // Initialize data model from experience
  const initialDataModel = useMemo(() => {
    const model: Record<string, unknown> = {};
    for (const [key, def] of Object.entries(experience.dataModel)) {
      model[key] = def.initial;
    }
    return model;
  }, [experience]);

  const [state, setState] = useState<RendererState>({
    currentSceneId: initialScene ?? experience.scenes[0]?.id ?? "void",
    dataModel: initialDataModel,
    sceneStartTime: Date.now(),
    elapsed: 0,
  });

  // Find current scene
  const currentScene = useMemo(
    () => experience.scenes.find((s) => s.id === state.currentSceneId),
    [experience, state.currentSceneId]
  );

  // Scene transition handler
  const transitionTo = useCallback(
    (sceneId: string) => {
      setState((prev) => ({
        ...prev,
        currentSceneId: sceneId,
        sceneStartTime: Date.now(),
        elapsed: 0,
      }));
    },
    []
  );

  // Action handler
  const handleAction = useCallback(
    (eventName: string, data?: unknown) => {
      // Check if this action triggers a scene transition
      // Match: event "void_click" against trigger target "void-sphere" (contains check)
      // or exact match with _click suffix
      const currentIdx = experience.scenes.findIndex(
        (s) => s.id === state.currentSceneId
      );
      const currentScene = experience.scenes[currentIdx];
      // Match click trigger: exact target match or known void_click event
      const triggerTarget = currentScene?.trigger?.target;
      const isClickTrigger =
        currentScene?.trigger?.type === "click" &&
        (eventName === `${triggerTarget}_click` ||
         eventName === "void_click");

      if (isClickTrigger && currentIdx < experience.scenes.length - 1) {
        transitionTo(experience.scenes[currentIdx + 1].id);
      }
      onAction?.(eventName, data);
    },
    [experience, state.currentSceneId, transitionTo, onAction]
  );

  // Auto-transition for timed scenes
  useEffect(() => {
    if (!currentScene?.duration) return;

    const timer = setTimeout(() => {
      const currentIdx = experience.scenes.findIndex(
        (s) => s.id === state.currentSceneId
      );
      const nextScene = experience.scenes[currentIdx + 1];
      if (nextScene?.transition?.auto) {
        transitionTo(nextScene.id);
      }
    }, currentScene.duration);

    return () => clearTimeout(timer);
  }, [currentScene, experience, state.currentSceneId, transitionTo]);

  // Expose inspection data
  useEffect(() => {
    if (!onInspect || !currentScene) return;

    const inspection: A2UIInspection = {
      experienceId: experience.experienceId,
      currentScene: state.currentSceneId,
      activeComponents: currentScene.components.map((c) => ({
        id: c.id,
        component: c.component,
        props: Object.fromEntries(
          Object.entries(c).filter(([k]) => k !== "id" && k !== "component")
        ),
      })),
      dataModel: state.dataModel,
      elapsed: (Date.now() - state.sceneStartTime) / 1000,
      catalogValid: validateExperience(experience).valid,
    };

    onInspect(inspection);
  }, [currentScene, experience, state, onInspect]);

  // Render components for current scene
  if (!currentScene) {
    return (
      <div className="text-red-500 font-mono text-sm p-4">
        A2UI Error: Scene &quot;{state.currentSceneId}&quot; not found
      </div>
    );
  }

  return (
    <div data-a2ui-scene={currentScene.id} data-a2ui-experience={experience.experienceId}>
      {currentScene.components.map((instance) => {
        const Renderer = componentRegistry[instance.component];
        if (!Renderer) {
          // Unregistered component — render placeholder for development
          return (
            <div
              key={instance.id}
              data-a2ui-component={instance.component}
              data-a2ui-id={instance.id}
              className="text-yellow-500 font-mono text-[10px] p-1"
            >
              [{instance.component}: {instance.id}]
            </div>
          );
        }
        return (
          <Renderer
            key={instance.id}
            instance={instance}
            state={state}
            onAction={handleAction}
          />
        );
      })}
    </div>
  );
}
