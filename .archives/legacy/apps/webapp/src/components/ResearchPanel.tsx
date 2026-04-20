import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

export const ResearchPanel = () => {
    const [isOpen, setIsOpen] = useState(false);
    const [notebook, setNotebook] = useState('hiho_explorer');

    const notebooks = [
        { id: 'hiho_explorer', name: 'HIHO Explorer' },
        { id: 'flume_showcase', name: 'FLUME Showcase' },
        { id: 'universe_explorer', name: 'Universe Engine' }
    ];

    return (
        <div className="absolute right-0 top-0 h-full z-40 flex pointer-events-none">
            {/* Toggle Button */}
            <div className="flex flex-col justify-center p-2">
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="pointer-events-auto w-10 h-32 bg-black/60 border border-nexus-green text-nexus-green flex items-center justify-center hover:bg-nexus-green/20 transition-all rounded-l-lg"
                    style={{ writingMode: 'vertical-rl', textOrientation: 'mixed' }}
                >
                    {isOpen ? 'CLOSE RESEARCH' : 'OPEN RESEARCH'}
                </button>
            </div>

            {/* Side Panel */}
            <AnimatePresence>
                {isOpen && (
                    <motion.div
                        initial={{ x: '100%' }}
                        animate={{ x: 0 }}
                        exit={{ x: '100%' }}
                        transition={{ type: 'spring', damping: 20 }}
                        className="pointer-events-auto w-[600px] h-full bg-black/80 border-l border-nexus-green backdrop-blur-xl flex flex-col p-6 font-mono"
                    >
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-nexus-green text-lg tracking-tighter uppercase">Living Research Substrate</h2>
                            <select 
                                value={notebook}
                                onChange={(e) => setNotebook(e.target.value)}
                                className="bg-black/40 border border-nexus-green text-nexus-green text-[10px] p-1 uppercase"
                            >
                                {notebooks.map(n => <option key={n.id} value={n.id}>{n.name}</option>)}
                            </select>
                        </div>

                        {/* Marimo Iframe Placeholder */}
                        <div className="flex-1 bg-void-black border border-nexus-green/30 relative rounded overflow-hidden">
                            <div className="absolute inset-0 flex items-center justify-center text-nexus-green/20 text-xs text-center p-12">
                                [ MARIMO REACTIVE NOTEBOOK: {notebook.toUpperCase()} ]
                                <br />
                                Integration active. Live-coding stream synchronized.
                            </div>
                            <iframe 
                                title="research-notebook"
                                src={`http://localhost:8081/${notebook}`}
                                className="w-full h-full border-none opacity-80"
                            />
                        </div>

                        {/* Interactive Agent Chat */}
                        <div className="h-48 mt-6 flex flex-col">
                            <div className="text-[10px] text-nexus-green/60 uppercase mb-2">Agent Guidance Protocol</div>
                            <div className="flex-1 bg-black/40 border border-nexus-green/20 p-3 overflow-y-auto text-[11px] space-y-2">
                                <div className="text-nexus-green"><span className="opacity-50">[KNOW]</span>: The manifold is reaching stability. You may now interpolate.</div>
                                <div className="text-white"><span className="text-red-400">[DOER]</span>: Nudging 12D state by dt=0.1. Coherence maintained.</div>
                            </div>
                            <div className="mt-2 flex gap-2">
                                <input 
                                    type="text" 
                                    placeholder="GUIDE THE SWARM..."
                                    className="flex-1 bg-black/60 border border-nexus-green/40 p-2 text-white text-xs focus:outline-none focus:border-nexus-green"
                                />
                                <button className="px-4 bg-nexus-green/20 border border-nexus-green text-nexus-green text-[10px] uppercase hover:bg-nexus-green/40">
                                    Send
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
};
