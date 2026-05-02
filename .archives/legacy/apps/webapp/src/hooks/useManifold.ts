import { useState, useEffect } from 'react';

export interface ManifoldPoint {
    trajectory_id: string;
    coherence: number;
    doer: number[];
    thinker: number[];
    knower: number[];
}

export function useManifold() {
    const [points, setPoints] = useState<ManifoldPoint[]>([]);
    const [latestPoint, setLatestPoint] = useState<ManifoldPoint | null>(null);

    useEffect(() => {
        const ws = new WebSocket('ws://localhost:8080/telemetry');

        ws.onopen = () => {
            console.log('Connected to Cohezion Telemetry');
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                const newPoint: ManifoldPoint = {
                    trajectory_id: data.trajectory_id,
                    coherence: data.coherence,
                    doer: data.state.doer,
                    thinker: data.state.thinker,
                    knower: data.state.knower
                };
                
                setLatestPoint(newPoint);
                setPoints(prev => {
                    const updated = [...prev, newPoint];
                    return updated.slice(-50); // Keep last 50 points
                });
            } catch (e) {
                console.warn('Failed to parse telemetry message:', e);
            }
        };

        // Fallback Generator (Dream State)
        const interval = setInterval(() => {
            if (ws.readyState !== WebSocket.OPEN) {
                const dummyPoint: ManifoldPoint = {
                    trajectory_id: `dream_${Math.floor(Math.random() * 1000)}`,
                    coherence: 0.4 + Math.random() * 0.2,
                    doer: Array.from({ length: 12 }, () => Math.random() * 2 - 1),
                    thinker: Array.from({ length: 10 }, () => Math.random() * 2 - 1),
                    knower: Array.from({ length: 10 }, () => Math.random() * 2 - 1)
                };
                setLatestPoint(dummyPoint);
                setPoints(prev => [...prev, dummyPoint].slice(-50));
            }
        }, 2000);

        return () => {
            ws.close();
            clearInterval(interval);
        };
    }, []);

    return { points, latestPoint };
}
