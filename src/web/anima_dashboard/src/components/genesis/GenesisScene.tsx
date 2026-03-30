"use client";

import React, { useState, useRef, useCallback, useEffect, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Stars, Html } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import * as THREE from "three";
import EquationPanel, { cosmogonyEquations } from "./EquationPanel";

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
const FABRIC_COLORS = {
  Space: new THREE.Color("#4488ff"),
  Field: new THREE.Color("#ffaa22"),
  Control: new THREE.Color("#22ff88"),
  Precipitation: new THREE.Color("#aa44ff"),
};

// --- Stage -1: The Void ---

function VoidPulse({ active }: { active: boolean }) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!ref.current || !active) return;
    // Barely perceptible zero-point fluctuation
    const t = state.clock.getElapsedTime();
    const scale = 0.01 + Math.sin(t * 0.5) * 0.005;
    ref.current.scale.setScalar(scale);
    const mat = ref.current.material as THREE.MeshBasicMaterial;
    mat.opacity = 0.1 + Math.sin(t * 0.7) * 0.05;
  });

  if (!active) return null;

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[1, 32, 32]} />
      <meshBasicMaterial color="#ffffff" transparent opacity={0.1} />
    </mesh>
  );
}

// --- Stage 0: The SO(12) Sphere ---

function SymmetrySphere({ active, breaking }: { active: boolean; breaking: boolean }) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!ref.current || !active) return;
    const t = state.clock.getElapsedTime();
    // Gentle breathing
    const scale = breaking ? 1.0 + Math.sin(t * 2) * 0.1 : 1.0 + Math.sin(t * 0.5) * 0.02;
    ref.current.scale.setScalar(scale);
    ref.current.rotation.y = t * 0.1;
  });

  if (!active) return null;

  return (
    <mesh ref={ref}>
      <icosahedronGeometry args={[1, 3]} />
      <meshPhysicalMaterial
        color="#ffffff"
        emissive="#224488"
        emissiveIntensity={0.3}
        wireframe={breaking}
        transparent
        opacity={breaking ? 0.6 : 0.9}
        roughness={0.2}
        metalness={0.3}
      />
    </mesh>
  );
}

// --- Stage 1: Four Fabric Fragments ---

function FabricFragment({
  index,
  active,
  axisSelected,
}: {
  index: number;
  active: boolean;
  axisSelected: boolean;
}) {
  const ref = useRef<THREE.Mesh>(null);
  const colors = [FABRIC_COLORS.Space, FABRIC_COLORS.Field, FABRIC_COLORS.Control, FABRIC_COLORS.Precipitation];
  const labels = ["Space", "Field", "Control", "Precipitation"];

  // Position: four quadrants
  const angle = (index / 4) * Math.PI * 2;
  const radius = 2.0;
  const basePos = new THREE.Vector3(
    Math.cos(angle) * radius,
    Math.sin(angle * 0.5) * 0.5,
    Math.sin(angle) * radius
  );

  useFrame((state) => {
    if (!ref.current || !active) return;
    const t = state.clock.getElapsedTime();
    // Orbit and breathe
    const orbAngle = angle + t * 0.2;
    ref.current.position.set(
      Math.cos(orbAngle) * radius,
      Math.sin(t * 0.3 + index) * 0.3,
      Math.sin(orbAngle) * radius
    );
    // If axis selected, elongate along one direction
    if (axisSelected) {
      const s = 0.6;
      ref.current.scale.set(s * 2, s, s);
      ref.current.rotation.z = orbAngle;
    } else {
      ref.current.scale.setScalar(0.6);
    }
    ref.current.rotation.y = t * 0.5;
  });

  if (!active) return null;

  return (
    <group>
      <mesh ref={ref} position={basePos}>
        <dodecahedronGeometry args={[0.5, 1]} />
        <meshPhysicalMaterial
          color={colors[index]}
          emissive={colors[index]}
          emissiveIntensity={0.4}
          transparent
          opacity={0.8}
          roughness={0.3}
        />
      </mesh>
      <Html position={basePos.clone().add(new THREE.Vector3(0, 0.8, 0))} center>
        <span className="text-[10px] font-mono text-gray-300 opacity-70">
          {labels[index]}
        </span>
      </Html>
    </group>
  );
}

// --- Stage 3: SPIN Bloch Spheres ---

function MiniBlochSphere({ index, active }: { index: number; active: boolean }) {
  const ref = useRef<THREE.Mesh>(null);
  const angle = (index / 4) * Math.PI * 2;
  const pos = new THREE.Vector3(
    Math.cos(angle) * 2,
    Math.sin(angle * 0.5) * 0.5,
    Math.sin(angle) * 2
  );

  useFrame((state) => {
    if (!ref.current || !active) return;
    ref.current.rotation.y = state.clock.getElapsedTime() * 0.5;
  });

  if (!active) return null;

  return (
    <mesh ref={ref} position={pos}>
      <sphereGeometry args={[0.2, 16, 16]} />
      <meshBasicMaterial color="#00ff00" wireframe transparent opacity={0.6} />
    </mesh>
  );
}

// --- Stage 4: HIHO Attractor ---

function HIHOAttractor({ active }: { active: boolean }) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (!ref.current || !active) return;
    const t = state.clock.getElapsedTime();
    const pulse = 1.0 + Math.sin(t * 2) * 0.05;
    ref.current.scale.setScalar(pulse);
  });

  if (!active) return null;

  return (
    <group>
      {/* Toroidal attractor ring */}
      <mesh ref={ref} rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1.5, 0.1, 16, 64]} />
        <meshBasicMaterial color="#00ff00" transparent opacity={0.8} />
      </mesh>
      {/* Center glow */}
      <mesh>
        <sphereGeometry args={[0.15, 16, 16]} />
        <meshBasicMaterial color="#00ff44" transparent opacity={0.9} />
      </mesh>
      <Html position={[0, 0.5, 0]} center>
        <div className="text-green-400 font-mono text-xs font-bold">
          HIHO = 0.5
        </div>
      </Html>
    </group>
  );
}

// --- Temperature Display ---

function TemperatureDisplay({ temperature, symmetry }: { temperature: number; symmetry: string }) {
  return (
    <div className="absolute top-4 left-4 font-mono">
      <h2 className="text-lg text-green-400 font-bold">Genesis</h2>
      <p className="text-[10px] text-gray-500 mb-2">
        From Nothing to Everything
      </p>
      <div className="text-sm text-gray-300">
        T = <span className="text-cyan-400">{temperature.toFixed(2)}</span>
      </div>
      <div className="text-sm text-gray-300">
        Symmetry: <span className="text-yellow-400">{symmetry}</span>
      </div>
    </div>
  );
}

// --- Narrative Captions ---

const NARRATIVES: Record<string, string> = {
  void: "In the beginning, there was nothing. Not even nothing.",
  "SO(12)": "From the first observation, symmetry crystallized. Twelve dimensions, all equivalent.",
  "SO(3)^4": "The fabrics separated. Space. Field. Control. Precipitation.",
  "U(1)^4": "Within each world, a preferred direction emerged.",
  "Z_2^4": "The discrete choice. Up or down. Brahmagupta's zero gave nothing a name.",
  HIHO: "At the still point, the dance began. Half in, half out. The balance that creates.",
};

// --- Main Component ---

export default function GenesisScene() {
  const [temperature, setTemperature] = useState(200.0);
  const [cosmogonyData, setCosmogonyData] = useState<CosmogonyData | null>(null);
  const [hasInteracted, setHasInteracted] = useState(false);

  const symmetry = cosmogonyData?.symmetry ?? "void";
  const stage = cosmogonyData?.stage ?? -1;

  // Local Landau computation for offline mode
  const computeLocalCosmogony = useCallback((temp: number): CosmogonyData => {
    // Critical temperatures for each symmetry-breaking stage
    const criticalTemps = [100, 10, 1.0, 0.1, 0.01];
    const symmetries = ["void", "SO(12)", "SO(3)^4", "U(1)^4", "Z_2^4", "HIHO"];

    // Determine stage by comparing temperature against critical thresholds
    let stageIdx = 0;
    for (let i = 0; i < criticalTemps.length; i++) {
      if (temp < criticalTemps[i]) stageIdx = i + 1;
    }
    const sym = symmetries[stageIdx];
    const stage = stageIdx - 1; // -1 for void, 0..4 for stages

    // Landau free energy: F(phi) = a*(T - T_c)*phi^2 + b*phi^4
    const a = 1.0;
    const b = 0.5;
    const criticalTemp = criticalTemps[Math.max(0, stageIdx - 1)] ?? 100;
    const orderParameter =
      temp < criticalTemp
        ? Math.sqrt(a * (criticalTemp - temp) / (2 * b))
        : 0;
    const landauFreeEnergy =
      orderParameter > 0
        ? a * (temp - criticalTemp) * orderParameter ** 2 + b * orderParameter ** 4
        : 0;

    // Fisher information eigenvalue (peaks near critical point)
    const closestTc = criticalTemps.reduce((closest, tc) =>
      Math.abs(tc - temp) < Math.abs(closest - temp) ? tc : closest
    );
    const fisherEig =
      closestTc > 0 ? 1 / (Math.abs(temp - closestTc) + 0.01) : 0;

    // Build transitions list for completed transitions
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
      stage,
      order_parameters: { fabric_differentiation: orderParameter },
      transitions,
      fisher_eigenvalue_max: fisherEig,
      landau_free_energy: landauFreeEnergy,
    };
  }, []);

  // Fetch cosmogony state from API, with local Landau fallback
  const fetchState = useCallback(async (temp: number) => {
    try {
      const resp = await fetch(`${API_BASE}/api/genesis/cosmogony/set-temperature`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ temperature: temp }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setCosmogonyData(data);
      } else {
        setCosmogonyData(computeLocalCosmogony(temp));
      }
    } catch {
      // Offline fallback — run Landau math locally
      setCosmogonyData(computeLocalCosmogony(temp));
    }
  }, [computeLocalCosmogony]);

  useEffect(() => {
    const timer = setTimeout(() => fetchState(temperature), 100);
    return () => clearTimeout(timer);
  }, [temperature, fetchState]);

  // Initial fetch
  useEffect(() => {
    fetchState(200.0);
  }, [fetchState]);

  // Animation state for the cosmogonic cooling sequence
  const animFrameRef = useRef<number | null>(null);
  const animStartRef = useRef<number>(0);
  const ANIM_DURATION = 10000; // 10 seconds
  const TEMP_START = 200;
  const TEMP_END = 0.01;

  // The first interaction IS the first distinction — "It from Bit"
  // On click, begin a 10-second cooling animation from T=200 down to T=0.01
  const handleFirstInteraction = useCallback(() => {
    if (!hasInteracted) {
      setHasInteracted(true);

      // Start the animation loop
      animStartRef.current = performance.now();

      const animate = (now: number) => {
        const elapsed = now - animStartRef.current;
        const progress = Math.min(elapsed / ANIM_DURATION, 1.0);
        // Exponential cooling: T = T_start * (T_end/T_start)^progress
        // This gives more time at high T and rapid descent at low T
        const newTemp = TEMP_START * Math.pow(TEMP_END / TEMP_START, progress);
        setTemperature(newTemp);

        if (progress < 1.0) {
          animFrameRef.current = requestAnimationFrame(animate);
        } else {
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
        orderParam: cosmogonyData?.order_parameters?.fabric_differentiation ?? 0,
        freeEnergy: cosmogonyData?.landau_free_energy ?? 0,
      }),
    [temperature, symmetry, cosmogonyData]
  );

  return (
    <div className="relative w-full h-[700px] bg-[#020208] rounded-xl overflow-hidden border border-gray-800">
      {/* 3D Canvas */}
      <Canvas
        camera={{ position: [0, 2, 5], fov: 50 }}
        onClick={handleFirstInteraction}
      >
        <ambientLight intensity={0.15} />
        <pointLight position={[5, 5, 5]} intensity={0.5} color="#4488ff" />
        <pointLight position={[-5, -3, -5]} intensity={0.3} color="#ff4488" />

        {/* Background stars */}
        <Stars radius={50} depth={50} count={1000} factor={2} fade speed={0.5} />

        {/* Stage -1: The Void */}
        <VoidPulse active={!hasInteracted} />

        {/* Stage 0: The Sphere */}
        <SymmetrySphere
          active={hasInteracted && stage >= 0 && stage < 2}
          breaking={stage === 1}
        />

        {/* Stage 1-2: Four Fabric Fragments */}
        {[0, 1, 2, 3].map((i) => (
          <FabricFragment
            key={i}
            index={i}
            active={stage >= 1}
            axisSelected={stage >= 2}
          />
        ))}

        {/* Stage 3: SPIN Bloch Spheres */}
        {[0, 1, 2, 3].map((i) => (
          <MiniBlochSphere key={i} index={i} active={stage >= 3} />
        ))}

        {/* Stage 4: HIHO Attractor */}
        <HIHOAttractor active={stage >= 4} />

        {/* Prompt to interact */}
        {!hasInteracted && (
          <Html center>
            <div className="text-gray-500 font-mono text-sm animate-pulse cursor-pointer select-none">
              Click to begin
            </div>
          </Html>
        )}

        <OrbitControls enablePan={false} autoRotate autoRotateSpeed={0.3} />

        <EffectComposer>
          <Bloom intensity={0.6} luminanceThreshold={0.2} luminanceSmoothing={0.9} />
        </EffectComposer>
      </Canvas>

      {/* Temperature display */}
      <TemperatureDisplay temperature={temperature} symmetry={symmetry} />

      {/* Temperature slider (appears after first interaction) */}
      {hasInteracted && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 w-[80%] max-w-lg">
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
          {/* Critical temperature markers */}
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
      {narrative && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-center font-mono text-xs text-gray-400 italic max-w-md">
          &quot;{narrative}&quot;
        </div>
      )}

      {/* Equation panel */}
      <EquationPanel
        title="Cosmogony"
        equations={equations}
        className="absolute top-4 right-4 w-72"
        defaultCollapsed={false}
      />

      {/* Phase transition markers */}
      {cosmogonyData && cosmogonyData.transitions.length > 0 && (
        <div className="absolute top-4 right-[320px] bg-black/80 border border-gray-700 rounded-lg p-3 font-mono text-[10px] text-gray-400 w-48">
          <div className="text-green-400 font-bold mb-2 text-xs">Transitions</div>
          {cosmogonyData.transitions.map((t, i) => (
            <div key={i} className="mb-1">
              <span className="text-yellow-400">{t.from}</span>
              <span className="text-gray-600"> → </span>
              <span className="text-cyan-400">{t.to}</span>
              <span className="text-gray-600"> @ T={t.T_critical}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
