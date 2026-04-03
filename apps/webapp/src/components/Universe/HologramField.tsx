import React, { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, PerspectiveCamera } from '@react-three/drei';
import { EffectComposer, Bloom, Noise, Vignette, ChromaticAberration } from '@react-three/postprocessing';
import * as THREE from 'three';
import { HIHOShader } from './HIHOShader';

// Phase 88: WASM Physics Worker Integration
// This enables Edge-Precipitation (12D physics in browser)
const useAxiomaticWorker = () => {
    const workerRef = useRef<Worker | null>(null);
    const [workerState, setWorkerState] = React.useState<any>({});

    React.useEffect(() => {
        const worker = new Worker(new URL('../../workers/physicsWorker.ts', import.meta.url), { type: 'module' });
        workerRef.current = worker;
        worker.postMessage({ type: 'INIT' });

        worker.onmessage = (e) => {
            if (e.data.type === 'PULSE') {
                setWorkerState(e.data.results);
            }
        };

        return () => worker.terminate();
    }, []);

    return { workerRef, workerState };
};

// Phase 88: Performance Profiles for Strix Halo (128GB LPDDR5X)
const LOD_TIERS = {
    ULTRA: { max_nodes: 10000, bloom_intensity: 2.0, post_processing: true },
    HALO: { max_nodes: 30000, bloom_intensity: 1.0, post_processing: true },
    STARDUST: { max_nodes: 100000, bloom_intensity: 0.5, post_processing: false }
};

const NodePoints = ({ nodes, workerData }: { nodes: any[], workerData: any }) => {
    const shaderRef = useRef<THREE.ShaderMaterial>(null);

    const [positions, awarenessArr, stabilityArr, noveltyArr, precipitationArr] = useMemo(() => {
        const count = nodes.length;
        const pos = new Float32Array(count * 3);
        const awa = new Float32Array(count);
        const sta = new Float32Array(count);
        const nov = new Float32Array(count);
        const pre = new Float32Array(count);

        nodes.forEach((node, i) => {
            // Use WASM-interpolated data if available, otherwise fallback to API
            const workerNode = workerData[node.id];
            const ax = workerNode ? workerNode.axiomatic : (node.axiomatic || []);
            const vis = workerNode ? workerNode.visibility : 0.8;

            pos[i * 3] = ax[0] || node.position[0];
            pos[i * 3 + 1] = ax[1] || node.position[1];
            pos[i * 3 + 2] = ax[2] || node.position[2];

            // 12D Manifold Mapping (D9, D11, D12)
            const d9 = ax[8] ?? 0.5;
            const d11 = ax[10] ?? 0.5;
            const d12 = ax[11] ?? 0.8;

            awa[i] = d9;
            sta[i] = vis; // Peaked at 0.5
            nov[i] = d11;
            pre[i] = d12;
        });

        return [pos, awa, sta, nov, pre];
    }, [nodes, workerData]);

    useFrame((state) => {
        if (shaderRef.current) {
            shaderRef.current.uniforms.uTime.value = state.clock.getElapsedTime();
        }
    });

    if (nodes.length === 0) return null;

    return (
        <points>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    args={[positions, 3]}
                    count={nodes.length}
                    array={positions}
                    itemSize={3}
                />
                <bufferAttribute
                    attach="attributes-awareness"
                    args={[awarenessArr, 1]}
                    count={nodes.length}
                    array={awarenessArr}
                    itemSize={1}
                />
                <bufferAttribute
                    attach="attributes-stability"
                    args={[stabilityArr, 1]}
                    count={nodes.length}
                    array={stabilityArr}
                    itemSize={1}
                />
                <bufferAttribute
                    attach="attributes-novelty"
                    args={[noveltyArr, 1]}
                    count={nodes.length}
                    array={noveltyArr}
                    itemSize={1}
                />
                <bufferAttribute
                    attach="attributes-precipitation"
                    args={[precipitationArr, 1]}
                    count={nodes.length}
                    array={precipitationArr}
                    itemSize={1}
                />
            </bufferGeometry>
            <shaderMaterial
                ref={shaderRef}
                transparent
                depthWrite={false}
                blending={THREE.AdditiveBlending}
                vertexShader={HIHOShader.vertexShader}
                fragmentShader={HIHOShader.fragmentShader}
                uniforms={HIHOShader.uniforms}
            />
        </points>
    );
};

import { useHomeostasisHarmonics } from '../../hooks/useHomeostasisHarmonics';

export const HologramField = () => {
    const [nodes, setNodes] = React.useState<any[]>([]);
    const [lodTier, setLodTier] = React.useState(LOD_TIERS.ULTRA);
    const [audioActive, setAudioActive] = React.useState(false);
    const [narrative, setNarrative] = React.useState<string>("Initializing manifold...");
    const { workerRef, workerState } = useAxiomaticWorker();

    // Global coherence average for sonification
    const avgCoherence = useMemo(() => {
        if (nodes.length === 0) return 0.5;
        const sum = nodes.reduce((acc, node) => acc + (node.coherence || 0.5), 0);
        return sum / nodes.length;
    }, [nodes]);

    useHomeostasisHarmonics(avgCoherence, audioActive);

    // Listen for narrative precipitation (mocked for demo, would come from stream)
    React.useEffect(() => {
        const interval = setInterval(() => {
            if (nodes.length > 0) {
                const randomNode = nodes[Math.floor(Math.random() * nodes.length)];
                setNarrative(`PRECIPITATING: ${randomNode.agent_name || 'Agent'} is navigating ${randomNode.intent || 'the manifold'}. Coherence: ${(randomNode.coherence ?? 0).toFixed(3)}`);
            }
        }, 5000);
        return () => clearInterval(interval);
    }, [nodes]);

    React.useEffect(() => {
        const fetchUniverse = async () => {
            try {
                // Fetch live 12D data from the Manifold API
                const limit = lodTier === LOD_TIERS.STARDUST ? 50000 : 5000;
                const res = await fetch(`/universe/nodes?limit=${limit}`);
                if (res.ok) {
                    const data = await res.json();
                    const newNodes = data.nodes || [];
                    setNodes(newNodes);

                    // Sync Latent Souls to Worker
                    newNodes.forEach((n: any) => {
                        if (n.latent_vector && workerRef.current) {
                            workerRef.current.postMessage({
                                type: 'HYDRATE',
                                data: { id: n.id, latent: new Float32Array(n.latent_vector) }
                            });
                        }
                    });

                    // Dynamic LOD
                    if (newNodes.length > LOD_TIERS.HALO.max_nodes) {
                        setLodTier(LOD_TIERS.STARDUST);
                    } else if (newNodes.length > LOD_TIERS.ULTRA.max_nodes) {
                        setLodTier(LOD_TIERS.HALO);
                    } else {
                        setLodTier(LOD_TIERS.ULTRA);
                    }
                }
            } catch (e) {
                console.error("Manifold Sync Terminated", e);
            }
        };
        fetchUniverse();
        const interval = setInterval(fetchUniverse, 1000);

        // Worker Tick Loop (60Hz)
        const tickInterval = setInterval(() => {
            if (workerRef.current) {
                workerRef.current.postMessage({ type: 'TICK', data: { dt: 0.016 } });
            }
        }, 16);

        return () => {
            clearInterval(interval);
            clearInterval(tickInterval);
        };
    }, [lodTier, workerRef]);

    return (
        <div className="w-full h-full bg-black relative overflow-hidden">
            <Canvas dpr={lodTier === LOD_TIERS.STARDUST ? [0.75, 1] : [1, 2]} linear shadows={false}>
                <PerspectiveCamera makeDefault position={[0, 0, 15]} fov={60} />
                <color attach="background" args={['#000']} />

                <Stars radius={150} depth={60} count={10000} factor={6} saturation={0} fade speed={1} />

                <NodePoints nodes={nodes} workerData={workerState} />

                {lodTier.post_processing && (
                    <EffectComposer>
                        <Bloom
                            luminanceThreshold={0.1}
                            intensity={lodTier.bloom_intensity}
                            radius={0.4}
                        />
                        <ChromaticAberration offset={new THREE.Vector2(0.001, 0.001)} />
                        <Noise opacity={0.02} />
                        <Vignette offset={0.2} darkness={1.2} />
                    </EffectComposer>
                )}

                <OrbitControls
                    enableDamping
                    dampingFactor={0.05}
                    rotateSpeed={0.5}
                    autoRotate
                    autoRotateSpeed={0.03}
                />
            </Canvas>

            <div className="absolute inset-0 pointer-events-none z-10 flex flex-col p-8 font-mono">
                {/* Top Narrative Overlay */}
                <div className="w-full max-w-2xl bg-black/40 border-l-2 border-nexus-green p-4 backdrop-blur-md">
                    <div className="text-nexus-green text-[10px] uppercase tracking-widest mb-1 opacity-60">Sovereign Narrative</div>
                    <div className="text-white text-xs leading-relaxed animate-pulse">
                        {narrative}
                    </div>
                </div>

                <div className="flex-1" />
            </div>

            <div className="absolute top-6 left-6 pointer-events-none font-mono">
                <div className="text-nexus-green text-xs opacity-60 tracking-[0.2em] uppercase mb-1">
                    Axiomatic Manifold [12:512]
                </div>
                <div className="text-white text-[10px] opacity-40">
                    Target: Strix Halo (UMA) | LOD: {lodTier === LOD_TIERS.ULTRA ? 'ULTRA' : lodTier === LOD_TIERS.HALO ? 'HALO' : 'STARDUST'}
                </div>
                <div className="text-white text-[10px] opacity-40 mt-1">
                    Nodes: {nodes.length} | Coherence Range: 0.5 \u00B1 0.2
                </div>
            </div>

            <div className="absolute bottom-6 right-6">
                <button
                    onClick={() => setAudioActive(!audioActive)}
                    className={`px-4 py-2 border font-mono text-[10px] transition-all ${audioActive
                        ? 'bg-nexus-green/20 border-nexus-green text-nexus-green'
                        : 'bg-white/10 border-white/30 text-white/50 hover:bg-white/20'
                        }`}
                >
                    🔊 HIHO SONIFICATION: {audioActive ? 'ON' : 'OFF'}
                </button>
            </div>
        </div>
    );
};
