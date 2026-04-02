import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { HologramField } from './Universe/HologramField';
import { CommandCenter } from './CommandCenter';
import { useOuroboros } from '../hooks/useOuroboros';

interface LandingPageProps {
    onEnter: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onEnter }) => {
    const ouroboros = useOuroboros();
    const [logs, setLogs] = useState<Array<{ id: string; text: string; type: 'info' | 'warning' | 'error' }>>([
        { id: '1', text: 'Manifold sync initialized', type: 'info' },
        { id: '2', text: 'HIHO coherence baseline: 0.500', type: 'info' },
    ]);

    useEffect(() => {
        const interval = setInterval(() => {
            const messages = [
                { text: `Coherence pulse: ${(ouroboros.coherence ?? 0).toFixed(3)}`, type: 'info' as const },
                { text: `Active agents: ${ouroboros.active_agents}`, type: 'info' as const },
                { text: `Entropy drift: ${(ouroboros.entropy ?? 0).toFixed(4)}`, type: 'warning' as const },
            ];
            const msg = messages[Math.floor(Math.random() * messages.length)];
            setLogs(prev => [...prev.slice(-20), { id: Date.now().toString(), ...msg }]);
        }, 3000);
        return () => clearInterval(interval);
    }, [ouroboros]);

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="relative w-full h-full"
        >
            <div className="canvas-container">
                <HologramField />
            </div>

            <CommandCenter
                coherence={(ouroboros.coherence ?? 0).toFixed(3)}
                isOnline={ouroboros.stability > 0.5}
                logs={logs}
            >
                <div className="flex items-center justify-center w-full h-full">
                    <button
                        onClick={onEnter}
                        className="pointer-events-auto px-8 py-3 border border-nexus-green text-nexus-green font-mono text-sm uppercase tracking-widest hover:bg-nexus-green/20 transition-all"
                    >
                        Enter the Manifold
                    </button>
                </div>
            </CommandCenter>
        </motion.div>
    );
};
