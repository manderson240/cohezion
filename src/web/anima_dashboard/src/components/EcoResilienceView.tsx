"use client";

import React, { useMemo, useRef, useState, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, Float, Text } from '@react-three/drei';
import * as THREE from 'three';
import { EffectComposer, Bloom } from '@react-three/postprocessing';

interface TrajectoryPoint {
  x: number;
  y: number;
  z: number;
  coherence: number;
  timestamp: string;
}

function ManifoldTrajectory({ points }: { points: TrajectoryPoint[] }) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);

  useEffect(() => {
    if (!meshRef.current) return;
    
    points.forEach((p, i) => {
      dummy.position.set(p.x, p.y, p.z);
      dummy.scale.setScalar(0.1);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  }, [points, dummy]);

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, 100]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial color="#3b82f6" transparent opacity={0.4} />
    </instancedMesh>
  );
}

function StabilityIndicator({ coherence }: { coherence: number }) {
  const meshRef = useRef<THREE.Mesh>(null);
  
  // HIHO Stability attractor is 0.5
  const stability = 1.0 - Math.abs(coherence - 0.5) * 2;
  const color = new THREE.Color().setHSL(0.3 * stability, 0.8, 0.5);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.rotation.y += 0.01;
      meshRef.current.position.y = Math.sin(state.clock.getElapsedTime()) * 0.2;
    }
  });

  return (
    <Float speed={2} rotationIntensity={1} floatIntensity={1}>
      <mesh ref={meshRef}>
        <octahedronGeometry args={[1, 0]} />
        <meshStandardMaterial 
          color={color} 
          emissive={color}
          emissiveIntensity={2}
          wireframe 
        />
      </mesh>
    </Float>
  );
}

interface MissionMetadata {
  report: string;
  assets: {
    image_prompt: string;
    diagram: string;
    sonification: any;
  };
  coherence: number;
}

export default function EcoResilienceView() {
  const [points, setPoints] = useState<TrajectoryPoint[]>([]);
  const [currentCoherence, setCurrentCoherence] = useState(0.5);
  const [metadata, setMetadata] = useState<MissionMetadata | null>(null);

  // Fetch mission metadata
  useEffect(() => {
    fetch('/generated/mission_metadata.json')
      .then(res => res.json())
      .then(data => {
        setMetadata(data);
        setCurrentCoherence(data.coherence);
      })
      .catch(err => console.error("Failed to load mission metadata", err));
  }, []);

  // Simulate SSE stream for the hackathon
  useEffect(() => {
    const interval = setInterval(() => {
      const newPoint = {
        x: (Math.random() - 0.5) * 10,
        y: (Math.random() - 0.5) * 10,
        z: (Math.random() - 0.5) * 10,
        coherence: 0.4 + Math.random() * 0.2,
        timestamp: new Date().toISOString()
      };
      setPoints(prev => [...prev.slice(-50), newPoint]);
      if (!metadata) setCurrentCoherence(newPoint.coherence);
    }, 1000);
    return () => clearInterval(interval);
  }, [metadata]);

  return (
    <div className="w-full h-full min-h-[600px] bg-slate-950 rounded-lg overflow-hidden relative border border-blue-500/30 flex flex-col md:flex-row">
      {/* 3D Manifold Canvas */}
      <div className="flex-1 relative">
        <div className="absolute top-4 left-4 z-10 bg-black/60 p-3 rounded border border-blue-400/20 backdrop-blur-md">
          <h3 className="text-blue-400 font-bold text-sm uppercase tracking-wider">EcoResilience 12D Manifold</h3>
          <div className="mt-2 space-y-1">
            <div className="flex justify-between gap-4 text-xs">
              <span className="text-slate-400">HIHO Coherence:</span>
              <span className={currentCoherence > 0.45 && currentCoherence < 0.55 ? "text-green-400" : "text-yellow-400"}>
                {currentCoherence.toFixed(4)}
              </span>
            </div>
            <div className="flex justify-between gap-4 text-xs">
              <span className="text-slate-400">Stability:</span>
              <span className="text-blue-400">{( (1.0 - Math.abs(currentCoherence - 0.5) * 2) * 100).toFixed(1)}%</span>
            </div>
          </div>
        </div>

        <Canvas camera={{ position: [0, 0, 15], fov: 50 }}>
          <color attach="background" args={['#020617']} />
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} intensity={1} />
          
          <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
          
          <ManifoldTrajectory points={points} />
          <StabilityIndicator coherence={currentCoherence} />
          
          <OrbitControls enablePan={false} />
          
          <EffectComposer>
            <Bloom luminanceThreshold={1} mipmapBlur intensity={1.5} />
          </EffectComposer>
        </Canvas>
      </div>

      {/* Multimodal Sidebar */}
      <div className="w-full md:w-80 bg-black/40 border-l border-blue-500/20 p-4 overflow-y-auto font-mono custom-scrollbar">
        {metadata ? (
          <div className="space-y-6">
            <section>
              <h4 className="text-blue-400 text-xs font-bold mb-2 uppercase border-b border-blue-500/30 pb-1">Resilience Map</h4>
              <div className="aspect-square bg-slate-900 rounded border border-blue-500/20 overflow-hidden">
                <img src="/generated/resilience_map.png" alt="Resilience Map" className="w-full h-full object-cover" />
              </div>
              <p className="text-[10px] text-slate-500 mt-2 italic leading-tight">{metadata.assets.image_prompt}</p>
            </section>

            <section>
              <h4 className="text-green-400 text-xs font-bold mb-2 uppercase border-b border-green-500/30 pb-1">Systemic Feedback</h4>
              <div className="bg-slate-900/50 p-2 rounded text-[9px] text-green-300 whitespace-pre overflow-x-auto">
                {metadata.assets.diagram}
              </div>
            </section>

            <section>
              <h4 className="text-yellow-400 text-xs font-bold mb-2 uppercase border-b border-yellow-500/30 pb-1">Resonance Audio</h4>
              <div className="flex items-center gap-2">
                <div className="w-full bg-slate-800 h-1 rounded overflow-hidden">
                  <div className="bg-yellow-400 h-full animate-pulse" style={{ width: '60%' }}></div>
                </div>
                <span className="text-[9px] text-yellow-500">{metadata.assets.sonification.base_freq}Hz</span>
              </div>
            </section>

            <section>
              <h4 className="text-slate-400 text-xs font-bold mb-2 uppercase border-b border-slate-500/30 pb-1">Synthesis Report</h4>
              <div className="text-[10px] text-slate-300 leading-relaxed max-h-40 overflow-y-auto">
                {metadata.report}
              </div>
            </section>
          </div>
        ) : (
          <div className="h-full flex items-center justify-center text-slate-600 text-xs italic">
            Waiting for Resonance Mission telemetry...
          </div>
        )}
      </div>
      
      <div className="absolute bottom-4 left-4 text-[10px] text-blue-500/50 font-mono">
        Gemma 4 Resonance Engine // Cohezion v1.0.2
      </div>
    </div>
  );
}
