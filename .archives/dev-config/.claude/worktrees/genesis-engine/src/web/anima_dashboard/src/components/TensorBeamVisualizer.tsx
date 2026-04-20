"use client";

import React, { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import * as THREE from 'three';
import { EffectComposer, Bloom } from '@react-three/postprocessing';

const COUNT = 5000;

// High-performance particle state initialization moved outside to keep components pure
function createParticles() {
  const temp = [];
  for (let i = 0; i < COUNT; i++) {
      // 12D down-projection to stereographic 3D (Clifford Torus approximation)
      const u = Math.random() * Math.PI * 2;
      const v = Math.random() * Math.PI * 2;
      
      // EVO Morphospace Mapping
      const R = 3 + Math.sin(v * 3) * 0.5;
      const r = 1.0 + Math.cos(u * 5) * 0.2;
      
      const x = (R + r * Math.cos(v)) * Math.cos(u);
      const y = r * Math.sin(v) * 2;
      const z = (R + r * Math.cos(v)) * Math.sin(u);
      
      const phase = Math.random() * Math.PI * 2;
      const speed = 0.002 + Math.random() * 0.01;
      temp.push({ x, y, z, phase, speed, R, r, u, v });
  }
  return temp;
}

function ParticleSwarm() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  
  // Keep particles in ref to avoid mutable state issues
  const particlesRef = useRef(createParticles());

  useFrame((state) => {
    if (!meshRef.current) return;
    
    const time = state.clock.getElapsedTime();
    const particles = particlesRef.current;
    
    particles.forEach((p, i) => {
        // Complex MHD Rotation & Helicity
        p.phase += p.speed;
        
        // Breathe effect (charge cluster density variation)
        const breathe = Math.sin(time * 2 + p.phase) * 0.5 + 1;
        
        // Helical torsion
        const angle = p.phase;
        const currentX = p.x * Math.cos(angle) - p.z * Math.sin(angle);
        const currentZ = p.x * Math.sin(angle) + p.z * Math.cos(angle);
        const currentY = p.y * Math.sin(time + p.phase) * 0.2 + p.y;
        
        dummy.position.set(currentX * breathe, currentY, currentZ * breathe);
        
        // Orient particles along the manifold tangent
        dummy.rotation.x = time * p.speed * 10;
        dummy.rotation.y = time * p.speed * 10;
        
        const scale = 0.5 + Math.sin(time * 3 + p.phase) * 0.5;
        dummy.scale.set(scale, scale, scale);
        
        dummy.updateMatrix();
        meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, COUNT]}>
      <sphereGeometry args={[0.04, 4, 4]} />
      <meshBasicMaterial 
        color="#10b981"
      />
    </instancedMesh>
  );
}

const EVO_COUNT = 12;
function generateEvoParticles(count: number) {
  return Array.from({length: count}, () => ({
    angle: Math.random() * Math.PI * 2,
    radius: 4 + Math.random() * 2,
    speed: 0.02 + Math.random() * 0.05,
    yOffset: (Math.random() - 0.5) * 4
  }));
}
const INITIAL_EVO_PARTICLES = generateEvoParticles(EVO_COUNT);

function ExoticVacuumObjects() {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  
  const particlesRef = useRef(INITIAL_EVO_PARTICLES);
  
  useFrame((state) => {
    if (!meshRef.current) return;
    const time = state.clock.getElapsedTime();
    particlesRef.current.forEach((p, i) => {
      p.angle += p.speed;
      const x = Math.cos(p.angle) * p.radius;
      const z = Math.sin(p.angle) * p.radius;
      const currentY = p.yOffset + Math.sin(time * 5 + i) * 0.5;
      
      dummy.position.set(x, currentY, z);
      const scale = 1.0 + Math.sin(time * 10 + i) * 0.3;
      dummy.scale.set(scale, scale, scale);
      dummy.updateMatrix();
      meshRef.current!.setMatrixAt(i, dummy.matrix);
    });
    meshRef.current.instanceMatrix.needsUpdate = true;
  });

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, EVO_COUNT]}>
      <sphereGeometry args={[0.3, 16, 16]} />
      <meshBasicMaterial color="#fbbf24" />
    </instancedMesh>
  );
}

function WallOfRed() {
  const wallRef = useRef<THREE.Mesh>(null);
  
  useFrame((state) => {
      if (!wallRef.current) return;
      const time = state.clock.getElapsedTime();
      // Pulsating bounds indicating plasma containment
      const scale = 1.0 + Math.sin(time * 8) * 0.005;
      wallRef.current.scale.set(scale, scale, scale);
      
      // Simulate "reactions" to plasma hits
      if (wallRef.current.material && !Array.isArray(wallRef.current.material)) {
          (wallRef.current.material as THREE.MeshBasicMaterial).opacity = 0.08 + Math.sin(time * 12) * 0.02;
      }
  });

  return (
    <mesh ref={wallRef}>
      <cylinderGeometry args={[11, 11, 15, 64, 1, true]} />
      <meshBasicMaterial color="#b91c1c" transparent={true} opacity={0.08} wireframe={true} side={THREE.DoubleSide} />
    </mesh>
  );
}

const CLOUD_COUNT = 2000;
function generateKordylewskiParticles(count: number, baseAngle: number) {
    const pts = new Float32Array(count * 3);
    for(let i=0; i<count; i++) {
        const r = 8 + (Math.random() - 0.5) * 3;
        const theta = baseAngle + (Math.random() - 0.5) * 0.8;
        pts[i*3] = r * Math.cos(theta);
        pts[i*3+1] = (Math.random() - 0.5) * 3;
        pts[i*3+2] = r * Math.sin(theta);
    }
    return pts;
}

const INITIAL_L4_PARTICLES = generateKordylewskiParticles(CLOUD_COUNT, Math.PI / 3);
const INITIAL_L5_PARTICLES = generateKordylewskiParticles(CLOUD_COUNT, -Math.PI / 3);

function KordylewskiClouds() {
  const l4Ref = useRef<THREE.Points>(null);
  const l5Ref = useRef<THREE.Points>(null);

  useFrame((state) => {
      const time = state.clock.getElapsedTime();
      if (l4Ref.current && l5Ref.current) {
          l4Ref.current.rotation.y = time * 0.05;
          l5Ref.current.rotation.y = time * 0.05;
          
          const scale = 1.0 + Math.sin(time * 3) * 0.02;
          l4Ref.current.scale.set(scale, scale, scale);
          l5Ref.current.scale.set(scale, scale, scale);
      }
  });

  return (
      <group>
        <points ref={l4Ref}>
            <bufferGeometry>
                <bufferAttribute attach="attributes-position" count={CLOUD_COUNT} args={[INITIAL_L4_PARTICLES, 3]} itemSize={3} />
            </bufferGeometry>
            <pointsMaterial size={0.06} color="#60a5fa" transparent opacity={0.6} />
        </points>
        <points ref={l5Ref}>
            <bufferGeometry>
                <bufferAttribute attach="attributes-position" count={CLOUD_COUNT} args={[INITIAL_L5_PARTICLES, 3]} itemSize={3} />
            </bufferGeometry>
            <pointsMaterial size={0.06} color="#c084fc" transparent opacity={0.6} />
        </points>
      </group>
  );
}

export default function TensorBeamVisualizer({ coherence, caGridDensity, evoCount }: {
  coherence?: number;
  caGridDensity?: number;
  evoCount?: number;
}) {
  return (
    <div className="w-full h-[600px] rounded-xl overflow-hidden bg-gradient-to-b from-[#050505] to-[#0a150f] border border-emerald-900/50 relative shadow-[0_0_50px_rgba(16,185,129,0.15)] group">
        <div className="absolute top-6 left-6 z-10 p-4 bg-black/40 rounded-xl border border-emerald-500/20 backdrop-blur-md shadow-2xl transition-all duration-500 group-hover:border-emerald-500/50">
            <div className="text-emerald-400 font-mono text-sm font-extrabold tracking-[0.2em] mb-2 flex items-center">
                <span className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,1)] animate-pulse mr-3"></span>
                12D TENSOR BEAM MANIFOLD
            </div>
            <div className="text-emerald-500/70 font-mono text-[10px] tracking-wider mb-2">
                HIHO (Half-In-Half-Out) PROJECTION
            </div>
            <div className="flex gap-4 mt-3 pt-3 border-t border-emerald-900/30">
                <div className="flex flex-col">
                    <span className="text-[9px] text-gray-500 font-mono mb-1">COHERENCE</span>
                    <span className="text-xs text-white font-mono">{(coherence ?? 0.5).toFixed(4)}</span>
                </div>
                <div className="flex flex-col">
                    <span className="text-[9px] text-gray-500 font-mono mb-1">CA DENSITY</span>
                    <span className="text-xs text-blue-400 font-mono">{((caGridDensity ?? 0.5) * 100).toFixed(1)}%</span>
                </div>
                <div className="flex flex-col">
                    <span className="text-[9px] text-gray-500 font-mono mb-1">CHARGE CLUSTERS</span>
                    <span className="text-xs text-amber-400 font-mono">{evoCount ?? 0} ACTIVE</span>
                </div>
            </div>
        </div>
      <Canvas camera={{ position: [0, 8, 16], fov: 50 }} gl={{ antialias: false }}>
        <color attach="background" args={['#020504']} />
        
        <ambientLight intensity={0.1} />
        <Stars radius={150} depth={50} count={8000} factor={3} saturation={1} fade speed={0.5} />
        
        <WallOfRed />
        <ParticleSwarm />
        <ExoticVacuumObjects />
        <KordylewskiClouds />
        
        <EffectComposer multisampling={4}>
            <Bloom luminanceThreshold={0.2} luminanceSmoothing={0.9} height={300} intensity={2.5} />
        </EffectComposer>

        <OrbitControls 
            autoRotate 
            autoRotateSpeed={0.5} 
            enablePan={false}
            maxPolarAngle={Math.PI / 1.5}
            minPolarAngle={Math.PI / 4}
            maxDistance={30}
            minDistance={5}
        />
      </Canvas>
      
      {/* HUD Overlays */}
      <div className="absolute bottom-6 right-6 z-10 text-right pointer-events-none">
          <div className="font-mono text-[10px] text-emerald-500/50 mb-1">FLUME ENCODER V4</div>
          <div className="font-mono text-[10px] text-emerald-500/50 mb-1">LATENT RESOLUTION: 256D</div>
          <div className="font-mono text-[10px] text-emerald-500/50">ORCH-OR BIOELECTRIC ENGINE</div>
      </div>
    </div>
  );
}
