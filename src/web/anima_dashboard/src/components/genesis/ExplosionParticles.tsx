"use client";

import React, { useRef, useMemo, useEffect } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

// --- Constants ---
const PARTICLE_COUNT = 500;
const HIHO_SHELL_RADIUS = 2.0;
const DAMPING = 0.97;
const ATTRACTOR_STRENGTH = 0.3;
const GOLD = new THREE.Color("#ffd700");
const WHITE = new THREE.Color("#ffffff");

// Fabric assignments and colors
const FABRIC_CENTERS = [
  new THREE.Vector3(3, 0, 0),     // Space
  new THREE.Vector3(-2, 2, 0),    // Field
  new THREE.Vector3(0, -2, 2),    // Control
  new THREE.Vector3(-1, -1, -3),  // Precipitation
];

const FABRIC_COLORS = [
  new THREE.Color("#3b82f6"), // Space - blue
  new THREE.Color("#f59e0b"), // Field - orange
  new THREE.Color("#10b981"), // Control - green
  new THREE.Color("#a855f7"), // Precipitation - purple
];

export type ExplosionPhase = "idle" | "exploding" | "settling" | "differentiating" | "final";

interface ExplosionParticlesProps {
  phase: ExplosionPhase;
  /** Seconds since explosion started */
  elapsed: number;
}

interface ParticleData {
  velocity: THREE.Vector3;
  fabricIndex: number;
  baseSize: number;
}

export default function ExplosionParticles({ phase, elapsed }: ExplosionParticlesProps) {
  const meshRef = useRef<THREE.InstancedMesh>(null);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const colorRef = useRef(new THREE.Color());

  // Initialize particle data: random velocities, fabric assignments, sizes
  const particles = useMemo<ParticleData[]>(() => {
    const arr: ParticleData[] = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Random direction (unit sphere), magnitude 3-8
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      const mag = 3 + Math.random() * 5;
      const vx = Math.sin(phi) * Math.cos(theta) * mag;
      const vy = Math.sin(phi) * Math.sin(theta) * mag;
      const vz = Math.cos(phi) * mag;

      // Assign to fabric based on angular position (quadrants in spherical coords)
      const fabricIndex = Math.floor((theta / (Math.PI * 2)) * 4) % 4;

      arr.push({
        velocity: new THREE.Vector3(vx, vy, vz),
        fabricIndex,
        baseSize: 0.01 + Math.random() * 0.01,
      });
    }
    return arr;
  }, []);

  // Current positions stored as flat array for performance
  const positions = useMemo(() => {
    const arr = new Float32Array(PARTICLE_COUNT * 3);
    // All start at origin
    return arr;
  }, []);

  // Track per-particle velocity (mutable copy of initial velocities)
  const velocities = useMemo(() => {
    return particles.map((p) => p.velocity.clone());
  }, [particles]);

  // Reset positions when phase goes from idle to exploding
  const prevPhaseRef = useRef<ExplosionPhase>("idle");
  useEffect(() => {
    if (phase === "exploding" && prevPhaseRef.current === "idle") {
      // Reset all positions to origin, reset velocities
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        positions[i * 3] = 0;
        positions[i * 3 + 1] = 0;
        positions[i * 3 + 2] = 0;
        velocities[i].copy(particles[i].velocity);
      }
    }
    prevPhaseRef.current = phase;
  }, [phase, positions, velocities, particles]);

  useFrame((_, delta) => {
    if (!meshRef.current || phase === "idle") return;
    const dt = Math.min(delta, 0.05); // Clamp to avoid explosion on tab-switch

    const tmpPos = new THREE.Vector3();
    const tmpTarget = new THREE.Vector3();

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const ix = i * 3;
      const iy = ix + 1;
      const iz = ix + 2;
      const vel = velocities[i];
      const pData = particles[i];

      tmpPos.set(positions[ix], positions[iy], positions[iz]);

      if (phase === "exploding") {
        // Phase 1: burst outward, damping + HIHO attractor toward shell
        vel.multiplyScalar(DAMPING);

        // Attractor toward SO(12) shell
        const dist = tmpPos.length();
        if (dist > 0.001) {
          const attractDir = tmpPos.clone().normalize();
          const shellDelta = HIHO_SHELL_RADIUS - dist;
          vel.addScaledVector(attractDir, shellDelta * ATTRACTOR_STRENGTH * dt * 60);
        }
      } else if (phase === "differentiating") {
        // Phase 2: pull toward fabric center
        vel.multiplyScalar(0.95);
        const center = FABRIC_CENTERS[pData.fabricIndex];
        tmpTarget.copy(center).sub(tmpPos);
        vel.addScaledVector(tmpTarget, 0.8 * dt);
      } else if (phase === "settling" || phase === "final") {
        // Phase 3-4: orbit around fabric center
        vel.multiplyScalar(0.93);
        const center = FABRIC_CENTERS[pData.fabricIndex];
        tmpTarget.copy(center).sub(tmpPos);
        const toCenterDist = tmpTarget.length();

        // Pull toward center with orbit
        vel.addScaledVector(tmpTarget, 1.2 * dt);

        // Tangential orbit force (cross product for circular motion)
        if (toCenterDist > 0.1) {
          const tangent = new THREE.Vector3()
            .crossVectors(tmpTarget.normalize(), new THREE.Vector3(0, 1, 0))
            .normalize();
          vel.addScaledVector(tangent, 0.5 * dt);
        }
      }

      // Integrate position
      positions[ix] += vel.x * dt;
      positions[iy] += vel.y * dt;
      positions[iz] += vel.z * dt;

      // Compute color based on phase
      if (phase === "exploding") {
        // White -> gold over 2 seconds
        const colorT = Math.min(elapsed / 2.0, 1.0);
        colorRef.current.copy(WHITE).lerp(GOLD, colorT);
      } else if (phase === "differentiating") {
        // Gold -> fabric color over 3 seconds (elapsed from differentiation start)
        const diffElapsed = elapsed - 2.0;
        const colorT = Math.min(diffElapsed / 3.0, 1.0);
        colorRef.current.copy(GOLD).lerp(FABRIC_COLORS[pData.fabricIndex], colorT);
      } else {
        // Full fabric color
        colorRef.current.copy(FABRIC_COLORS[pData.fabricIndex]);
      }

      // Update instance matrix
      dummy.position.set(positions[ix], positions[iy], positions[iz]);
      dummy.scale.setScalar(pData.baseSize);
      dummy.updateMatrix();
      meshRef.current.setMatrixAt(i, dummy.matrix);
      meshRef.current.setColorAt(i, colorRef.current);
    }

    meshRef.current.instanceMatrix.needsUpdate = true;
    if (meshRef.current.instanceColor) {
      meshRef.current.instanceColor.needsUpdate = true;
    }
  });

  if (phase === "idle") return null;

  return (
    <instancedMesh ref={meshRef} args={[undefined, undefined, PARTICLE_COUNT]}>
      <sphereGeometry args={[1, 8, 8]} />
      <meshBasicMaterial toneMapped={false} />
    </instancedMesh>
  );
}
