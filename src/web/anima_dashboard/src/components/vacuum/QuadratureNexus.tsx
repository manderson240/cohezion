'use client';

/**
 * QuadratureNexus — IQ phase space visualization.
 *
 * Shows the Nexus I/Q as a saddle surface z = I² - Q², with:
 * - Einstein ring (TorusGeometry) marking the HIHO equilibrium orbit
 * - Gravitational lens warp at the nexus center (vertex distortion)
 * - Emissive sphere at HIHO equilibrium point (I=0.5, Q=0.5)
 *
 * nexusPower drives glow intensity: maximum at HIHO (I=Q=0.5, power=1).
 */

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const SADDLE_VERTS = /* glsl */ `
  uniform float nexusPower;
  uniform float time;
  varying vec2 vUV;
  varying float vHeight;

  void main() {
    vUV = uv;
    vec3 pos = position;
    // Saddle: z = I^2 - Q^2 where I=(x+1)/2, Q=(y+1)/2
    float I = (pos.x + 1.0) * 0.5;
    float Q = (pos.y + 1.0) * 0.5;
    float saddle = (I - 0.5) * (I - 0.5) - (Q - 0.5) * (Q - 0.5);
    // Gravitational lens warp: pull geometry toward center by nexusPower
    float r = length(pos.xy);
    float warp = nexusPower * 0.15 * exp(-r * 2.0) * sin(time * 1.2);
    pos.z = saddle * 0.8 + warp;
    vHeight = saddle;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
  }
`;

const SADDLE_FRAG = /* glsl */ `
  uniform float nexusPower;
  uniform float time;
  varying vec2 vUV;
  varying float vHeight;

  void main() {
    // Color: blue-violet toward HIHO center, orange at saddle extremes
    float d = length(vUV - 0.5);
    vec3 center = vec3(0.2, 0.4, 1.0);
    vec3 edge = vec3(1.0, 0.5, 0.1);
    vec3 col = mix(center, edge, d * 2.0);
    // Glow pulse at HIHO power
    float pulse = nexusPower * 0.4 * (0.5 + 0.5 * sin(time * 2.0));
    col += vec3(pulse * 0.3, pulse * 0.5, pulse);
    float alpha = 0.6 + 0.3 * nexusPower - abs(vHeight) * 0.2;
    gl_FragColor = vec4(col, clamp(alpha, 0.2, 0.9));
  }
`;

interface QuadratureNexusProps {
  nexusI?: number;
  nexusQ?: number;
  nexusPower?: number;
}

export function QuadratureNexus({
  nexusI = 0.5,
  nexusQ = 0.5,
  nexusPower = 1.0,
}: QuadratureNexusProps) {
  const matRef = useRef<THREE.ShaderMaterial | null>(null);
  const ringRef = useRef<THREE.Mesh | null>(null);
  const timeRef = useRef(0);

  const saddle = useMemo(() => {
    const geo = new THREE.PlaneGeometry(2.0, 2.0, 32, 32);
    return geo;
  }, []);

  const saddleMat = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: SADDLE_VERTS,
        fragmentShader: SADDLE_FRAG,
        uniforms: {
          nexusPower: { value: nexusPower },
          time: { value: 0 },
        },
        transparent: true,
        side: THREE.DoubleSide,
        depthWrite: false,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );
  matRef.current = saddleMat;

  // Einstein ring — torus at HIHO equilibrium radius
  const ringGeo = useMemo(() => new THREE.TorusGeometry(0.5, 0.02, 16, 128), []);
  const ringMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: new THREE.Color(0x88ffcc),
        emissive: new THREE.Color(0x44ffaa),
        emissiveIntensity: nexusPower * 2.0,
        transparent: true,
        opacity: 0.7 + 0.3 * nexusPower,
      }),
    [nexusPower]
  );

  // HIHO equilibrium marker
  const eqGeo = useMemo(() => new THREE.SphereGeometry(0.04, 16, 16), []);
  const eqMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: new THREE.Color(0xffffff),
        emissive: new THREE.Color(0xffffff),
        emissiveIntensity: nexusPower * 3.0,
      }),
    [nexusPower]
  );

  // Indicator sphere at current (I, Q) position
  const indicatorGeo = useMemo(
    () => new THREE.SphereGeometry(0.06, 16, 16),
    []
  );
  const indicatorMat = useMemo(
    () =>
      new THREE.MeshStandardMaterial({
        color: new THREE.Color(0xff6600),
        emissive: new THREE.Color(0xff3300),
        emissiveIntensity: 1.5,
      }),
    []
  );

  // Map I,Q from [0,1] to saddle space [-1,1]
  const indicatorPos: [number, number, number] = [
    (nexusI - 0.5) * 2.0,
    (nexusQ - 0.5) * 2.0,
    0.15,
  ];

  useFrame((_, delta) => {
    timeRef.current += delta;
    if (matRef.current) {
      matRef.current.uniforms.time.value = timeRef.current;
      matRef.current.uniforms.nexusPower.value = nexusPower;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z = timeRef.current * 0.3;
    }
  });

  return (
    <group>
      {/* Saddle surface — IQ phase space */}
      <mesh geometry={saddle} material={saddleMat} rotation={[-Math.PI / 2, 0, 0]} />

      {/* Einstein ring at HIHO equilibrium orbit */}
      <mesh
        ref={ringRef}
        geometry={ringGeo}
        material={ringMat}
        rotation={[Math.PI / 2, 0, 0]}
      />

      {/* HIHO equilibrium point (0.5, 0.5) */}
      <mesh geometry={eqGeo} material={eqMat} position={[0, 0, 0.1]} />

      {/* Current nexus position indicator */}
      <mesh geometry={indicatorGeo} material={indicatorMat} position={indicatorPos} />

      {/* Ambient glow light at nexus center */}
      <pointLight
        position={[0, 0, 0.5]}
        intensity={nexusPower * 2.0}
        color={0x88ffcc}
        distance={3}
      />
    </group>
  );
}

export default QuadratureNexus;
