import { useState, useEffect } from 'react';

export interface OuroborosState {
    coherence: number;
    stability: number;
    entropy: number;
    uptime: number;
    active_agents: number;
}

export function useOuroboros() {
    const [state, setState] = useState<OuroborosState>({
        coherence: 0,
        stability: 0,
        entropy: 0,
        uptime: 0,
        active_agents: 0
    });

    useEffect(() => {
        // Attempt real connection to Cohezion Pulse (Port 8080 for API)
        const ws = new WebSocket('ws://localhost:8080/pulse');

        ws.onopen = () => {
            console.log('Connected to Cohezion Pulse');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'pulse') {
                    // Mapping backend 12D vector to frontend state
                    const brane = data.payload.brane;
                    setState({
                        coherence: brane[7] || 0.85, // Precipitation -> Coherence
                        stability: brane[5] || 0.92, // Control -> Stability
                        entropy: brane[6] || 0.05,   // Entropy -> Entropy
                        uptime: Date.now(),
                        active_agents: 3 // TODO: dynamic agent count
                    });
                }
            } catch (e) {
                console.warn('Failed to parse pulse:', e);
            }
        };

        // Fallback Simulation (Dream State) if no connection
        const interval = setInterval(() => {
            if (ws.readyState !== WebSocket.OPEN) {
                setState(prev => ({
                    coherence: 0.8 + Math.random() * 0.1,
                    stability: 0.9 + Math.random() * 0.05,
                    entropy: 0.02 + Math.random() * 0.03,
                    uptime: prev.uptime + 1000,
                    active_agents: 3 + Math.floor(Math.random() * 2)
                }));
            }
        }, 1000);

        return () => {
            ws.close();
            clearInterval(interval);
        };
    }, []);

    return state;
}
