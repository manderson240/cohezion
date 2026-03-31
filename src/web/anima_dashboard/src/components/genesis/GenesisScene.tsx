"use client";

import React, { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Stars, Html, Line } from "@react-three/drei";
import {
  EffectComposer,
  Bloom,
  Vignette,
  ChromaticAberration,
} from "@react-three/postprocessing";
import { BlendFunction } from "postprocessing";
import * as THREE from "three";
import EquationPanel, { cosmogonyEquations } from "./EquationPanel";
import ExplosionParticles, { type ExplosionPhase } from "./ExplosionParticles";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

// --- Types ---

interface CosmogonyData {
  temperature: number;
  symmetry: string;
  stage: number;
  order_parameters: Record<string, number>;
  transitions: Array<{
    from: string;
    to: string;
    T_critical: number;
    stage: number;
  }>;
  fisher_eigenvalue_max: number;
  landau_free_energy: number;
}

// --- Color palette per fabric ---
const FABRIC_COLORS_MAP = {
  Space: new THREE.Color("#3b82f6"),
  Field: new THREE.Color("#f59e0b"),
  Control: new THREE.Color("#10b981"),
  Precipitation: new THREE.Color("#a855f7"),
};

// Fabric centers for fiber strands (matches ExplosionParticles)
const FABRIC_CENTERS = [
  new THREE.Vector3(3, 0, 0),     // Space
  new THREE.Vector3(-2, 2, 0),    // Field
  new THREE.Vector3(0, -2, 2),    // Control
  new THREE.Vector3(-1, -1, -3),  // Precipitation
];

const FABRIC_HEX_COLORS = ["#3b82f6", "#f59e0b", "#10b981", "#a855f7"];
const FABRIC_LABELS = ["Space", "Field", "Control", "Precipitation"];

// ============================================================
// Part 1: THE VOID (before click state)
// ============================================================

/** Pulsing sphere + large invisible click target + hover ring affordance */
function VoidSphere({
  active,
  onClick,
}: {
  active: boolean;
  onClick: () => void;
}) {
  const glowRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);
  const [hovered, setHovered] = useState(false);

  useFrame((state) => {
    if (!active) return;
    const t = state.clock.getElapsedTime();
    // Visible glow sphere — pulsing between 0.03 and 0.08
    if (glowRef.current) {
      const scale = 0.055 + Math.sin(t * 0.5) * 0.025;
      glowRef.current.scale.setScalar(scale);
      const mat = glowRef.current.material as THREE.MeshBasicMaterial;
      mat.opacity = hovered ? 0.6 : 0.25 + Math.sin(t * 0.7) * 0.1;
    }
    // Hover ring — pulsing opacity
    if (ringRef.current) {
      const mat = ringRef.current.material as THREE.MeshBasicMaterial;
      mat.opacity = hovered
        ? 0.15 + Math.sin(t * 2) * 0.05
        : 0.04 + Math.sin(t * 0.8) * 0.02;
      ringRef.current.rotation.z = t * 0.1;
    }
  });

  if (!active) return null;

  return (
    <group>
      {/* Large invisible click target — catches clicks near center */}
      <mesh
        onClick={onClick}
        onPointerOver={() => {
          setHovered(true);
          document.body.style.cursor = "pointer";
        }}
        onPointerOut={() => {
          setHovered(false);
          document.body.style.cursor = "auto";
        }}
      >
        <sphereGeometry args={[2, 16, 16]} />
        <meshBasicMaterial transparent opacity={0} depthWrite={false} />
      </mesh>

      {/* Visible pulsing glow sphere */}
      <mesh ref={glowRef}>
        <sphereGeometry args={[1, 32, 32]} />
        <meshBasicMaterial
          color="#ffffff"
          transparent
          opacity={0.25}
          toneMapped={false}
        />
      </mesh>

      {/* Hover ring affordance */}
      <mesh ref={ringRef} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[0.8, 0.008, 16, 64]} />
        <meshBasicMaterial
          color="#ffffff"
          transparent
          opacity={0.04}
          toneMapped={false}
        />
      </mesh>

      {/* "click to begin" text below the void */}
      <Html position={[0, -1.2, 0]} center>
        <div
          style={{
            color: hovered ? "rgba(255,255,255,0.7)" : "rgba(255,255,255,0.3)",
            fontFamily: "monospace",
            fontSize: "12px",
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            transition: "color 0.3s",
            userSelect: "none",
            whiteSpace: "nowrap",
          }}
        >
          click to begin
        </div>
      </Html>
    </group>
  );
}

/** 100 dust particles drifting around center — zero-point fluctuations */
function VoidDust({ active }: { active: boolean }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  // Seed random positions and drift velocities
  const dustData = useMemo(() => {
    const data: { pos: THREE.Vector3; vel: THREE.Vector3 }[] = [];
    for (let i = 0; i < 100; i++) {
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const r = Math.random() * 5;
      data.push({
        pos: new THREE.Vector3(
          Math.sin(phi) * Math.cos(theta) * r,
          Math.sin(phi) * Math.sin(theta) * r,
          Math.cos(phi) * r
        ),
        vel: new THREE.Vector3(
          (Math.random() - 0.5) * 0.02,
          (Math.random() - 0.5) * 0.02,
          (Math.random() - 0.5) * 0.02
        ),
      });
    }
    return data;
  }, []);

  useFrame(() => {
    if (!meshRef.current || !active) return;
    for (let i = 0; i < 100; i++) {
      const d = dustData[i];
      d.pos.add(d.vel);
      // Wrap back if too far
      if (d.pos.length() > 5) {
        d.pos.multiplyScalar(0.1);
      }
      dummy.position.copy(d.pos);
      dummy.scale.setScalar(0.002);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
    }
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  if (!active) return null;

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, 100]}>
      <sphereGeometry args={[1, 4, 4]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0.08} toneMapped={false} />
    </instancedMesh>
  );
}

/** Void quote overlay — pulsing opacity */
function VoidQuote({ active }: { active: boolean }) {
  const [opacity, setOpacity] = useState(0.3);

  useEffect(() => {
    if (!active) return;
    let frameId: number;
    const animate = () => {
      const t = performance.now() / 1000;
      setOpacity(0.3 + Math.sin(t * 0.8) * 0.15);
      frameId = requestAnimationFrame(animate);
    };
    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [active]);

  if (!active) return null;

  return (
    <Html position={[0, 1.5, 0]} center>
      <div
        className="font-mono text-sm text-center select-none max-w-xs"
        style={{
          color: "#444",
          opacity,
          transition: "opacity 0.1s",
        }}
      >
        In the beginning, there was nothing. Not even nothing.
      </div>
    </Html>
  );
}

// ============================================================
// Part 2: CAMERA SHAKE (during explosion)
// ============================================================

function CameraShake({
  active,
  startTime,
}: {
  active: boolean;
  startTime: number;
}) {
  const { camera } = useThree();
  const basePosRef = useRef(new THREE.Vector3(0, 0, 5));

  useFrame(() => {
    if (!active) {
      return;
    }
    const elapsed = (performance.now() - startTime) / 1000;

    // Shake for 0.5s after explosion start
    if (elapsed < 0.5) {
      const amplitude = 0.05 * (1 - elapsed / 0.5);
      const freq = 20;
      camera.position.x =
        basePosRef.current.x + Math.sin(elapsed * freq * Math.PI * 2) * amplitude;
      camera.position.y =
        basePosRef.current.y + Math.cos(elapsed * freq * Math.PI * 2 * 1.3) * amplitude;
    } else if (elapsed < 1.0) {
      // Settle back to base
      camera.position.x = THREE.MathUtils.lerp(
        camera.position.x,
        basePosRef.current.x,
        0.1
      );
      camera.position.y = THREE.MathUtils.lerp(
        camera.position.y,
        basePosRef.current.y,
        0.1
      );
    }
  });

  return null;
}

// ============================================================
// Part 3: CAMERA PULLBACK (settling phase)
// ============================================================

function CameraPullback({ active, elapsed }: { active: boolean; elapsed: number }) {
  const { camera } = useThree();

  useFrame(() => {
    if (!active) return;
    // Over seconds 5-10, pull camera.z from 5 to 8
    const settleProgress = Math.min((elapsed - 5) / 5, 1.0);
    if (settleProgress > 0) {
      const targetZ = 5 + settleProgress * 3;
      camera.position.z = THREE.MathUtils.lerp(camera.position.z, targetZ, 0.02);
    }
  });

  return null;
}

// ============================================================
// Part 3: FABRIC FRAGMENTS (dodecahedrons that scale in)
// ============================================================

function FabricFragment({
  index,
  active,
  axisSelected,
  scaleProgress,
}: {
  index: number;
  active: boolean;
  axisSelected: boolean;
  scaleProgress: number; // 0-1, how visible this is
}) {
  const ref = useRef<THREE.Mesh>(null);
  const colors = [
    FABRIC_COLORS_MAP.Space,
    FABRIC_COLORS_MAP.Field,
    FABRIC_COLORS_MAP.Control,
    FABRIC_COLORS_MAP.Precipitation,
  ];

  const center = FABRIC_CENTERS[index];

  useFrame((state) => {
    if (!ref.current || !active) return;
    const t = state.clock.getElapsedTime();

    // Orbit gently around fabric center
    const orbRadius = 0.3;
    const orbAngle = t * 0.4 + index * 1.5;
    ref.current.position.set(
      center.x + Math.cos(orbAngle) * orbRadius,
      center.y + Math.sin(t * 0.3 + index) * 0.15,
      center.z + Math.sin(orbAngle) * orbRadius
    );

    // Scale in from 0
    const s = 0.6 * scaleProgress;
    if (axisSelected) {
      ref.current.scale.set(s * 2, s, s);
      ref.current.rotation.z = orbAngle;
    } else {
      ref.current.scale.setScalar(s);
    }
    ref.current.rotation.y = t * 0.5;
  });

  if (!active || scaleProgress <= 0) return null;

  return (
    <group>
      <mesh ref={ref} position={center}>
        <dodecahedronGeometry args={[0.5, 1]} />
        <meshPhysicalMaterial
          color={colors[index]}
          emissive={colors[index]}
          emissiveIntensity={0.4}
          transparent
          opacity={0.8 * scaleProgress}
          roughness={0.3}
        />
      </mesh>
      {scaleProgress > 0.5 && (
        <Html
          position={[center.x, center.y + 0.8, center.z]}
          center
        >
          <span
            className="text-[10px] font-mono text-gray-300"
            style={{ opacity: 0.7 * scaleProgress }}
          >
            {FABRIC_LABELS[index]}
          </span>
        </Html>
      )}
    </group>
  );
}

// ============================================================
// FIBER STRANDS — catenary curves from center to each fabric
// ============================================================

function FiberStrand({
  index,
  active,
  brightness,
}: {
  index: number;
  active: boolean;
  brightness: number; // 0-1
}) {
  const points = useMemo(() => {
    const origin = new THREE.Vector3(0, 0, 0);
    const target = FABRIC_CENTERS[index];
    const pts: THREE.Vector3[] = [];
    const segments = 32;
    for (let i = 0; i <= segments; i++) {
      const t = i / segments;
      // Lerp + catenary sag
      const p = new THREE.Vector3().lerpVectors(origin, target, t);
      // Add a catenary sag (deepest at midpoint)
      const sag = -0.5 * Math.sin(t * Math.PI);
      p.y += sag;
      pts.push(p);
    }
    return pts;
  }, [index]);

  if (!active || brightness <= 0) return null;

  return (
    <Line
      points={points}
      color={FABRIC_HEX_COLORS[index]}
      lineWidth={1.5 * brightness}
      transparent
      opacity={0.4 * brightness}
    />
  );
}

// ============================================================
// MINI BLOCH SPHERES (appear during settling)
// ============================================================

function MiniBlochSphere({
  index,
  active,
  scaleProgress,
}: {
  index: number;
  active: boolean;
  scaleProgress: number;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const center = FABRIC_CENTERS[index];

  useFrame((state) => {
    if (!ref.current || !active) return;
    ref.current.rotation.y = state.clock.getElapsedTime() * 0.5;
    ref.current.scale.setScalar(0.3 * scaleProgress);
  });

  if (!active || scaleProgress <= 0) return null;

  return (
    <mesh ref={ref} position={center}>
      <sphereGeometry args={[1, 16, 16]} />
      <meshBasicMaterial
        color={FABRIC_HEX_COLORS[index]}
        wireframe
        transparent
        opacity={0.5 * scaleProgress}
      />
    </mesh>
  );
}

// ============================================================
// HIHO TORUS — materializes at origin during settling
// ============================================================

function HIHOTorus({
  active,
  scaleProgress,
}: {
  active: boolean;
  scaleProgress: number;
}) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!ref.current || !active) return;
    const t = state.clock.getElapsedTime();
    const pulse = scaleProgress * (1.0 + Math.sin(t * 2) * 0.05);
    ref.current.scale.setScalar(pulse);
  });

  if (!active || scaleProgress <= 0) return null;

  return (
    <group>
      <mesh ref={ref} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.5, 0.08, 16, 64]} />
        <meshBasicMaterial
          color="#ffd700"
          transparent
          opacity={0.7 * scaleProgress}
          toneMapped={false}
        />
      </mesh>
      {/* Center glow */}
      <mesh scale={[scaleProgress * 0.15, scaleProgress * 0.15, scaleProgress * 0.15]}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color="#ffd700" transparent opacity={0.9 * scaleProgress} toneMapped={false} />
      </mesh>
      {scaleProgress > 0.5 && (
        <Html position={[0, 0.5, 0]} center>
          <div
            className="text-yellow-500 font-mono text-xs font-bold"
            style={{ opacity: scaleProgress }}
          >
            HIHO = 0.5
          </div>
        </Html>
      )}
    </group>
  );
}

// ============================================================
// STARS WRAPPER — fades in after explosion
// ============================================================

function FadingStars({ opacity }: { opacity: number }) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame(() => {
    if (!groupRef.current) return;
    // Stars component doesn't have opacity; we control via group
    groupRef.current.visible = opacity > 0.01;
  });

  if (opacity <= 0.01) return null;

  return (
    <group ref={groupRef}>
      <Stars
        radius={50}
        depth={50}
        count={1000}
        factor={2}
        fade
        speed={0.5}
      />
    </group>
  );
}

// ============================================================
// DYNAMIC POSTPROCESSING
// ============================================================

function DynamicEffects({
  bloomIntensity,
  chromaticOffset,
}: {
  bloomIntensity: number;
  chromaticOffset: number;
}) {
  const offsetVec = useMemo(
    () => new THREE.Vector2(chromaticOffset, chromaticOffset),
    [chromaticOffset]
  );

  return (
    <EffectComposer>
      <Bloom
        intensity={bloomIntensity}
        luminanceThreshold={0.15}
        luminanceSmoothing={0.9}
      />
      <Vignette
        offset={0.3}
        darkness={0.7}
        blendFunction={BlendFunction.NORMAL}
      />
      <ChromaticAberration
        offset={offsetVec}
        blendFunction={BlendFunction.NORMAL}
      />
    </EffectComposer>
  );
}

// ============================================================
// TEMPERATURE DISPLAY
// ============================================================

function TemperatureDisplay({
  temperature,
  symmetry,
  visible,
}: {
  temperature: number;
  symmetry: string;
  visible: boolean;
}) {
  if (!visible) return null;

  return (
    <div className="absolute top-4 left-4 font-mono">
      <h2 className="text-lg text-green-400 font-bold">Genesis</h2>
      <p className="text-[10px] text-gray-500 mb-2">From Nothing to Everything</p>
      <div className="text-sm text-gray-300">
        T = <span className="text-cyan-400">{temperature.toFixed(2)}</span>
      </div>
      <div className="text-sm text-gray-300">
        Symmetry: <span className="text-yellow-400">{symmetry}</span>
      </div>
    </div>
  );
}

// ============================================================
// NARRATIVE CAPTIONS
// ============================================================

const NARRATIVES: Record<string, string> = {
  void: "In the beginning, there was nothing. Not even nothing.",
  "SO(12)":
    "From the first observation, symmetry crystallized. Twelve dimensions, all equivalent.",
  "SO(3)^4": "The fabrics separated. Space. Field. Control. Precipitation.",
  "U(1)^4": "Within each world, a preferred direction emerged.",
  "Z_2^4":
    "The discrete choice. Up or down. Brahmagupta's zero gave nothing a name.",
  HIHO: "At the still point, the dance began. Half in, half out. The balance that creates.",
};

// ============================================================
// MAIN COMPONENT
// ============================================================

export interface GenesisSceneProps {
  /** Called when the void phase begins (page loads) */
  onVoidStart?: () => void;
  /** Called when the user clicks the void sphere (explosion) */
  onExplosion?: () => void;
  /** Called when fabrics begin differentiating (~2s) */
  onFabricSplit?: () => void;
  /** Called when the settling phase begins (~5s) */
  onSettle?: () => void;
}

export default function GenesisScene({
  onVoidStart,
  onExplosion,
  onFabricSplit,
  onSettle,
}: GenesisSceneProps = {}) {
  const [temperature, setTemperature] = useState(200.0);
  const [cosmogonyData, setCosmogonyData] = useState<CosmogonyData | null>(null);
  const [hasInteracted, setHasInteracted] = useState(false);
  const [animElapsed, setAnimElapsed] = useState(0); // seconds since click

  const symmetry = cosmogonyData?.symmetry ?? "void";
  const stage = cosmogonyData?.stage ?? -1;

  // --- Cinematic phase tracking ---
  const explosionPhase: ExplosionPhase = useMemo(() => {
    if (!hasInteracted) return "idle";
    if (animElapsed < 2) return "exploding";
    if (animElapsed < 5) return "differentiating";
    if (animElapsed < 10) return "settling";
    return "final";
  }, [hasInteracted, animElapsed]);

  // Dynamic bloom intensity: 0.6 base, surge to 3.0 on explosion, ease to 0.8
  const bloomIntensity = useMemo(() => {
    if (!hasInteracted) return 0.6;
    if (animElapsed < 0.1) return 3.0;
    if (animElapsed < 2.0) {
      // Ease from 3.0 back to 1.0 over 2 seconds
      const t = animElapsed / 2.0;
      return 3.0 + (1.0 - 3.0) * t;
    }
    if (animElapsed < 10) {
      // Settle from 1.0 to 0.8
      const t = (animElapsed - 2) / 8;
      return 1.0 + (0.8 - 1.0) * t;
    }
    return 0.8;
  }, [hasInteracted, animElapsed]);

  // Chromatic aberration: on during explosion, fade out over 2s
  const chromaticOffset = useMemo(() => {
    if (!hasInteracted) return 0;
    if (animElapsed < 2.0) {
      const t = animElapsed / 2.0;
      return 0.003 * (1 - t);
    }
    return 0;
  }, [hasInteracted, animElapsed]);

  // Stars opacity: fade in after 1 second
  const starsOpacity = useMemo(() => {
    if (!hasInteracted) return 0;
    if (animElapsed < 1.0) return 0;
    if (animElapsed < 2.0) return (animElapsed - 1.0); // 0->1 over 1 second
    return 1.0;
  }, [hasInteracted, animElapsed]);

  // Fabric fragment scale: appear during settling (seconds 5-8)
  const fabricScaleProgress = useMemo(() => {
    if (animElapsed < 5) return 0;
    if (animElapsed < 8) return (animElapsed - 5) / 3;
    return 1.0;
  }, [animElapsed]);

  // Bloch sphere + HIHO torus scale: appear during seconds 6-9
  const blochScaleProgress = useMemo(() => {
    if (animElapsed < 6) return 0;
    if (animElapsed < 9) return (animElapsed - 6) / 3;
    return 1.0;
  }, [animElapsed]);

  // Fiber strand brightness: appear during differentiation (seconds 3-6), solidify (6-10)
  const fiberBrightness = useMemo(() => {
    if (animElapsed < 3) return 0;
    if (animElapsed < 6) return (animElapsed - 3) / 3;
    if (animElapsed < 10) {
      return 0.7 + ((animElapsed - 6) / 4) * 0.3;
    }
    return 1.0;
  }, [animElapsed]);

  // UI visibility: sidebar panels fade in after settling
  const uiOpacity = useMemo(() => {
    if (!hasInteracted) return 0;
    if (animElapsed < 8) return 0;
    if (animElapsed < 10) return (animElapsed - 8) / 2;
    return 1.0;
  }, [hasInteracted, animElapsed]);

  // Explosion start time (for camera shake)
  const explosionStartTimeRef = useRef(0);

  // Track which cinematic callbacks have fired (so we fire each once)
  const firedCallbacksRef = useRef({ fabricSplit: false, settle: false });

  // --- Landau computation (offline fallback) ---
  const computeLocalCosmogony = useCallback((temp: number): CosmogonyData => {
    const criticalTemps = [100, 10, 1.0, 0.1, 0.01];
    const symmetries = ["void", "SO(12)", "SO(3)^4", "U(1)^4", "Z_2^4", "HIHO"];

    let stageIdx = 0;
    for (let i = 0; i < criticalTemps.length; i++) {
      if (temp < criticalTemps[i]) stageIdx = i + 1;
    }
    const sym = symmetries[stageIdx];
    const stg = stageIdx - 1;

    const a = 1.0;
    const b = 0.5;
    const criticalTemp = criticalTemps[Math.max(0, stageIdx - 1)] ?? 100;
    const orderParameter =
      temp < criticalTemp
        ? Math.sqrt((a * (criticalTemp - temp)) / (2 * b))
        : 0;
    const landauFreeEnergy =
      orderParameter > 0
        ? a * (temp - criticalTemp) * orderParameter ** 2 +
          b * orderParameter ** 4
        : 0;

    const closestTc = criticalTemps.reduce((closest, tc) =>
      Math.abs(tc - temp) < Math.abs(closest - temp) ? tc : closest
    );
    const fisherEig =
      closestTc > 0 ? 1 / (Math.abs(temp - closestTc) + 0.01) : 0;

    const transitionNames = ["SO(12)", "SO(3)^4", "U(1)^4", "Z_2^4", "HIHO"];
    const transitions = criticalTemps
      .filter((tc) => temp < tc)
      .map((tc, i) => ({
        from: i === 0 ? "void" : transitionNames[i - 1],
        to: transitionNames[i],
        T_critical: tc,
        stage: i,
      }));

    return {
      temperature: temp,
      symmetry: sym,
      stage: stg,
      order_parameters: { fabric_differentiation: orderParameter },
      transitions,
      fisher_eigenvalue_max: fisherEig,
      landau_free_energy: landauFreeEnergy,
    };
  }, []);

  // Compute cosmogony state locally (Landau math, no API needed)
  const fetchState = useCallback(
    (temp: number) => {
      setCosmogonyData(computeLocalCosmogony(temp));
    },
    [computeLocalCosmogony]
  );

  useEffect(() => {
    const timer = setTimeout(() => fetchState(temperature), 100);
    return () => clearTimeout(timer);
  }, [temperature, fetchState]);

  // Initial fetch + trigger void start
  useEffect(() => {
    fetchState(200.0);
    onVoidStart?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchState]);

  // --- Animation state for the cosmogonic cooling sequence ---
  const animFrameRef = useRef<number | null>(null);
  const animStartRef = useRef<number>(0);
  const ANIM_DURATION = 10000; // 10 seconds
  const TEMP_START = 200;
  const TEMP_END = 0.01;

  // The first interaction IS the first distinction — "It from Bit"
  const handleFirstInteraction = useCallback(() => {
    if (!hasInteracted) {
      setHasInteracted(true);
      explosionStartTimeRef.current = performance.now();
      onExplosion?.();

      animStartRef.current = performance.now();

      const animate = (now: number) => {
        const elapsed = now - animStartRef.current;
        const elapsedSec = elapsed / 1000;
        const progress = Math.min(elapsed / ANIM_DURATION, 1.0);

        // Exponential cooling: T = T_start * (T_end/T_start)^progress
        const newTemp =
          TEMP_START * Math.pow(TEMP_END / TEMP_START, progress);
        setTemperature(newTemp);
        setAnimElapsed(elapsedSec);

        // Fire cinematic callbacks at phase boundaries
        if (elapsedSec >= 2 && !firedCallbacksRef.current.fabricSplit) {
          firedCallbacksRef.current.fabricSplit = true;
          onFabricSplit?.();
        }
        if (elapsedSec >= 5 && !firedCallbacksRef.current.settle) {
          firedCallbacksRef.current.settle = true;
          onSettle?.();
        }

        if (progress < 1.0) {
          animFrameRef.current = requestAnimationFrame(animate);
        } else {
          setAnimElapsed(10);
          animFrameRef.current = null;
        }
      };

      animFrameRef.current = requestAnimationFrame(animate);
    }
  }, [hasInteracted]);

  // Cleanup animation on unmount
  useEffect(() => {
    return () => {
      if (animFrameRef.current !== null) {
        cancelAnimationFrame(animFrameRef.current);
      }
    };
  }, []);

  const narrative = NARRATIVES[symmetry] ?? "";

  const equations = useMemo(
    () =>
      cosmogonyEquations({
        temperature,
        symmetry,
        orderParam:
          cosmogonyData?.order_parameters?.fabric_differentiation ?? 0,
        freeEnergy: cosmogonyData?.landau_free_energy ?? 0,
      }),
    [temperature, symmetry, cosmogonyData]
  );

  return (
    <div className="relative w-full h-[700px] bg-black rounded-xl overflow-hidden border border-gray-800">
      {/* 3D Canvas */}
      <Canvas camera={{ position: [0, 0, 5], fov: 50 }}>
        {/* Minimal lighting — let bloom do the work */}
        <ambientLight intensity={0.05} />
        <pointLight position={[5, 5, 5]} intensity={0.3} color="#4488ff" />

        {/* Part 1: The Void */}
        <VoidSphere active={!hasInteracted} onClick={handleFirstInteraction} />
        <VoidDust active={!hasInteracted} />
        <VoidQuote active={!hasInteracted} />

        {/* Stars — fade in after explosion */}
        <FadingStars opacity={starsOpacity} />

        {/* Part 2: Explosion particles */}
        <ExplosionParticles phase={explosionPhase} elapsed={animElapsed} />

        {/* Camera shake during explosion */}
        <CameraShake
          active={hasInteracted && animElapsed < 1.0}
          startTime={explosionStartTimeRef.current}
        />

        {/* Camera pullback during settling */}
        <CameraPullback
          active={hasInteracted && animElapsed >= 5}
          elapsed={animElapsed}
        />

        {/* Part 3: Fiber strands */}
        {[0, 1, 2, 3].map((i) => (
          <FiberStrand
            key={`fiber-${i}`}
            index={i}
            active={fiberBrightness > 0}
            brightness={fiberBrightness}
          />
        ))}

        {/* Part 4: Fabric fragments (dodecahedrons) */}
        {[0, 1, 2, 3].map((i) => (
          <FabricFragment
            key={`fabric-${i}`}
            index={i}
            active={fabricScaleProgress > 0}
            axisSelected={stage >= 2}
            scaleProgress={fabricScaleProgress}
          />
        ))}

        {/* Mini Bloch spheres at fabric centers */}
        {[0, 1, 2, 3].map((i) => (
          <MiniBlochSphere
            key={`bloch-${i}`}
            index={i}
            active={blochScaleProgress > 0}
            scaleProgress={blochScaleProgress}
          />
        ))}

        {/* HIHO torus at origin */}
        <HIHOTorus
          active={blochScaleProgress > 0}
          scaleProgress={blochScaleProgress}
        />

        {/* OrbitControls — disabled during void, enabled after */}
        <OrbitControls
          enablePan={false}
          enabled={hasInteracted}
          autoRotate={hasInteracted && animElapsed > 3}
          autoRotateSpeed={0.2}
        />

        {/* Dynamic post-processing */}
        <DynamicEffects
          bloomIntensity={bloomIntensity}
          chromaticOffset={chromaticOffset}
        />
      </Canvas>

      {/* Temperature display — always visible but minimal */}
      <TemperatureDisplay
        temperature={temperature}
        symmetry={symmetry}
        visible={hasInteracted}
      />

      {/* Temperature slider (fades in during settling) */}
      {uiOpacity > 0 && (
        <div
          className="absolute bottom-20 left-1/2 -translate-x-1/2 w-[80%] max-w-lg"
          style={{ opacity: uiOpacity, transition: "opacity 0.3s" }}
        >
          <div className="flex justify-between text-[10px] font-mono text-gray-500 mb-1">
            <span>HIHO (cold)</span>
            <span>Void (hot)</span>
          </div>
          <input
            type="range"
            min={0.005}
            max={200}
            step={0.1}
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
            className="w-full accent-green-500 h-2"
          />
          <div className="relative h-2 mt-1">
            {[0.01, 0.1, 1.0, 10.0, 100.0].map((tc) => {
              const pct = (tc / 200) * 100;
              return (
                <div
                  key={tc}
                  className="absolute w-1 h-2 bg-yellow-500/60"
                  style={{ left: `${pct}%` }}
                  title={`T_c = ${tc}`}
                />
              );
            })}
          </div>
        </div>
      )}

      {/* Narrative caption */}
      {hasInteracted && narrative && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center font-mono text-xs text-gray-400 italic max-w-md">
          &quot;{narrative}&quot;
        </div>
      )}

      {/* Equation panel — hidden during void, fades in after settling */}
      {uiOpacity > 0 && (
        <div style={{ opacity: uiOpacity, transition: "opacity 0.3s" }}>
          <EquationPanel
            title="Cosmogony"
            equations={equations}
            className="absolute top-4 right-4 w-72"
            defaultCollapsed={false}
          />
        </div>
      )}

      {/* Phase transition markers — hidden during void */}
      {uiOpacity > 0 &&
        cosmogonyData &&
        cosmogonyData.transitions.length > 0 && (
          <div
            className="absolute top-4 right-[320px] bg-black/80 border border-gray-700 rounded-lg p-3 font-mono text-[10px] text-gray-400 w-48"
            style={{ opacity: uiOpacity, transition: "opacity 0.3s" }}
          >
            <div className="text-green-400 font-bold mb-2 text-xs">
              Transitions
            </div>
            {cosmogonyData.transitions.map((t, i) => (
              <div key={i} className="mb-1">
                <span className="text-yellow-400">{t.from}</span>
                <span className="text-gray-600"> &rarr; </span>
                <span className="text-cyan-400">{t.to}</span>
                <span className="text-gray-600"> @ T={t.T_critical}</span>
              </div>
            ))}
          </div>
        )}
    </div>
  );
}
