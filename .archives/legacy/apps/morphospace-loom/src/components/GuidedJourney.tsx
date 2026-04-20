import React, { useState } from 'react';

const TOUR_STEPS = [
    {
        id: 'intro',
        title: 'WELCOME TO COHEZION',
        content: 'You have entered the 12-Dimensional Manifold. This dashboard visualizes the cognitive state of the AI Swarm. Let me guide you through the instruments.',
        position: { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
    },
    {
        id: 'state-vector',
        title: '12D STATE VECTOR',
        content: 'To your LEFT is the State Card. It tracks the 12 dimensions of reality: 3 Spatial, 1 Temporal, and 8 Brane (Hidden) dimensions. Color shifts indicate "Sentiment" - Blue is stable, Red is entropic.',
        position: { top: '30%', left: '350px' }
    },
    {
        id: 'bbq-status',
        title: 'AUTONOMOUS MISSION',
        content: 'To your RIGHT is the Mission Status. This tracks the "Low and Slow" autonomous driver executing in the background. If it pulses Green, the swarm is actively cooking data.',
        position: { top: '150px', right: '350px' }
    },
    {
        id: 'complete',
        title: 'YOU ARE READY',
        content: 'The system is now under your observation. Watch for "Novelty Decay" in the central visualization. Good luck, Operator.',
        position: { top: '50%', left: '50%', transform: 'translate(-50%, -50%)' }
    }
];

export const GuidedJourney = ({ onComplete, onSpeak }: { onComplete: () => void, onSpeak: (text: string) => void }) => {
    const [stepIndex, setStepIndex] = useState(0);
    const step = TOUR_STEPS[stepIndex];

    // Trigger audio on step change
    React.useEffect(() => {
        onSpeak(`${step.title}. ${step.content}`);
    }, [stepIndex, onSpeak]);

    const next = () => {
        if (stepIndex < TOUR_STEPS.length - 1) {
            setStepIndex(stepIndex + 1);
        } else {
            onComplete();
        }
    };

    return (
        <div style={{
            position: 'absolute', top: 0, left: 0, width: '100vw', height: '100vh',
            zIndex: 900, pointerEvents: 'none' // Allow click-through for highlight? No, we block interaction during tour.
        }}>
            {/* Darken Background */}
            <div style={{
                position: 'absolute', width: '100%', height: '100%',
                background: 'rgba(0,0,0,0.6)', pointerEvents: 'auto'
            }} />

            {/* Tour Card */}
            <div style={{
                position: 'absolute',
                ...step.position,
                width: '400px',
                background: 'rgba(10, 10, 30, 0.95)',
                border: '1px solid #00FFFF',
                boxShadow: '0 0 30px rgba(0, 255, 255, 0.3)',
                padding: '2rem',
                color: '#fff',
                pointerEvents: 'auto',
                transition: 'all 0.5s ease'
            }}>
                <h2 style={{
                    fontFamily: 'Orbitron', color: '#00FFFF', marginTop: 0,
                    fontSize: '1.5rem', letterSpacing: '0.1rem'
                }}>
                    {step.title}
                </h2>
                <div style={{ height: '2px', background: 'linear-gradient(90deg, #00FFFF, transparent)', marginBottom: '1rem' }} />

                <p style={{ lineHeight: '1.6', fontSize: '1rem', color: '#ddd' }}>
                    {step.content}
                </p>

                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.5rem', gap: '1rem' }}>
                    <div style={{ fontSize: '0.8rem', color: '#666', alignSelf: 'center', marginRight: 'auto' }}>
                        STEP {stepIndex + 1} / {TOUR_STEPS.length}
                    </div>
                    <button onClick={next} className="cyber-button" style={{ padding: '0.5rem 1.5rem', fontSize: '0.9rem' }}>
                        {stepIndex === TOUR_STEPS.length - 1 ? 'ENGAGE' : 'NEXT >>'}
                    </button>
                </div>
            </div>
        </div>
    );
};
