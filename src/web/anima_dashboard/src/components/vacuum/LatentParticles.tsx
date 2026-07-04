'use client';

/**
 * LatentParticles — 50k particle thought field.
 *
 * Particle positions driven by FLUME 12D latent dims:
 *   x = mean(dims[0:3]), y = mean(dims[3:6]), z = mean(dims[6:12]) as center
 *   + Gaussian noise scaled by (1 - coherenceScore) * disperseRadius
 *
 * HIHO at coherence=0.5 → maximum animation speed (logistic map r=4 onset).
 * At coherence=1 → tight cluster (ordered phase). At 0 → expanded cloud (chaotic).
 */

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const N_PARTICLES = 50_000;
const DEFAULT_DIMS_12D = Array(12).fill(0.0);

interface LatentParticlesProps {
  coherenceScore?: number;
  dims12d?: number[];
}

// Seeded pseudo-random (deterministic across renders)
function seededRng(seed: number) {
  let s = seed;
  return () => {
    s = (s * 1664525 + 1013904223) & 0xffffffff;
    return (s >>> 1) / 0x7fffffff;
  };
}

export function LatentParticles({
  coherenceScore = 0.5,
  dims12d = DEFAULT_DIMS_12D,
}: LatentParticlesProps) {
  const pointsRef = useRef<THREE.Points | null>(null);
  const timeRef = useRef(0);

  // Semantic center from 12D axes
  const center = useMemo((): THREE.Vector3 => {
    const d = dims12d.length >= 12 ? dims12d : DEFAULT_DIMS_12D;
    const cx = (d[0] + d[1] + d[2]) / 3;
    const cy = (d[3] + d[4] + d[5]) / 3;
    const cz = (d[6] + d[7] + d[8] + d[9] + d[10] + d[11]) / 6;
    return new THREE.Vector3(cx, cy, cz);
  }, [dims12d]);

  // Initial positions: Gaussian cloud around center
  const { positions, velocities, sizes } = useMemo(() => {
    const rng = seededRng(42);
    const pos = new Float32Array(N_PARTICLES * 3);
    const vel = new Float32Array(N_PARTICLES * 3);
    const sz = new Float32Array(N_PARTICLES);
    for (let i = 0; i < N_PARTICLES; i++) {
      // Box-Muller Gaussian
      const u1 = Math.max(1e-10, rng());
      const u2 = rng();
      const r = Math.sqrt(-2 * Math.log(u1));
      const gx = r * Math.cos(2 * Math.PI * u2);
      const gy = r * Math.sin(2 * Math.PI * u2);
      const u3 = Math.max(1e-10, rng());
      const u4 = rng();
      const gz = Math.sqrt(-2 * Math.log(u3)) * Math.cos(2 * Math.PI * u4);
      pos[i * 3] = center.x + gx * 0.8;
      pos[i * 3 + 1] = center.y + gy * 0.8;
      pos[i * 3 + 2] = center.z + gz * 0.8;
      // Small random velocity for animation
      vel[i * 3] = (rng() - 0.5) * 0.002;
      vel[i * 3 + 1] = (rng() - 0.5) * 0.002;
      vel[i * 3 + 2] = (rng() - 0.5) * 0.002;
      sz[i] = 0.003 + rng() * 0.008;
    }
    return { positions: pos, velocities: vel, sizes: sz };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center.x, center.y, center.z]);

  const geometry = useMemo(() => {
    const geo = new THREE.BufferGeometry();
    geo.setAttribute('position', new THREE.BufferAttribute(positions.slice(), 3));
    geo.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
    return geo;
  }, [positions, sizes]);

  // Color: warm at high coherence (NPU-converging), cool when dispersed
  const material = useMemo(
    () =>
      new THREE.PointsMaterial({
        size: 0.005,
        sizeAttenuation: true,
        color: new THREE.Color().setHSL(0.6 - coherenceScore * 0.4, 0.8, 0.6),
        transparent: true,
        opacity: 0.5 + coherenceScore * 0.3,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      }),
    [coherenceScore]
  );

  useFrame((_, delta) => {
    timeRef.current += delta;
    if (!pointsRef.current) return;
    const pos = pointsRef.current.geometry.attributes.position
      .array as Float32Array;

    // HIHO animation speed peaks at coherence=0.5 (logistic map resonance)
    const hihoSpeed = 1.0 - Math.abs(coherenceScore - 0.5) * 2.0;
    const speed = (0.3 + hihoSpeed * 1.5) * delta;

    // Dispersion radius: tight cluster at high coherence, expanded at low
    const disperse = (1.0 - coherenceScore) * 0.5;

    for (let i = 0; i < N_PARTICLES; i++) {
      const t = timeRef.current + i * 0.001;
      const ix = i * 3;
      // Drift toward center + Brownian motion
      pos[ix] +=
        (center.x - pos[ix]) * speed * 0.1 +
        velocities[ix] * speed +
        Math.sin(t * 1.1 + i) * disperse * 0.003;
      pos[ix + 1] +=
        (center.y - pos[ix + 1]) * speed * 0.1 +
        velocities[ix + 1] * speed +
        Math.cos(t * 0.9 + i) * disperse * 0.003;
      pos[ix + 2] +=
        (center.z - pos[ix + 2]) * speed * 0.1 +
        velocities[ix + 2] * speed +
        Math.sin(t * 1.3 + i * 0.5) * disperse * 0.002;
    }
    pointsRef.current.geometry.attributes.position.needsUpdate = true;
  });

  return <points ref={pointsRef} geometry={geometry} material={material} />;
}

export default LatentParticles;
