import React, { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import { ChevronRight, Cpu, Activity, Zap } from 'lucide-react';
import { motion } from 'framer-motion';
import './index.css';
import logo from './logo.png';
import { CommandCenter } from './components/CommandCenter';
import { useOuroboros } from './hooks/useOuroboros';
import { HologramField } from './components/Universe/HologramField';

// --- UI Components ---

const LandingPage = ({ onEnter }: { onEnter: () => void }) => (
  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="landing-overlay">
    <div className="hero-card glass text-center">
      <img src={logo} alt="Cohezion Nexus" className="mx-auto mb-6 w-32 h-32" />
      <h1 className="text-5xl font-bold mb-2 tracking-tighter">COHEZION</h1>
      <p className="text-gray-400 mb-6 px-4">Universal Lattice Orchestration & Recursive Simulation Synthesis.</p>

      <div className="grid grid-cols-2 gap-4 text-left mb-8 px-8">
        <div className="flex items-center gap-2"><Cpu size={16} className="text-primary" /> <span>12D Vectors</span></div>
        <div className="flex items-center gap-2"><Zap size={16} className="text-secondary" /> <span>The Pulse</span></div>
      </div>

      <button onClick={onEnter} className="btn-primary flex items-center gap-2 mx-auto">
        Join the Swarm <ChevronRight size={18} />
      </button>

      <p className="mt-8 text-xs text-gray-500">Currently executing mission: The Great Convergence</p>
    </div>
  </motion.div>
);

function App() {
  const [view, setView] = useState<'landing' | 'explorer'>('landing');
  const ouroboros = useOuroboros();
  const isOnline = ouroboros.coherence !== 0; // Simple check, could be more robust

  return (
    <div className="app">
      <AnimatePresence>
        {view === 'landing' ? (
          <LandingPage key="landing" onEnter={() => setView('explorer')} />
        ) : (
          <div key="explorer" className="w-full h-full">
            <CommandCenter
              coherence={ouroboros.coherence.toFixed(4)}
              isOnline={isOnline}
              logs={[
                { id: 'LOG-001', text: `Stability: ${ouroboros.stability.toFixed(4)}`, type: 'info' },
                { id: 'LOG-002', text: `Entropy: ${ouroboros.entropy.toFixed(4)}`, type: 'info' }
              ]}
            >
              <HologramField />
            </CommandCenter>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
