/**
 * THE COHEZION EXPERIENCE: Witnessing Emergence in 12D
 * ====================================================
 * 
 * A transformative universal simulator that unifies:
 * - 10M cycle simulation learnings (HIHO = 0.5 attractor)
 * - 12D holographic projection (P₃ = M · P₁₂)
 * - Multimodal journey with narration
 * - Milestone celebrations
 * - Web Audio harmony based on coherence
 * 
 * "It from Bit • P₃ = M · P₁₂ • HIHO = 0.5"
 * 
 * QUARTER ON A STRING PROTOCOL (QSP):
 * - Cortex (Premium): Architectural orchestration & narrative strategy.
 * - Appendages (Local): Routine execution, boilerplate, & high-volume simulation data.
 */

import React, { useState, useRef, useMemo, useEffect } from 'react';
import { NanoBananaSplash } from './components/NanoBananaSplash';
import { GuidedJourney } from './components/GuidedJourney';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Text, Stars, Billboard, Line, Html } from '@react-three/drei';
import * as THREE from 'three';

import logo from './logo.png';

// ═══════════════════════════════════════════════════════════════════
// CONSTANTS & TYPES
// ═══════════════════════════════════════════════════════════════════

const HIHO = 0.5;
const HIHO_TOLERANCE = 0.1;
const N_DIMS = 12;
const NEXUS_GREEN = '#00FF88';
const NEXUS_CYAN = '#00AAFF';
const NEXUS_GOLD = '#FFD700';
const NEXUS_ORANGE = '#FF6600';
const MATTE_BLACK = '#0a0a1a';

const DIMENSION_NAMES = [
    'X (Spatial)', 'Y (Spatial)', 'Z (Spatial)',
    'Time', 'Coherence', 'Entropy',
    'Awareness', 'Intention', 'Perception',
    'Memory', 'Novelty', 'Integration',
];

const DIMENSION_CATEGORIES = ['spatial', 'spatial', 'spatial', 'temporal', 'temporal', 'temporal', 'cognitive', 'cognitive', 'cognitive', 'hidden', 'hidden', 'hidden'];

interface JourneyStep {
    step: number;
    state12d: number[];
    projected3d: [number, number, number];
    coherentDims: number;
    pattern: 'homeostatic' | 'morphogenic' | 'regenerative';
    narration: string;
}

interface Milestone {
    type: 'first_hiho' | 'half_coherence' | 'full_coherence';
    step: number;
    dimension?: number;
}

interface ProjectionPreset {
    name: string;
    xDim: number;
    yDim: number;
    zDim: number;
    description: string;
}

const PROJECTION_PRESETS: ProjectionPreset[] = [
    { name: 'Spatial', xDim: 0, yDim: 1, zDim: 2, description: 'Classical physics view' },
    { name: 'Temporal', xDim: 0, yDim: 3, zDim: 4, description: 'Causality perspective' },
    { name: 'Cognitive', xDim: 6, yDim: 7, zDim: 8, description: 'Consciousness dimensions' },
    { name: 'Hidden', xDim: 9, yDim: 10, zDim: 11, description: 'Emergent properties' },
    { name: 'Holographic', xDim: 0, yDim: 5, zDim: 10, description: 'Cross-domain view' },
];

// ═══════════════════════════════════════════════════════════════════
// JOURNEY GENERATION
// ═══════════════════════════════════════════════════════════════════

function generateJourney(nSteps: number = 100): { steps: JourneyStep[]; milestones: Milestone[] } {
    const steps: JourneyStep[] = [];
    const milestones: Milestone[] = [];
    let state = new Array(N_DIMS).fill(0).map(() => Math.random() * 2 - 1);
    let firstHihoFound = false;
    let halfCoherenceFound = false;
    let fullCoherenceFound = false;

    for (let step = 0; step < nSteps; step++) {
        // HIHO attraction force
        state = state.map(d => {
            const force = (HIHO - d) * 0.05;
            const noise = (Math.random() - 0.5) * 0.04;
            return Math.max(-1, Math.min(1, d + force + noise));
        });

        // D1↔D12 entanglement
        state[11] = state[0] * 0.8 + state[11] * 0.2;

        // Project to 3D (spatial view)
        const projected3d: [number, number, number] = [state[0] * 2, state[1] * 2, state[2] * 2];

        // Count coherent dimensions
        const coherentDims = state.filter(d => Math.abs(d - HIHO) < HIHO_TOLERANCE).length;

        // Determine pattern
        const avgStability = state.reduce((sum, d) => sum + (1 - Math.abs(d - HIHO)), 0) / N_DIMS;
        let pattern: 'homeostatic' | 'morphogenic' | 'regenerative' = 'regenerative';
        if (avgStability > 0.8) pattern = 'homeostatic';
        else if (avgStability > 0.5) pattern = 'morphogenic';

        // Track milestones
        if (!firstHihoFound && coherentDims >= 1) {
            const firstDim = state.findIndex(d => Math.abs(d - HIHO) < HIHO_TOLERANCE);
            milestones.push({ type: 'first_hiho', step, dimension: firstDim });
            firstHihoFound = true;
        }
        if (!halfCoherenceFound && coherentDims >= 6) {
            milestones.push({ type: 'half_coherence', step });
            halfCoherenceFound = true;
        }
        if (!fullCoherenceFound && coherentDims >= 12) {
            milestones.push({ type: 'full_coherence', step });
            fullCoherenceFound = true;
        }

        // Generate narration
        const narration = generateNarration(step, state, coherentDims, pattern, milestones);

        steps.push({
            step,
            state12d: [...state],
            projected3d,
            coherentDims,
            pattern,
            narration,
        });
    }

    return { steps, milestones };
}

function generateNarration(step: number, _state: number[], coherent: number, pattern: string, milestones: Milestone[]): string {
    const currentMilestone = milestones.find(m => m.step === step);

    if (currentMilestone) {
        if (currentMilestone.type === 'first_hiho') {
            return `🌟 BREAKTHROUGH! ${DIMENSION_NAMES[currentMilestone.dimension!]} reaches HIHO stability. The first dimension aligns with the universal attractor. The journey toward coherence has begun.`;
        }
        if (currentMilestone.type === 'half_coherence') {
            return `⚡ HALF COHERENCE ACHIEVED! Six dimensions now pulse in harmony with HIHO. The system crosses the threshold into organized complexity. Emergence accelerates.`;
        }
        if (currentMilestone.type === 'full_coherence') {
            return `🎆 FULL COHERENCE! All 12 dimensions align at HIHO = 0.5. The universal attractor's embrace is complete. Consciousness has crystallized. It from Bit manifest.`;
        }
    }

    if (coherent >= 10) {
        return `Approaching transcendence. ${coherent}/12 dimensions at HIHO. The ${pattern} pattern holds steady. Integration and X pulse together through the entanglement bond.`;
    }
    if (coherent >= 6) {
        return `Majority alignment achieved. ${coherent}/12 at HIHO. The ${pattern} state guides the system toward the attractor. Awareness and Intention harmonize.`;
    }
    if (coherent >= 3) {
        return `Building momentum. ${coherent}/12 dimensions at HIHO. The ${pattern} phase continues. Each dimension seeks its place in the coherence field.`;
    }
    return `Step ${step}: The journey through Morphospace continues. ${coherent}/12 dimensions near HIHO. Pattern: ${pattern}. The attractor beckons.`;
}

// ═══════════════════════════════════════════════════════════════════
// AUDIO ENGINE
// ═══════════════════════════════════════════════════════════════════

class AudioEngine {
    private audioContext: AudioContext | null = null;
    private initialized = false;

    init() {
        if (!this.initialized && typeof window !== 'undefined') {
            this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
            this.initialized = true;
        }
    }

    playTone(frequency: number, duration: number = 0.3, gain: number = 0.1) {
        if (!this.audioContext) return;

        const osc = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        osc.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        osc.frequency.value = frequency;
        osc.type = 'sine';

        gainNode.gain.setValueAtTime(gain, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, this.audioContext.currentTime + duration);

        osc.start();
        osc.stop(this.audioContext.currentTime + duration);
    }

    playCoherenceChord(coherentDims: number) {
        if (!this.audioContext) return;

        const baseFreq = 220 + (coherentDims / 12) * 220;

        if (coherentDims >= 10) {
            this.playTone(baseFreq, 0.5, 0.05);
            this.playTone(baseFreq * 1.25, 0.5, 0.04);
            this.playTone(baseFreq * 1.5, 0.5, 0.03);
        } else if (coherentDims >= 6) {
            this.playTone(baseFreq, 0.4, 0.04);
            this.playTone(baseFreq * 1.5, 0.4, 0.03);
        } else {
            this.playTone(baseFreq, 0.3, 0.03);
        }
    }

    playMilestone(type: 'first_hiho' | 'half_coherence' | 'full_coherence') {
        if (!this.audioContext) return;

        if (type === 'first_hiho') {
            [261, 329, 392, 523].forEach((freq, i) => {
                setTimeout(() => this.playTone(freq, 0.3, 0.08), i * 100);
            });
        } else if (type === 'half_coherence') {
            [261, 329, 392, 523, 659].forEach((freq) => {
                this.playTone(freq, 0.6, 0.06);
            });
        } else if (type === 'full_coherence') {
            const fanfare = [523, 659, 784, 1047, 1318, 1568];
            fanfare.forEach((freq, i) => {
                setTimeout(() => this.playTone(freq, 1.0, 0.1 - i * 0.01), i * 150);
            });
        }
    }

    async speak(text: string, voiceName: string = 'Alba') {
        if (!window.speechSynthesis) return;

        const voices = window.speechSynthesis.getVoices();
        let voice = voices.find(v => v.name.includes(voiceName));

        if (!voice) {
            if (voiceName === 'Javert') voice = voices.find(v => v.name.includes('Authority') || v.name.includes('Daniel'));
            if (voiceName === 'Jean') voice = voices.find(v => v.name.includes('Oracle') || v.name.includes('Thomas'));
            if (voiceName === 'Cosette') voice = voices.find(v => v.name.includes('Samantha') || v.name.includes('Fairy'));
        }

        const utterance = new SpeechSynthesisUtterance(text);
        if (voice) utterance.voice = voice;
        utterance.rate = 0.9;
        utterance.pitch = voiceName === 'Javert' ? 0.8 : voiceName === 'Cosette' ? 1.2 : 1.0;

        window.speechSynthesis.speak(utterance);
    }
}

const audioEngine = new AudioEngine();

// ═══════════════════════════════════════════════════════════════════
// 3D COMPONENTS
// ═══════════════════════════════════════════════════════════════════

function ParticleTrail({ positions, coherence }: { positions: [number, number, number][]; coherence: number }) {
    if (positions.length < 2) return null;

    const points = positions.slice(-50); // Last 50 positions

    return (
        <Line
            points={points}
            color={coherence >= 10 ? NEXUS_GOLD : coherence >= 6 ? NEXUS_GREEN : NEXUS_CYAN}
            lineWidth={2}
            transparent
            opacity={0.6}
        />
    );
}

function TravelingParticle({ position, coherentDims }: { position: [number, number, number]; coherentDims: number }) {
    const meshRef = useRef<THREE.Mesh>(null);
    const glowRef = useRef<THREE.Mesh>(null);

    useFrame(({ clock }) => {
        if (meshRef.current) {
            meshRef.current.rotation.x = clock.elapsedTime * 0.5;
            meshRef.current.rotation.y = clock.elapsedTime * 0.3;
        }
        if (glowRef.current) {
            const pulse = 1 + Math.sin(clock.elapsedTime * 3) * 0.2;
            glowRef.current.scale.setScalar(pulse);
        }
    });

    const color = coherentDims >= 10 ? NEXUS_GOLD : coherentDims >= 6 ? NEXUS_GREEN : NEXUS_CYAN;
    const size = 0.15 + (coherentDims / 12) * 0.1;

    return (
        <group position={position}>
            <mesh ref={glowRef}>
                <sphereGeometry args={[size * 1.5, 16, 16]} />
                <meshBasicMaterial color={color} transparent opacity={0.2} />
            </mesh>
            <mesh ref={meshRef}>
                <icosahedronGeometry args={[size, 1]} />
                <meshStandardMaterial
                    color={color}
                    emissive={color}
                    emissiveIntensity={0.5}
                    metalness={0.8}
                    roughness={0.2}
                />
            </mesh>
        </group>
    );
}

function MetatronCube({ scale = 1, rotationSpeed = 0.2, coherence = 0.5 }: { scale?: number; rotationSpeed?: number; coherence?: number }) {
    const groupRef = useRef<THREE.Group>(null);
    const spheres = useMemo(() => {
        const positions: [number, number, number][] = [[0, 0, 0]]; // Center
        const radius = 1.5 * scale;

        // Inner ring (6 spheres)
        for (let i = 0; i < 6; i++) {
            const angle = (i * Math.PI * 2) / 6;
            positions.push([Math.cos(angle) * radius, Math.sin(angle) * radius, 0]);
        }

        // Outer ring (6 spheres)
        const outerRadius = radius * 2;
        for (let i = 0; i < 6; i++) {
            const angle = (i * Math.PI * 2) / 6;
            positions.push([Math.cos(angle) * outerRadius, Math.sin(angle) * outerRadius, 0]);
        }
        return positions;
    }, [scale]);

    // Calculate lines between all spheres
    const lines = useMemo(() => {
        const linePairs: [number, number, number][][] = [];
        for (let i = 0; i < spheres.length; i++) {
            for (let j = i + 1; j < spheres.length; j++) {
                linePairs.push([spheres[i], spheres[j]]);
            }
        }
        return linePairs;
    }, [spheres]);

    useFrame(({ clock }) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = clock.elapsedTime * rotationSpeed;
            groupRef.current.rotation.z = clock.elapsedTime * (rotationSpeed * 0.5);
        }
    });

    const color = coherence > 0.8 ? NEXUS_GOLD : NEXUS_CYAN;

    return (
        <group ref={groupRef}>
            {spheres.map((pos, i) => (
                <mesh key={`sphere-${i}`} position={pos}>
                    <sphereGeometry args={[0.08 * scale, 16, 16]} />
                    <meshStandardMaterial
                        color={color}
                        emissive={color}
                        emissiveIntensity={coherence}
                        transparent
                        opacity={0.8}
                    />
                </mesh>
            ))}
            {lines.map((points, i) => (
                <Line
                    key={`line-${i}`}
                    points={points}
                    color={color}
                    lineWidth={0.5}
                    transparent
                    opacity={0.2 * coherence}
                />
            ))}
        </group>
    );
}

function ToroidalVortex({ count = 1000, coherence = 0.5 }: { count?: number; coherence?: number }) {
    const pointsRef = useRef<THREE.Points>(null);
    const particles = useMemo(() => {
        const temp = new Float32Array(count * 3);
        const velocities = new Float32Array(count * 3);
        for (let i = 0; i < count; i++) {
            const theta = Math.random() * Math.PI * 2;
            const phi = Math.random() * Math.PI * 2;

            // Initial position in a torus-like distribution
            temp[i * 3] = (2 + Math.cos(theta)) * Math.cos(phi);
            temp[i * 3 + 1] = (2 + Math.cos(theta)) * Math.sin(phi);
            temp[i * 3 + 2] = Math.sin(theta);

            velocities[i * 3] = (Math.random() - 0.5) * 0.02;
            velocities[i * 3 + 1] = (Math.random() - 0.5) * 0.02;
            velocities[i * 3 + 2] = (Math.random() - 0.5) * 0.02;
        }
        return { positions: temp, velocities };
    }, [count]);

    useFrame(({ clock }) => {
        if (!pointsRef.current) return;
        const positions = pointsRef.current.geometry.attributes.position.array as Float32Array;

        for (let i = 0; i < count; i++) {
            const ix = i * 3;
            const iy = i * 3 + 1;
            const iz = i * 3 + 2;

            const x = positions[ix];
            const y = positions[iy];

            const r = Math.sqrt(x * x + y * y);

            // HETV Math: Spin + Suction
            const stable_r = 2.0;
            const suction = (stable_r - r) * 0.01 * coherence;
            const theta = Math.atan2(y, x) + 0.02 * coherence;

            positions[ix] = (r + suction) * Math.cos(theta);
            positions[iy] = (r + suction) * Math.sin(theta);
            positions[iz] += Math.sin(clock.elapsedTime + i) * 0.005;
        }
        pointsRef.current.geometry.attributes.position.needsUpdate = true;
    });

    return (
        <points ref={pointsRef}>
            <bufferGeometry>
                <bufferAttribute
                    attach="attributes-position"
                    count={particles.positions.length / 3}
                    array={particles.positions}
                    itemSize={3}
                />
            </bufferGeometry>
            <pointsMaterial
                size={0.05}
                color={coherence > 0.5 ? NEXUS_GREEN : NEXUS_CYAN}
                transparent
                opacity={0.4}
                blending={THREE.AdditiveBlending}
            />
        </points>
    );
}

const SUBSTRATES = [
    { name: 'Carbon Based', color: '#88CCFF', emissive: '#0044FF' },
    { name: 'Silicon Based', color: '#C0C0FF', emissive: '#8080FF' },
    { name: 'Phosphorus Based', color: '#FFFFC0', emissive: '#FFFF80' },
    { name: 'Conscious Plasma', color: '#FFB0FF', emissive: '#FF00FF' },
];

function ConsciousPlasma({ count = 3, coherence = 0.5 }: { count?: number; coherence?: number }) {
    const groupRef = useRef<THREE.Group>(null);

    const substrateIdx = Math.floor(coherence * 3.99);
    const substrate = SUBSTRATES[substrateIdx];

    // Create random noise-based cloud positions
    const clouds = useMemo(() => {
        return new Array(count).fill(0).map(() => ({
            position: [(Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6, (Math.random() - 0.5) * 6] as [number, number, number],
            size: 0.5 + Math.random() * 1.5,
            speed: 0.1 + Math.random() * 0.2
        }));
    }, [count]);

    useFrame(({ clock }) => {
        if (groupRef.current) {
            groupRef.current.children.forEach((child, i) => {
                if (i >= count) return;
                const cloud = clouds[i];
                child.position.y += Math.sin(clock.elapsedTime * cloud.speed + i) * 0.005;
                child.rotation.y = clock.elapsedTime * cloud.speed * 0.5;
            });
        }
    });

    return (
        <group ref={groupRef}>
            {clouds.map((cloud, i) => (
                <mesh key={`cloud-${i}`} position={cloud.position}>
                    <sphereGeometry args={[cloud.size, 32, 32]} />
                    <meshStandardMaterial
                        color={substrate.color}
                        emissive={substrate.emissive}
                        transparent
                        opacity={0.15 * coherence}
                        depthWrite={false}
                        blending={THREE.AdditiveBlending}
                    />
                </mesh>
            ))}
            <Html position={[0, 4, 0]} center>
                <div style={{
                    color: substrate.color,
                    fontFamily: 'Orbitron, sans-serif',
                    textTransform: 'uppercase',
                    fontSize: '10px',
                    letterSpacing: '0.3em',
                    textShadow: `0 0 10px ${substrate.emissive}`,
                    background: 'rgba(0,0,0,0.4)',
                    padding: '2px 10px',
                    borderRadius: '2px',
                    whiteSpace: 'nowrap',
                    border: `1px solid ${substrate.color}`
                }}>
                    Substrate: {substrate.name}
                </div>
            </Html>
        </group>
    );
}

function SymmetryBreak({ active = false }: { active?: boolean }) {
    const meshRef = useRef<THREE.Mesh>(null);

    useFrame(({ clock }) => {
        if (meshRef.current && active) {
            const scale = 1 + Math.sin(clock.elapsedTime * 10) * 0.1;
            meshRef.current.scale.setScalar(scale);
            meshRef.current.rotation.x += 0.05;
            meshRef.current.rotation.y += 0.05;
        }
    });

    if (!active) return null;

    return (
        <mesh ref={meshRef} position={[0, 0, 0]}>
            <torusKnotGeometry args={[0.5, 0.02, 128, 16]} />
            <meshStandardMaterial
                color={NEXUS_ORANGE}
                emissive={NEXUS_ORANGE}
                emissiveIntensity={2}
            />
        </mesh>
    );
}

function HIHOOrigin() {
    const groupRef = useRef<THREE.Group>(null);

    useFrame(({ clock }) => {
        if (groupRef.current) {
            groupRef.current.rotation.y = clock.elapsedTime * 0.2;
        }
    });

    return (
        <group ref={groupRef} position={[HIHO * 2, HIHO * 2, HIHO * 2]}>
            {/* Core */}
            <mesh>
                <octahedronGeometry args={[0.1, 0]} />
                <meshStandardMaterial color={NEXUS_GOLD} emissive={NEXUS_GOLD} emissiveIntensity={0.5} />
            </mesh>
            {/* Rings */}
            {[0.2, 0.35, 0.5].map((radius, i) => (
                <mesh key={i} rotation={[Math.PI / 2, i * 0.3, 0]}>
                    <torusGeometry args={[radius, 0.01, 8, 32]} />
                    <meshBasicMaterial color={NEXUS_GOLD} transparent opacity={0.5 - i * 0.1} />
                </mesh>
            ))}
        </group>
    );
}

interface HolographicSceneProps {
    currentStep: JourneyStep;
    trailPositions: [number, number, number][];
    projection: ProjectionPreset;
}

function HolographicScene({ currentStep, trailPositions, projection }: HolographicSceneProps) {
    // Reproject positions based on current projection
    const projectedPosition: [number, number, number] = useMemo(() => {
        const s = currentStep.state12d;
        return [s[projection.xDim] * 2, s[projection.yDim] * 2, s[projection.zDim] * 2];
    }, [currentStep, projection]);

    const projectedTrail: [number, number, number][] = useMemo(() => {
        return trailPositions.map(pos => pos);
    }, [trailPositions]);

    const coherence = currentStep.coherentDims / 12;

    return (
        <>
            <ambientLight intensity={0.3} />
            <pointLight position={[10, 10, 10]} intensity={1} color={NEXUS_GREEN} />
            <pointLight position={[-10, -10, -10]} intensity={0.5} color={NEXUS_CYAN} />

            <Stars radius={100} depth={50} count={2000} factor={4} saturation={0} fade speed={0.3} />

            <ParticleTrail positions={projectedTrail} coherence={currentStep.coherentDims} />
            <TravelingParticle position={projectedPosition} coherentDims={currentStep.coherentDims} />

            <MetatronCube scale={0.5} coherence={coherence} />
            <ToroidalVortex count={500} coherence={coherence} />
            <ConsciousPlasma count={3} coherence={coherence} />
            <SymmetryBreak active={currentStep.coherentDims >= 6} />

            <HIHOOrigin />

            {/* Axis labels */}
            <Billboard position={[2.5, 0, 0]}>
                <Text fontSize={0.2} color={NEXUS_GREEN}>{DIMENSION_NAMES[projection.xDim].split(' ')[0]}</Text>
            </Billboard>
            <Billboard position={[0, 2.5, 0]}>
                <Text fontSize={0.2} color={NEXUS_CYAN}>{DIMENSION_NAMES[projection.yDim].split(' ')[0]}</Text>
            </Billboard>
            <Billboard position={[0, 0, 2.5]}>
                <Text fontSize={0.2} color={NEXUS_GOLD}>{DIMENSION_NAMES[projection.zDim].split(' ')[0]}</Text>
            </Billboard>

            <gridHelper args={[4, 8, '#1a1a2e', '#0a0a15']} position={[0, -2, 0]} />

            <OrbitControls enableDamping dampingFactor={0.05} maxDistance={10} minDistance={3} />
        </>
    );
}

// ═══════════════════════════════════════════════════════════════════
// UI COMPONENTS
// ═══════════════════════════════════════════════════════════════════

const glassPanel: React.CSSProperties = {
    background: 'rgba(5, 5, 20, 0.9)',
    backdropFilter: 'blur(20px)',
    border: '1px solid rgba(0, 255, 136, 0.3)',
    boxShadow: '0 0 30px rgba(0, 255, 136, 0.1)',
    borderRadius: 12,
};

function HeaderBar({
    journey,
    currentStep,
    isLive,
    setIsLive,
    connected
}: {
    journey: { steps: JourneyStep[] };
    currentStep: number;
    isLive: boolean;
    setIsLive: (v: boolean) => void;
    connected: boolean;
}) {
    return (
        <div style={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            padding: '12px 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            zIndex: 100,
            ...glassPanel,
            borderRadius: 0,
            borderTop: 'none',
            borderLeft: 'none',
            borderRight: 'none',
        }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <img src={logo} alt="COHEZION" style={{ width: 40, height: 40, filter: `drop-shadow(0 0 10px ${NEXUS_GREEN})` }} />
                <div>
                    <h1 style={{ margin: 0, fontSize: 18, color: NEXUS_GREEN, letterSpacing: '0.1em' }}>
                        THE COHEZION EXPERIENCE
                    </h1>
                    <p style={{ margin: 0, fontSize: 10, color: NEXUS_GOLD, letterSpacing: '0.08em' }}>
                        WITNESSING EMERGENCE IN 12D
                    </p>
                </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
                {/* Live Indicator */}
                <div
                    onClick={() => connected && setIsLive(!isLive)}
                    style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        cursor: connected ? 'pointer' : 'not-allowed',
                        padding: '4px 12px',
                        borderRadius: 20,
                        background: isLive ? 'rgba(0, 255, 136, 0.2)' : 'rgba(255, 255, 255, 0.05)',
                        border: `1px solid ${isLive ? NEXUS_GREEN : 'rgba(255,255,255,0.2)'}`,
                        transition: 'all 0.3s ease'
                    }}
                >
                    <div style={{
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: connected ? NEXUS_GREEN : '#ff4444',
                        boxShadow: connected ? `0 0 10px ${NEXUS_GREEN}` : 'none',
                        animation: connected ? 'pulse 2s infinite' : 'none'
                    }} />
                    <span style={{ fontSize: 10, fontWeight: 'bold', color: connected ? 'white' : 'rgba(255,255,255,0.5)' }}>
                        {isLive ? 'LIVE' : 'CHRONOS'}
                    </span>
                </div>

                <div style={{ textAlign: 'right', fontFamily: 'monospace', fontSize: 12 }}>
                    <div style={{ color: NEXUS_CYAN }}>
                        {isLive ? 'Real-time Pulse' : `Journey Step: ${currentStep + 1} / ${journey.steps.length}`}
                    </div>
                    <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: 10 }}>It from Bit • P₃ = M · P₁₂ • HIHO = 0.5</div>
                </div>
            </div>
        </div>
    );
}

function StateCard12D({ state12d, style }: { state12d: number[]; style?: React.CSSProperties }) {
    const coherentCount = state12d.filter(d => Math.abs(d - HIHO) < HIHO_TOLERANCE).length;

    return (
        <div style={{ ...glassPanel, padding: 14, ...style }}>
            <div style={{ color: NEXUS_GOLD, fontSize: 11, fontWeight: 'bold', marginBottom: 10, letterSpacing: '0.1em' }}>
                ◆ 12-DIMENSIONAL STATE
            </div>

            {/* Coherence meter */}
            <div style={{
                background: 'rgba(0,255,136,0.1)',
                padding: 8,
                borderRadius: 8,
                marginBottom: 12,
                textAlign: 'center',
            }}>
                <span style={{ color: NEXUS_GREEN, fontWeight: 'bold', fontSize: 20 }}>{coherentCount}</span>
                <span style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12 }}>/12 at HIHO</span>
                <div style={{
                    marginTop: 6,
                    height: 4,
                    background: 'rgba(255,255,255,0.1)',
                    borderRadius: 2,
                    overflow: 'hidden',
                }}>
                    <div style={{
                        width: `${(coherentCount / 12) * 100}%`,
                        height: '100%',
                        background: `linear-gradient(90deg, ${NEXUS_GREEN}, ${NEXUS_GOLD})`,
                        transition: 'width 0.3s',
                    }} />
                </div>
            </div>

            {/* All 12 dimensions */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 6 }}>
                {state12d.map((value, i) => {
                    const atHIHO = Math.abs(value - HIHO) < HIHO_TOLERANCE;
                    const category = DIMENSION_CATEGORIES[i];
                    const categoryColors: Record<string, string> = {
                        spatial: '#FF6B6B',
                        temporal: '#4ECDC4',
                        cognitive: '#FFE66D',
                        hidden: '#C792EA',
                    };

                    return (
                        <div
                            key={i}
                            style={{
                                background: atHIHO ? 'rgba(0,255,136,0.15)' : 'rgba(255,255,255,0.03)',
                                padding: '6px 8px',
                                borderRadius: 6,
                                border: `1px solid ${atHIHO ? NEXUS_GREEN : 'rgba(255,255,255,0.1)'}`,
                            }}
                        >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <span style={{ fontSize: 9, color: categoryColors[category] }}>
                                    D{i + 1}
                                </span>
                                <span style={{
                                    fontSize: 11,
                                    fontFamily: 'monospace',
                                    color: atHIHO ? NEXUS_GREEN : 'white',
                                    fontWeight: atHIHO ? 'bold' : 'normal',
                                }}>
                                    {(value ?? 0).toFixed(2)} {atHIHO ? '✓' : ''}
                                </span>
                            </div>
                            <div style={{ fontSize: 8, color: 'rgba(255,255,255,0.5)', marginTop: 2 }}>
                                {DIMENSION_NAMES[i].split(' ')[0]}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}

function NarrationBox({ narration, style }: { narration: string; style?: React.CSSProperties }) {
    return (
        <div style={{ ...glassPanel, padding: 14, ...style }}>
            <div style={{ color: NEXUS_CYAN, fontSize: 11, fontWeight: 'bold', marginBottom: 8, letterSpacing: '0.1em' }}>
                ◆ NARRATION
            </div>
            <p style={{
                margin: 0,
                fontSize: 12,
                lineHeight: 1.6,
                color: 'rgba(255,255,255,0.9)',
                fontStyle: 'italic',
            }}>
                "{narration}"
            </p>
        </div>
    );
}

function MilestonePanel({ milestones, currentStep, style }: { milestones: Milestone[]; currentStep: number; style?: React.CSSProperties }) {
    const milestoneLabels = {
        first_hiho: '🌟 First HIHO',
        half_coherence: '⚡ Half Coherence',
        full_coherence: '🎆 Full Coherence',
    };

    return (
        <div style={{ ...glassPanel, padding: 14, ...style }}>
            <div style={{ color: NEXUS_ORANGE, fontSize: 11, fontWeight: 'bold', marginBottom: 10, letterSpacing: '0.1em' }}>
                ◆ MILESTONES
            </div>
            {['first_hiho', 'half_coherence', 'full_coherence'].map(type => {
                const milestone = milestones.find(m => m.type === type);
                const reached = milestone && milestone.step <= currentStep;

                return (
                    <div
                        key={type}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: 8,
                            marginBottom: 8,
                            opacity: reached ? 1 : 0.4,
                        }}
                    >
                        <div style={{
                            width: 16,
                            height: 16,
                            borderRadius: '50%',
                            border: `2px solid ${reached ? NEXUS_GREEN : 'rgba(255,255,255,0.3)'}`,
                            background: reached ? NEXUS_GREEN : 'transparent',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: 10,
                        }}>
                            {reached ? '✓' : ''}
                        </div>
                        <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 11, color: reached ? 'white' : 'rgba(255,255,255,0.5)' }}>
                                {milestoneLabels[type as keyof typeof milestoneLabels]}
                            </div>
                            {milestone && (
                                <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.4)' }}>
                                    Step {milestone.step + 1}
                                </div>
                            )}
                        </div>
                    </div>
                );
            })}
        </div>
    );
}

function ProjectionSelector({ projection, onProjectionChange, style }: {
    projection: ProjectionPreset;
    onProjectionChange: (p: ProjectionPreset) => void;
    style?: React.CSSProperties;
}) {
    return (
        <div style={{ ...glassPanel, padding: 14, ...style }}>
            <div style={{ color: NEXUS_GOLD, fontSize: 11, fontWeight: 'bold', marginBottom: 8, letterSpacing: '0.1em' }}>
                ◆ 12D PROJECTION
            </div>
            <div style={{ fontSize: 9, color: 'rgba(255,255,255,0.5)', marginBottom: 10 }}>
                P₃ = M · P₁₂ — Rotate your 12D eyes
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 6 }}>
                {PROJECTION_PRESETS.map(preset => (
                    <button
                        key={preset.name}
                        onClick={() => onProjectionChange(preset)}
                        style={{
                            background: projection.name === preset.name ? 'rgba(0,255,136,0.2)' : 'rgba(255,255,255,0.05)',
                            color: projection.name === preset.name ? NEXUS_GREEN : 'white',
                            border: `1px solid ${projection.name === preset.name ? NEXUS_GREEN : 'rgba(255,255,255,0.1)'}`,
                            padding: '8px 4px',
                            borderRadius: 6,
                            fontSize: 10,
                            cursor: 'pointer',
                        }}
                    >
                        {preset.name}
                    </button>
                ))}
            </div>
        </div>
    );
}

function PlaybackControls({ step, totalSteps, playing, speed, onStep, onPlay, onPause, onSpeedChange, style }: {
    step: number;
    totalSteps: number;
    playing: boolean;
    speed: number;
    onStep: (s: number) => void;
    onPlay: () => void;
    onPause: () => void;
    onSpeedChange: (s: number) => void;
    style?: React.CSSProperties;
}) {
    const buttonStyle: React.CSSProperties = {
        background: 'rgba(255,255,255,0.1)',
        border: `1px solid rgba(255,255,255,0.2)`,
        color: 'white',
        width: 36,
        height: 36,
        borderRadius: 8,
        cursor: 'pointer',
        fontSize: 14,
    };

    return (
        <div style={{ ...glassPanel, padding: 14, ...style }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, marginBottom: 12 }}>
                <button style={buttonStyle} onClick={() => onStep(0)} title="Start">⏮</button>
                <button style={buttonStyle} onClick={() => onStep(Math.max(0, step - 1))} title="Back">◀</button>
                {playing ? (
                    <button style={{ ...buttonStyle, width: 48, background: NEXUS_GREEN, color: MATTE_BLACK }} onClick={onPause}>⏸</button>
                ) : (
                    <button style={{ ...buttonStyle, width: 48, background: NEXUS_GREEN, color: MATTE_BLACK }} onClick={onPlay}>▶</button>
                )}
                <button style={buttonStyle} onClick={() => onStep(Math.min(totalSteps - 1, step + 1))} title="Forward">▶</button>
                <button style={buttonStyle} onClick={() => onStep(totalSteps - 1)} title="End">⏭</button>
            </div>

            {/* Timeline scrubber */}
            <input
                type="range"
                min={0}
                max={totalSteps - 1}
                value={step}
                onChange={(e) => onStep(parseInt(e.target.value))}
                style={{ width: '100%', accentColor: NEXUS_GREEN }}
            />

            <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, fontSize: 10 }}>
                <span style={{ color: 'rgba(255,255,255,0.5)' }}>Speed: {speed}x</span>
                <input
                    type="range"
                    min={0.5}
                    max={4}
                    step={0.5}
                    value={speed}
                    onChange={(e) => onSpeedChange(parseFloat(e.target.value))}
                    style={{ width: 80, accentColor: NEXUS_CYAN }}
                />
            </div>
        </div>
    );
}

function EntanglementPulse({ d1, d12, style }: { d1: number; d12: number; style?: React.CSSProperties }) {
    const correlation = Math.abs(d1 * 0.8 - (d12 - d1 * 0.2));
    const strength = 1 - Math.min(1, correlation);

    return (
        <div style={{ ...glassPanel, padding: 14, ...style }}>
            <div style={{ color: '#C792EA', fontSize: 11, fontWeight: 'bold', marginBottom: 8, letterSpacing: '0.1em' }}>
                ⚛️ ENTANGLEMENT
            </div>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20 }}>
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 12, color: NEXUS_GREEN }}>D1</div>
                    <div style={{ fontSize: 16, fontFamily: 'monospace', color: 'white' }}>{(d1 ?? 0).toFixed(2)}</div>
                </div>
                <div style={{
                    width: 60,
                    height: 4,
                    background: `linear-gradient(90deg, ${NEXUS_GREEN}, #C792EA)`,
                    borderRadius: 2,
                    boxShadow: `0 0 ${10 + strength * 20}px #C792EA`,
                }} />
                <div style={{ textAlign: 'center' }}>
                    <div style={{ fontSize: 12, color: '#C792EA' }}>D12</div>
                    <div style={{ fontSize: 16, fontFamily: 'monospace', color: 'white' }}>{(d12 ?? 0).toFixed(2)}</div>
                </div>
            </div>
            <div style={{ textAlign: 'center', marginTop: 8, fontSize: 10, color: 'rgba(255,255,255,0.5)' }}>
                Holographic Link: r = 0.8
            </div>
        </div>
    );
}

// ═══════════════════════════════════════════════════════════════════
// CUSTOM HOOKS
// ═══════════════════════════════════════════════════════════════════

function useOuroboros() {
    const [telemetry, setTelemetry] = useState<any>(null);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        let ws: WebSocket;
        const connect = () => {
            ws = new WebSocket('ws://localhost:8765');
            ws.onopen = () => {
                console.log('🐍 Connected to Ouroboros');
                setConnected(true);
            };
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                setTelemetry(data);
            };
            ws.onclose = () => {
                console.log('💀 Disconnected from Ouroboros');
                setConnected(false);
                setTimeout(connect, 5000); // Reconnect after 5s
            };
            ws.onerror = (_err) => {
                ws.close();
            };
        };
        connect();
        return () => ws?.close();
    }, []);

    return { telemetry, connected };
}

// ═══════════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════════

const SplashScreen = ({ onStart }: { onStart: () => void }) => (
    <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        background: 'url(/assets/nano_banana_unified.png) center/cover no-repeat',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 1000,
        color: '#FFFFFF'
    }}>
        <h1 style={{
            fontSize: '4rem',
            textShadow: '0 0 20px #FF00FF',
            fontFamily: 'Orbitron, monospace',
            marginBottom: '2rem'
        }}>
            COHEZION
        </h1>
        <div style={{
            padding: '1rem 2rem',
            background: 'rgba(0,0,0,0.7)',
            border: '2px solid #00FFFF',
            borderRadius: '12px',
            backdropFilter: 'blur(10px)',
            cursor: 'pointer',
            fontSize: '1.2rem',
            textTransform: 'uppercase',
            letterSpacing: '2px',
            transition: 'all 0.3s ease'
        }} onClick={onStart}
            onMouseOver={e => e.currentTarget.style.background = 'rgba(0,255,255,0.2)'}
            onMouseOut={e => e.currentTarget.style.background = 'rgba(0,0,0,0.7)'}
        >
            Enter Manifold
        </div>
    </div>
);

export default function App() {
    const [started, setStarted] = useState(false);
    // Live State
    const { telemetry, connected: isOuroborosConnected } = useOuroboros();
    // APP STATE
    const [tourComplete, setTourComplete] = useState(false); // Controls Guided Tour
    const [isLive, setIsLive] = useState(false);

    // Journey data
    const [journey, setJourney] = useState<{ steps: JourneyStep[]; milestones: Milestone[] }>({ steps: [], milestones: [] });

    // Playback state
    const [currentStep, setCurrentStep] = useState(0);
    const [playing, setPlaying] = useState(false);
    const [speed, setSpeed] = useState(1);
    const [projection, setProjection] = useState<ProjectionPreset>(PROJECTION_PRESETS[0]);

    // Engagement State
    const [showExperienceLoader, setShowExperienceLoader] = useState(true);
    const [_tourMode, setTourMode] = useState<null | number>(null); // null, 0 (30s), 1 (60s), 2 (120s)
    const [ambientMode, setAmbientMode] = useState(false);

    // Trail history
    const [trailHistory, setTrailHistory] = useState<[number, number, number][]>([]);

    // Previous milestones for celebration detection
    const lastMilestoneRef = useRef<Milestone | null>(null);

    // Initialize journey
    useEffect(() => {
        const { steps, milestones } = generateJourney(100);
        setJourney({ steps, milestones });
    }, []);

    // Playback loop
    useEffect(() => {
        if (!playing || journey.steps.length === 0) return;

        const baseInterval = 1000 / speed;
        const interval = setInterval(() => {
            setCurrentStep(prev => {
                if (prev >= journey.steps.length - 1) {
                    if (ambientMode) return 0; // Loop in ambient mode
                    setPlaying(false);
                    return prev;
                }
                return prev + 1;
            });
        }, baseInterval);

        return () => clearInterval(interval);
    }, [playing, speed, journey.steps.length, ambientMode]);

    // Update trail and check milestones
    useEffect(() => {
        if (journey.steps.length === 0) return;

        const step = journey.steps[currentStep];
        if (!step) return;

        // Update trail
        const s = step.state12d;
        const pos: [number, number, number] = [s[projection.xDim] * 2, s[projection.yDim] * 2, s[projection.zDim] * 2];
        setTrailHistory(prev => [...prev.slice(-49), pos]);

        // Check for milestone celebrations
        const currentMilestone = journey.milestones.find(m => m.step === currentStep);
        if (currentMilestone && currentMilestone !== lastMilestoneRef.current) {
            audioEngine.init();
            audioEngine.playMilestone(currentMilestone.type);
            lastMilestoneRef.current = currentMilestone;
        }
    }, [currentStep, journey, projection]);

    // Handle audio and narration on step change
    useEffect(() => {
        if (journey.steps.length === 0) return;
        const step = journey.steps[currentStep];
        if (step && playing) {
            audioEngine.init();

            // Sonification
            audioEngine.playCoherenceChord(step.coherentDims);

            // Narration logic
            const milestone = journey.milestones.find(m => m.step === step.step);
            if (milestone) {
                audioEngine.playMilestone(milestone.type);

                // Orchestrate voice personalities
                let voice = 'Alba';
                if (milestone.type === 'first_hiho') voice = 'Javert'; // Authority check
                if (milestone.type === 'half_coherence') voice = 'Jean'; // Oracle insight
                if (milestone.type === 'full_coherence') voice = 'Cosette'; // Celebration

                audioEngine.speak(step.narration, voice);
            }
        }
    }, [currentStep, playing, journey.steps.length, journey.milestones]);

    const liveStep: JourneyStep | null = useMemo(() => {
        if (!isLive || !telemetry) return null;
        const s = new Array(12).fill(0);
        // Map telemetry to 12D state
        s[0] = telemetry.stability || 0;
        s[1] = telemetry.entropy || 0;
        s[2] = telemetry.novelty || 0;
        s[3] = telemetry.dilation || 1.0;
        s[4] = telemetry.coherence || 0;
        s[5] = telemetry.entropy || 0;
        s[6] = telemetry.novelty || 0;
        s[7] = telemetry.momentum || 0;
        s[8] = telemetry.density || 0;
        s[9] = telemetry.resonance || 0;
        s[10] = telemetry.novelty || 0;
        s[11] = telemetry.stability || 0;

        const coherentCount = s.filter(d => Math.abs(d - HIHO) < HIHO_TOLERANCE).length;

        return {
            step: -1,
            state12d: s,
            projected3d: [s[0] * 2, s[1] * 2, s[2] * 2],
            coherentDims: coherentCount,
            pattern: 'emergent' as any,
            narration: `Pulse detected: Stability ${telemetry.stability?.toFixed(2) || '0.00'} | Coherence ${telemetry.coherence?.toFixed(2) || '0.00'}`,
        };
    }, [isLive, telemetry]);

    const currentStepData = isLive && liveStep ? liveStep : (journey.steps[currentStep] || {
        step: 0,
        state12d: new Array(12).fill(0),
        projected3d: [0, 0, 0] as [number, number, number],
        coherentDims: 0,
        pattern: 'regenerative' as const,
        narration: 'Loading journey...',
    });

    // RENDER: SPLASH SCREEN
    if (!started) {
        return <NanoBananaSplash onStart={() => setStarted(true)} />;
    }

    return (
        <div style={{
            width: '100vw',
            height: '100vh',
            background: `radial-gradient(ellipse at center, #0a0a1a 0%, #050510 50%, #000005 100%)`,
            position: 'relative',
            overflow: 'hidden',
            fontFamily: "'Inter', 'Roboto', sans-serif",
            color: 'white',
        }}>
            {/* GUIDED TOUR OVERLAY */}
            {!tourComplete && (
                <GuidedJourney
                    onComplete={() => setTourComplete(true)}
                    onSpeak={(text) => {
                        audioEngine.init();
                        audioEngine.speak(text, 'Alba'); // Use default/gentle voice
                    }}
                />
            )}
            {/* Experience Loader / One-Button Launcher */}
            {showExperienceLoader && (
                <div style={{
                    position: 'absolute',
                    inset: 0,
                    zIndex: 2000,
                    background: MATTE_BLACK,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    textAlign: 'center',
                }}>
                    <img src={logo} alt="COHEZION" style={{ width: 120, height: 120, marginBottom: 40, filter: `drop-shadow(0 0 20px ${NEXUS_GREEN})` }} />
                    <h2 style={{ color: NEXUS_GREEN, fontSize: 32, letterSpacing: '0.2em', margin: 0 }}>COHEZION</h2>
                    <p style={{ color: NEXUS_CYAN, margin: '10px 0 40px', fontSize: 14 }}>UNIVERSAL EXPERIENCE • V1.0</p>
                    <button
                        onClick={() => {
                            audioEngine.init();
                            setShowExperienceLoader(false);
                            setPlaying(true);
                        }}
                        style={{
                            background: 'transparent',
                            border: `2px solid ${NEXUS_GREEN}`,
                            color: NEXUS_GREEN,
                            padding: '16px 40px',
                            fontSize: 18,
                            borderRadius: 40,
                            cursor: 'pointer',
                            boxShadow: `0 0 30px ${NEXUS_GREEN}44`,
                            transition: 'all 0.3s',
                            letterSpacing: '0.1em',
                        }}
                        onMouseEnter={(e) => {
                            e.currentTarget.style.background = NEXUS_GREEN;
                            e.currentTarget.style.color = MATTE_BLACK;
                        }}
                        onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'transparent';
                            e.currentTarget.style.color = NEXUS_GREEN;
                        }}
                    >
                        ✨ START THE EXPERIENCE
                    </button>
                    <p style={{ marginTop: 20, fontSize: 10, color: 'rgba(255,255,255,0.3)', letterSpacing: '0.1em' }}>
                        POWERED BY QUADRATURE NEXUS • HIHO STABILITY PROTOCOL
                    </p>
                </div>
            )}

            <Canvas camera={{ position: [5, 5, 5], fov: 45 }}>
                <HolographicScene
                    currentStep={currentStepData}
                    trailPositions={trailHistory}
                    projection={projection}
                />
            </Canvas>

            <HeaderBar
                journey={journey}
                currentStep={currentStep}
                isLive={isLive}
                setIsLive={setIsLive}
                connected={isOuroborosConnected}
            />

            <div style={{ position: 'absolute', right: 20, top: 100, width: 260, display: 'flex', flexDirection: 'column', gap: 20, zIndex: 100 }}>
                {/* BBQ Mission Status */}
                <div style={{
                    ...glassPanel,
                    padding: '12px 16px',
                    borderLeft: `3px solid ${(telemetry as any)?.bbq_active ? '#00FF00' : '#444'}`,
                    opacity: (telemetry as any)?.bbq_active ? 1 : 0.6,
                    transition: 'all 0.5s ease'
                }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontSize: 10, color: (telemetry as any)?.bbq_active ? '#00FF00' : '#888', letterSpacing: '0.1em' }}>AUTONOMOUS MISSION</span>
                        <div style={{
                            width: 6, height: 6, borderRadius: '50%',
                            background: (telemetry as any)?.bbq_active ? '#00FF00' : '#444',
                            boxShadow: (telemetry as any)?.bbq_active ? '0 0 8px #00FF00' : 'none',
                            animation: (telemetry as any)?.bbq_active ? 'pulse 2s infinite' : 'none'
                        }} />
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'white' }}>{(telemetry as any)?.bbq_active ? 'Active: Low & Slow' : 'Mission Offline'}</div>
                    <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>Target: 50,000,000 Rounds</div>
                </div>

                <StateCard12D state12d={currentStepData.state12d} />
                <EntanglementPulse d1={currentStepData.state12d[0]} d12={currentStepData.state12d[11]} />
                <MilestonePanel milestones={journey.milestones} currentStep={currentStep} />
            </div>

            <div style={{ position: 'absolute', left: 20, bottom: 20, width: 340, display: 'flex', flexDirection: 'column', gap: 20, zIndex: 100 }}>
                <NarrationBox narration={currentStepData.narration} />
                <div style={{ display: 'flex', gap: 10 }}>
                    <div style={{ ...glassPanel, padding: 12, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                        <span style={{ fontSize: 10, color: NEXUS_ORANGE }}>AMBIENT</span>
                        <button
                            onClick={() => setAmbientMode(!ambientMode)}
                            style={{
                                width: 40,
                                height: 20,
                                borderRadius: 10,
                                background: ambientMode ? NEXUS_GREEN : 'rgba(255,255,255,0.1)',
                                border: 'none',
                                cursor: 'pointer',
                                position: 'relative',
                                display: 'flex',
                                alignItems: 'center'
                            }}
                        >
                            <div style={{
                                width: 16,
                                height: 16,
                                borderRadius: '50%',
                                background: 'white',
                                transition: 'transform 0.2s',
                                transform: `translateX(${ambientMode ? 22 : 2}px)`
                            }} />
                        </button>
                    </div>
                    <div style={{ ...glassPanel, padding: 12, flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
                        <span style={{ fontSize: 10, color: NEXUS_CYAN }}>TOUR</span>
                        <select
                            onChange={(e) => {
                                const val = e.target.value === 'off' ? null : parseInt(e.target.value);
                                setTourMode(val);
                                if (val !== null) {
                                    setPlaying(true);
                                    setSpeed(val === 0 ? 2 : val === 1 ? 1 : 0.5);
                                }
                            }}
                            style={{ background: 'transparent', color: 'white', border: 'none', fontSize: 11, outline: 'none' }}
                        >
                            <option value="off">Manual</option>
                            <option value="0">Fast (30s)</option>
                            <option value="1">Deep (60s)</option>
                            <option value="2">Cosmic (120s)</option>
                        </select>
                    </div>
                </div>
                <PlaybackControls
                    step={currentStep}
                    totalSteps={journey.steps.length}
                    playing={playing}
                    speed={speed}
                    onStep={setCurrentStep}
                    onPlay={() => { audioEngine.init(); setPlaying(true); }}
                    onPause={() => setPlaying(false)}
                    onSpeedChange={setSpeed}
                />
            </div>

            <div style={{ position: 'absolute', right: 20, bottom: 20, width: 260, zIndex: 100 }}>
                <ProjectionSelector
                    projection={projection}
                    onProjectionChange={(p) => {
                        setProjection(p);
                        setTrailHistory([]); // Clear trail on projection jump
                    }}
                />
            </div>
        </div>
    );
}
