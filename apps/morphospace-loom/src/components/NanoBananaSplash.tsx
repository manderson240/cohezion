import React, { useEffect, useState } from 'react';

export const NanoBananaSplash = ({ onStart }: { onStart: () => void }) => {
    const [phase, setPhase] = useState<'condensing' | 'expanding' | 'ready'>('condensing');

    useEffect(() => {
        setTimeout(() => setPhase('expanding'), 1000);
        setTimeout(() => setPhase('ready'), 3500);
    }, []);

    return (
        <div style={{
            position: 'absolute', top: 0, left: 0, width: '100vw', height: '100vh',
            background: 'radial-gradient(circle at center, #1a0b2e 0%, #000000 100%)',
            display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center',
            zIndex: 1000, overflow: 'hidden'
        }}>
            {/* The Quantum Banana / Singularity */}
            <div className={`quantum-core ${phase}`} style={{
                width: '300px', height: '300px',
                position: 'relative',
                display: 'flex', justifyContent: 'center', alignItems: 'center'
            }}>
                <div className="orbital-ring ring-1"></div>
                <div className="orbital-ring ring-2"></div>
                <div className="orbital-ring ring-3"></div>
                <div className="core-nucleus">
                    <div className="quantum-banana-arc"></div>
                </div>
            </div>

            <h1 className="title-glitch" style={{
                fontSize: '4rem', fontFamily: 'Orbitron, monospace',
                marginTop: '3rem', opacity: phase === 'ready' ? 1 : 0,
                transition: 'opacity 1s ease',
                textShadow: '0 0 20px #FF00FF'
            }}>
                COHEZION
            </h1>

            <div style={{
                marginTop: '2rem', opacity: phase === 'ready' ? 1 : 0,
                transition: 'opacity 1s ease 0.5s',
                display: 'flex', gap: '1rem'
            }}>
                <button onClick={onStart} className="cyber-button">
                    INITIATE SEQUENCE
                </button>
            </div>

            <div style={{ position: 'absolute', bottom: 30, fontSize: 10, color: '#444' }}>
                GENIE 3.0 / NANO-BANANA PROTOCOL / v0.9.1
            </div>
        </div>
    );
};
