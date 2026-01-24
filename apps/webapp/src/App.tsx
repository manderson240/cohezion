import React, { Suspense, useState, useEffect } from 'react';
import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars, Float, PerspectiveCamera } from '@react-three/drei';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Cpu, ChevronRight, Activity } from 'lucide-react';
import './index.css';
import logo from './logo.png';

// --- Types ---
interface MissionState {
  stability: number;
  lattice_density: string;
  eco_metrics: { habitat_quality: number };
}

// --- 3D Components ---

const ManifoldNode = ({ position, stability }: { position: [number, number, number], stability: number }) => {
  const color = stability > 0.5 ? '#00FF00' : '#FF3B3B'; // Nexus Green or Critical Red
  const intensity = Math.abs(stability - 0.5) * 5;
  return (
    <mesh position={position}>
      <sphereGeometry args={[0.05, 16, 16]} />
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={intensity} />
    </mesh>
  );
};

const ManifoldExplorer = ({ state }: { state: MissionState }) => (
  <div className="canvas-container">
    <Canvas>
      <PerspectiveCamera makeDefault position={[0, 0, 5]} />
      <color attach="background" args={['#0A0A0A']} />
      <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1.5} color="#00FF00" />
      <Suspense fallback={null}>
        <Float speed={2} rotationIntensity={0.5} floatIntensity={0.5}>
          <group>
            {[...Array(20)].map((_, i) => (
              <ManifoldNode key={i} position={[Math.sin(i) * 2, Math.cos(i) * 2, Math.sin(i * 0.5) * 1]} stability={state.stability} />
            ))}
            <mesh>
              <torusKnotGeometry args={[1, 0.3, 128, 32]} />
              <meshStandardMaterial color="#0077BE" wireframe emissive="#0077BE" emissiveIntensity={0.3} transparent opacity={0.4} />
            </mesh>
          </group>
        </Float>
      </Suspense>
      <OrbitControls enablePan={false} autoRotate autoRotateSpeed={0.5} />
    </Canvas>
  </div>
);

// --- UI Components ---

const LandingPage = ({ onEnter }: { onEnter: () => void }) => (
  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="landing-overlay">
    <div className="hero-card glass text-center">
      <img src={logo} alt="Cohezion Nexus" className="mx-auto mb-6 w-32 h-32" />
      <h1 className="text-5xl font-bold mb-2 tracking-tighter">COHEZION</h1>
      <p className="text-gray-400 mb-6 px-4">Universal Lattice Orchestration & Recursive Simulation Synthesis.</p>

      <div className="grid grid-cols-2 gap-4 text-left mb-8 px-8">
        <div className="flex items-center gap-2"><Cpu size={16} className="text-primary" /> <span>12D Vectors</span></div>
        <div className="flex items-center gap-2"><Activity size={16} className="text-secondary" /> <span>FLUME Protocol</span></div>
      </div>

      <button onClick={onEnter} className="btn-primary flex items-center gap-2 mx-auto">
        Join the Swarm <ChevronRight size={18} />
      </button>

      <p className="mt-8 text-xs text-gray-500">Currently executing mission: The Great Convergence</p>
    </div>
  </motion.div>
);

const HUD = ({ state }: { state: MissionState }) => (
  <div className="hud-container">
    <motion.div initial={{ x: -100, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="hud-panel glass">
      <h1 className="text-xl">Mission Control</h1>
      <div className="metric"><span>Stability</span><span className="value">{state.stability.toFixed(4)}</span></div>
      <div className="metric"><span>Density</span><span className="value">{state.lattice_density}</span></div>
      <div className="metric"><span>Habitat</span><span className="value">{state.eco_metrics.habitat_quality.toFixed(3)}</span></div>
    </motion.div>
    <div />
    <motion.div initial={{ x: 100, opacity: 0 }} animate={{ x: 0, opacity: 1 }} className="hud-panel glass">
      <h2>Log</h2>
      <div className="text-xs font-mono opacity-70">
        <p>&gt; HIHO Parity reached</p>
        <p>&gt; Manifold crystallized</p>
      </div>
    </motion.div>
  </div>
);

function App() {
  const [view, setView] = useState<'landing' | 'explorer'>('landing');
  const [state, setState] = useState<MissionState>({
    stability: 0.8542,
    lattice_density: "1.2M",
    eco_metrics: { habitat_quality: 0.723 }
  });

  useEffect(() => {
    const timer = setInterval(() => {
      setState(prev => ({ ...prev, stability: prev.stability + (Math.random() - 0.5) * 0.001 }));
    }, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="app">
      <AnimatePresence>
        {view === 'landing' ? (
          <LandingPage key="landing" onEnter={() => setView('explorer')} />
        ) : (
          <div key="explorer">
            <ManifoldExplorer state={state} />
            <HUD state={state} />
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
