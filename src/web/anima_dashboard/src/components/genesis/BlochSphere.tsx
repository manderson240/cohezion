"use client";

import React, { useState, useRef, useMemo, useCallback } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, Html, Line } from "@react-three/drei";
import { EffectComposer, Bloom } from "@react-three/postprocessing";
import * as THREE from "three";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

// --- Types ---

interface SpinorData {
  bloch_vector: number[];
  coherence: number;
  charge_polarity: number;
  spin_rotation: number;
  spin_precession: number;
  hiho_deviation: number;
}

// --- Bloch Sphere Wireframe ---

function SphereWireframe() {
  // Great circles: equator, two meridians
  const equator = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 64; i++) {
      const a = (i / 64) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(a), 0, Math.sin(a)));
    }
    return pts;
  }, []);

  const meridianXZ = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 64; i++) {
      const a = (i / 64) * Math.PI * 2;
      pts.push(new THREE.Vector3(Math.cos(a), Math.sin(a), 0));
    }
    return pts;
  }, []);

  const meridianYZ = useMemo(() => {
    const pts: THREE.Vector3[] = [];
    for (let i = 0; i <= 64; i++) {
      const a = (i / 64) * Math.PI * 2;
      pts.push(new THREE.Vector3(0, Math.sin(a), Math.cos(a)));
    }
    return pts;
  }, []);

  return (
    <group>
      {/* Translucent sphere */}
      <mesh>
        <sphereGeometry args={[1, 32, 32]} />
        <meshPhysicalMaterial
          color="#1a1a2e"
          transparent
          opacity={0.08}
          roughness={0.9}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Great circles */}
      <Line points={equator} color="#00ff88" lineWidth={1} opacity={0.4} transparent />
      <Line points={meridianXZ} color="#4488ff" lineWidth={1} opacity={0.3} transparent />
      <Line points={meridianYZ} color="#ff4488" lineWidth={1} opacity={0.3} transparent />

      {/* Axis labels */}
      <Html position={[1.2, 0, 0]} center>
        <span className="text-[10px] font-mono text-green-400 opacity-70">+x (Rotation)</span>
      </Html>
      <Html position={[-1.2, 0, 0]} center>
        <span className="text-[10px] font-mono text-green-400 opacity-50">-x</span>
      </Html>
      <Html position={[0, 1.2, 0]} center>
        <span className="text-[10px] font-mono text-blue-400 opacity-70">|↑⟩ (+z Charge)</span>
      </Html>
      <Html position={[0, -1.2, 0]} center>
        <span className="text-[10px] font-mono text-red-400 opacity-70">|↓⟩ (-z Charge)</span>
      </Html>
      <Html position={[0, 0, 1.2]} center>
        <span className="text-[10px] font-mono text-pink-400 opacity-70">+y (Precession)</span>
      </Html>

      {/* HIHO equatorial band glow */}
      <mesh rotation={[Math.PI / 2, 0, 0]}>
        <torusGeometry args={[1, 0.02, 8, 64]} />
        <meshBasicMaterial color="#00ff00" transparent opacity={0.6} />
      </mesh>
    </group>
  );
}

// --- Bloch Vector Arrow ---

function BlochVector({ data }: { data: SpinorData }) {
  const meshRef = useRef<THREE.Mesh>(null);
  const [bx, by, bz] = data.bloch_vector;

  // Map Bloch vector: x=rotation, y=precession, z=charge
  // In Three.js: x=x, y=z(charge up), z=y
  const tipPosition = new THREE.Vector3(bx, bz, by);

  // Color based on charge: green at equator (HIHO), blue at north, red at south
  const chargeColor = useMemo(() => {
    const c = data.charge_polarity;
    if (Math.abs(c) < 0.1) return "#00ff00"; // HIHO green
    return c > 0 ? `hsl(220, 80%, ${50 + c * 30}%)` : `hsl(0, 80%, ${50 + Math.abs(c) * 30}%)`;
  }, [data.charge_polarity]);

  useFrame((state) => {
    if (meshRef.current) {
      // Gentle pulse at the tip
      const scale = 0.08 + Math.sin(state.clock.getElapsedTime() * 3) * 0.02;
      meshRef.current.scale.setScalar(scale);
    }
  });

  const arrowPoints = useMemo(
    () => [new THREE.Vector3(0, 0, 0), tipPosition],
    [tipPosition]
  );

  return (
    <group>
      {/* Arrow line */}
      <Line
        points={arrowPoints}
        color={chargeColor}
        lineWidth={3}
      />
      {/* Tip sphere */}
      <mesh ref={meshRef} position={tipPosition}>
        <sphereGeometry args={[1, 16, 16]} />
        <meshBasicMaterial color={chargeColor} />
      </mesh>

      {/* State label */}
      <Html position={tipPosition.clone().multiplyScalar(1.3)} center>
        <div className="bg-black/80 px-2 py-1 rounded text-[10px] font-mono text-white whitespace-nowrap">
          r=[{bx.toFixed(2)}, {by.toFixed(2)}, {bz.toFixed(2)}]
        </div>
      </Html>
    </group>
  );
}

// --- HIHO Reference Point ---

function HIHOMarker() {
  const ref = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (ref.current) {
      const s = 0.04 + Math.sin(state.clock.getElapsedTime() * 2) * 0.01;
      ref.current.scale.setScalar(s);
    }
  });

  return (
    <mesh ref={ref} position={[1, 0, 0]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial color="#00ff00" transparent opacity={0.8} />
    </mesh>
  );
}

// --- Info Panel ---

function InfoPanel({ data, isHiho }: { data: SpinorData; isHiho: boolean }) {
  return (
    <div className="absolute top-4 right-4 bg-black/90 border border-gray-700 rounded-lg p-4 font-mono text-xs text-gray-300 w-64 space-y-2">
      <h3 className="text-green-400 font-bold text-sm mb-2">
        {isHiho ? "HIHO State (Brahmagupta's Zero)" : "Current Spinor State"}
      </h3>

      <div className="space-y-1">
        <div className="flex justify-between">
          <span className="text-blue-400">⟨σ_x⟩ Rotation:</span>
          <span>{data.spin_rotation.toFixed(4)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-pink-400">⟨σ_y⟩ Precession:</span>
          <span>{data.spin_precession.toFixed(4)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-yellow-400">⟨σ_z⟩ Charge:</span>
          <span className={Math.abs(data.charge_polarity) < 0.01 ? "text-green-400" : ""}>
            {data.charge_polarity.toFixed(4)}
          </span>
        </div>
      </div>

      <div className="border-t border-gray-700 pt-2 space-y-1">
        <div className="flex justify-between">
          <span>Coherence |r|:</span>
          <span className={data.coherence > 0.99 ? "text-green-400" : ""}>
            {data.coherence?.toFixed(4) ?? '0.0000'}
          </span>
        </div>
        <div className="flex justify-between">
          <span>HIHO Deviation:</span>
          <span className={data.hiho_deviation < 0.01 ? "text-green-400" : "text-yellow-400"}>
            {data.hiho_deviation?.toFixed(4) ?? '0.0000'}
          </span>
        </div>
      </div>

      {isHiho && (
        <div className="border-t border-gray-700 pt-2 text-[10px] text-gray-500 italic">
          &quot;At the still point of the turning world&quot; — T.S. Eliot
        </div>
      )}
    </div>
  );
}

// --- Controls Panel ---

function ControlsPanel({
  logic,
  quantum,
  theta,
  phi,
  onLogicChange,
  onQuantumChange,
  onThetaChange,
  onPhiChange,
}: {
  logic: number;
  quantum: number;
  theta: number;
  phi: number;
  onLogicChange: (v: number) => void;
  onQuantumChange: (v: number) => void;
  onThetaChange: (v: number) => void;
  onPhiChange: (v: number) => void;
}) {
  return (
    <div className="absolute bottom-4 left-4 bg-black/90 border border-gray-700 rounded-lg p-4 font-mono text-xs text-gray-300 w-64 space-y-3">
      <h3 className="text-green-400 font-bold text-sm">SPIN Controls</h3>

      <div>
        <label className="flex justify-between mb-1">
          <span>Logic (θ polar)</span>
          <span className="text-blue-400">{logic.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={logic}
          onChange={(e) => onLogicChange(parseFloat(e.target.value))}
          className="w-full accent-blue-500"
        />
      </div>

      <div>
        <label className="flex justify-between mb-1">
          <span>Quantum (φ azimuthal)</span>
          <span className="text-pink-400">{quantum.toFixed(2)}</span>
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={quantum}
          onChange={(e) => onQuantumChange(parseFloat(e.target.value))}
          className="w-full accent-pink-500"
        />
      </div>

      <div className="border-t border-gray-700 pt-2">
        <label className="flex justify-between mb-1">
          <span>Rotation (θ_rot)</span>
          <span className="text-cyan-400">{((theta / Math.PI) * 180).toFixed(0)}°</span>
        </label>
        <input
          type="range"
          min={-Math.PI}
          max={Math.PI}
          step="0.01"
          value={theta}
          onChange={(e) => onThetaChange(parseFloat(e.target.value))}
          className="w-full accent-cyan-500"
        />
      </div>

      <div>
        <label className="flex justify-between mb-1">
          <span>Precession (φ_prec)</span>
          <span className="text-amber-400">{((phi / Math.PI) * 180).toFixed(0)}°</span>
        </label>
        <input
          type="range"
          min={-Math.PI}
          max={Math.PI}
          step="0.01"
          value={phi}
          onChange={(e) => onPhiChange(parseFloat(e.target.value))}
          className="w-full accent-amber-500"
        />
      </div>
    </div>
  );
}

// --- Main Component ---

export default function BlochSphere() {
  const [logic, setLogic] = useState(0.5);
  const [quantum, setQuantum] = useState(0.0);
  const [theta, setTheta] = useState(0.0);
  const [phi, setPhi] = useState(0.0);
  const [spinorData, setSpinorData] = useState<SpinorData | null>(null);
  const [loading, setLoading] = useState(false);

  // Fetch spinor state from API when controls change
  const fetchSpinor = useCallback(async (l: number, q: number, t: number, p: number) => {
    try {
      const resp = await fetch(`${API_BASE}/api/genesis/spinor/rotate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ logic: l, quantum: q, theta: t, phi: p, gamma: 0 }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setSpinorData(data.bloch);
      }
    } catch {
      // Fallback: compute locally (simplified)
      const thetaB = (1 - l) * Math.PI;
      const phiB = q * 2 * Math.PI;
      const bx = Math.sin(thetaB) * Math.cos(phiB);
      const by = Math.sin(thetaB) * Math.sin(phiB);
      const bz = Math.cos(thetaB);
      setSpinorData({
        bloch_vector: [bx, by, bz],
        coherence: 1.0,
        charge_polarity: bz,
        spin_rotation: bx,
        spin_precession: by,
        hiho_deviation: Math.abs(bz),
      });
    }
  }, []);

  // Debounced fetch on control changes
  React.useEffect(() => {
    const timer = setTimeout(() => fetchSpinor(logic, quantum, theta, phi), 50);
    return () => clearTimeout(timer);
  }, [logic, quantum, theta, phi, fetchSpinor]);

  // Initial fetch
  React.useEffect(() => {
    fetchSpinor(0.5, 0.0, 0.0, 0.0);
  }, [fetchSpinor]);

  const isHiho = spinorData ? spinorData.hiho_deviation < 0.01 : false;

  return (
    <div className="relative w-full h-[600px] bg-[#0a0a1a] rounded-xl overflow-hidden border border-gray-800">
      {/* 3D Canvas */}
      <Canvas camera={{ position: [2.5, 1.5, 2.5], fov: 45 }}>
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={0.8} />

        <SphereWireframe />
        <HIHOMarker />
        {spinorData && <BlochVector data={spinorData} />}

        <OrbitControls enablePan={false} />

        <EffectComposer>
          <Bloom
            intensity={0.4}
            luminanceThreshold={0.3}
            luminanceSmoothing={0.9}
          />
        </EffectComposer>
      </Canvas>

      {/* UI Overlays */}
      <ControlsPanel
        logic={logic}
        quantum={quantum}
        theta={theta}
        phi={phi}
        onLogicChange={setLogic}
        onQuantumChange={setQuantum}
        onThetaChange={setTheta}
        onPhiChange={setPhi}
      />

      {spinorData && <InfoPanel data={spinorData} isHiho={isHiho} />}

      {/* Title */}
      <div className="absolute top-4 left-4 font-mono">
        <h2 className="text-lg text-green-400 font-bold">Bloch Sphere</h2>
        <p className="text-[10px] text-gray-500">SU(2) Spinor Visualization — SPIN = Rotation + Precession</p>
      </div>
    </div>
  );
}
