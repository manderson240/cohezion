import React, { useMemo, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Stars, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import { useManifold, ManifoldPoint } from '../../hooks/useManifold';

const EVOParticles = ({ points }: { points: ManifoldPoint[] }) => {
    const meshRef = useRef<THREE.Points>(null);

    const [positions, colors] = useMemo(() => {
        const count = points.length;
        const pos = new Float32Array(count * 3);
        const col = new Float32Array(count * 3);

        points.forEach((p, i) => {
            // Map 12D Doer state to 3D position
            pos[i * 3] = p.doer[0] * 5;
            pos[i * 3 + 1] = p.doer[1] * 5;
            pos[i * 3 + 2] = p.doer[2] * 5;

            // Map coherence to color (Red for 0, Green for 0.5, Blue for 1.0)
            const hue = p.coherence * 120; // 0 to 120 (Red to Green)
            const color = new THREE.Color().setHSL(hue / 360, 0.8, 0.5);
            col[i * 3] = color.r;
            col[i * 3 + 1] = color.g;
            col[i * 3 + 2] = color.b;
        });

        return [pos, col];
    }, [points]);

    useFrame((state) => {
        if (meshRef.current) {
            meshRef.current.rotation.y += 0.001;
        }
    });

    return (
        <points ref={meshRef}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={points.length}
                    array={positions}
                    itemSize={3}
                />
                <bufferAttribute
                    attach="attributes-color"
                    count={points.length}
                    array={colors}
                    itemSize={3}
                />
            </bufferGeometry>
            <pointsMaterial
                size={0.2}
                vertexColors
                transparent
                opacity={0.8}
                blending={THREE.AdditiveBlending}
            />
        </points>
    );
};

export const ManifoldCanvas = () => {
    const { points, latestPoint } = useManifold();

    return (
        <div className="w-full h-full relative bg-void-black">
            <Canvas>
                <PerspectiveCamera makeDefault position={[0, 0, 20]} />
                <Stars radius={100} depth={50} count={5000} factor={4} saturation={0} fade speed={1} />
                <ambientLight intensity={0.5} />
                
                <EVOParticles points={points} />
                
                <OrbitControls enableDamping />
            </Canvas>

            {/* Telemetry Overlay */}
            <div className="absolute top-4 left-4 pointer-events-none p-4 bg-black/60 border-l-2 border-nexus-green backdrop-blur-md font-mono text-[10px]">
                <div className="text-nexus-green uppercase tracking-widest mb-2 opacity-80">Triune Manifold Telemetry</div>
                {latestPoint ? (
                    <div className="space-y-1">
                        <div className="text-white">Trajectory: <span className="text-nexus-green">{latestPoint.trajectory_id}</span></div>
                        <div className="text-white">Coherence: <span className={latestPoint.coherence > 0.45 && latestPoint.coherence < 0.55 ? "text-nexus-green" : "text-red-400"}>
                            {latestPoint.coherence?.toFixed(4)}
                        </span></div>
                        <div className="text-white opacity-60">Doer [12D]: {latestPoint.doer.slice(0, 3).map(v => (v ?? 0).toFixed(2)).join(', ')}...</div>
                    </div>
                ) : (
                    <div className="text-white animate-pulse">Awaiting connection...</div>
                )}
            </div>
        </div>
    );
};
