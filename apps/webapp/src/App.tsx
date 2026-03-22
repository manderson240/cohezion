import React, { useState } from 'react';
import { AnimatePresence } from 'framer-motion';
import './index.css';
import { LandingPage } from './components/LandingPage';
import { useOuroboros } from './hooks/useOuroboros';

function App() {
  const [view, setView] = useState<'landing' | 'explorer'>('landing');
  const ouroboros = useOuroboros();

  return (
    <div className="app w-screen h-screen overflow-hidden bg-void-black text-nexus-green font-mono">
      <AnimatePresence mode="wait">
        {view === 'landing' ? (
          <LandingPage key="landing" onEnter={() => setView('explorer')} />
        ) : (
          <div key="explorer" className="w-full h-full flex flex-col items-center justify-center">
            {/* The explorer view is currently the LandingPage initialized state */}
            {/* Future: Add more dashboard components here or let LandingPage handle it */}
            <LandingPage key="active-swarm" onEnter={() => setView('landing')} />
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default App;
