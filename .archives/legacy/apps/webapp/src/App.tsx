import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import './index.css';
import { LandingPage } from './components/LandingPage';
import { ManifoldCanvas } from './components/Universe/ManifoldCanvas';
import { ResearchPanel } from './components/ResearchPanel';
import { useOuroboros } from './hooks/useOuroboros';

function App() {
  const [view, setView] = useState<'landing' | 'explorer' | 'manifold'>('landing');
  const ouroboros = useOuroboros();

  return (
    <div className="app w-screen h-screen overflow-hidden bg-void-black text-nexus-green font-mono">
      <AnimatePresence mode="wait">
        {view === 'landing' ? (
          <LandingPage key="landing" onEnter={() => setView('explorer')} />
        ) : (
          <motion.div 
            key="interface" 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="w-full h-full flex flex-col"
          >
            {/* Navigation Toggle */}
            <div className="absolute top-4 right-4 z-50 flex gap-4">
                <button 
                    onClick={() => setView(view === 'explorer' ? 'manifold' : 'explorer')}
                    className="px-4 py-2 border border-nexus-green bg-black/40 text-[10px] hover:bg-nexus-green/20 transition-all uppercase tracking-widest"
                >
                    Switch to {view === 'explorer' ? 'Manifold' : 'Dashboard'}
                </button>
                <button 
                    onClick={() => setView('landing')}
                    className="px-4 py-2 border border-red-900 bg-black/40 text-[10px] hover:bg-red-900/20 text-red-400 transition-all uppercase tracking-widest"
                >
                    Logout
                </button>
            </div>

            {view === 'explorer' ? (
                <LandingPage key="active-swarm" onEnter={() => {}} />
            ) : (
                <>
                    <ManifoldCanvas />
                    <ResearchPanel />
                </>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
