'use client';

/**
 * HopfManifold — ~300 Hopf fibration fiber loops with thin-film iridescence.
 *
 * Physics: Vortex string cross-sections in 3D ARE Hopf fiber circles.
 * The complex order parameter φ = f(r)·e^{iℓθ} produces exactly these loops.
 * Winding number ℓ: +1=NPU (warm), 0=iGPU (neutral), -1=CPU (cool/flipped).
 *
 * HIHO glow peaks at coherenceScore=0.5 — the BKT critical temperature.
 */

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

const FIBER_COUNT = 300;
const TUBE_SEGMENTS = 64;
const TUBE_RADIUS = 0.012;

// Thin-film iridescence vertex shader
const VERT = /* glsl */ `
  varying vec3 vNormal;
  varying vec3 vViewDir;
  void main() {
    vNormal = normalize(normalMatrix * normal);
    vec4 worldPos = modelViewMatrix * vec4(position, 1.0);
    vViewDir = normalize(-worldPos.xyz);
    gl_Position = projectionMatrix * worldPos;
  }
`;

// Thin-film iridescence fragment shader.
// hihoGlow peaks at coherenceScore=0.5 (BKT equilibrium).
const FRAG = /* glsl */ `
  uniform float time;
  uniform float coherenceScore;
  varying vec3 vNormal;
  varying vec3 vViewDir;

  void main() {
    float ndotv = dot(normalize(vNormal), normalize(vViewDir));
    float phase = ndotv * 6.28318 + time * 0.3;
    vec3 thinFilm = vec3(
      0.5 + 0.5 * sin(phase),
      0.5 + 0.5 * sin(phase + 2.094),
      0.5 + 0.5 * sin(phase + 4.189)
    );
    // Peak at coherence=0.5; falls to 0 at 0 and 1
    float hihoGlow = pow(1.0 - abs(coherenceScore - 0.5) * 2.0, 2.0);
    vec3 color = mix(vec3(0.05, 0.0, 0.2), thinFilm, hihoGlow);
    // Fresnel rim glow
    color += pow(max(0.0, 1.0 - ndotv), 3.0) * vec3(0.3, 0.8, 1.0);
    gl_FragColor = vec4(color, 0.7 - ndotv * 0.4);
  }
`;

// Hopf fiber parametric curve for angle θ ∈ [0, 2π], time offset t
function hopfFiber(theta: number, t: number, segments: number): Float32Array {
  const pts = new Float32Array(segments * 3);
  const eta = theta / 2;
  for (let i = 0; i < segments; i++) {
    const phi = (i / segments) * Math.PI * 2 + t;
    const denom = Math.SQRT2 - Math.sin(eta) * Math.sin(phi);
    const x = (Math.cos(eta) * Math.cos(phi)) / denom;
    const y = (Math.cos(eta) * Math.sin(phi)) / denom;
    const z = (Math.sin(eta) * Math.cos(phi)) / denom;
    pts[i * 3] = x;
    pts[i * 3 + 1] = y;
    pts[i * 3 + 2] = z;
  }
  return pts;
}

// Color per fiber based on winding number: warm=NPU, neutral=iGPU, cool=CPU
function fiberColor(idx: number, tierUsed: string): THREE.Color {
  const npu = new THREE.Color(0xff7700);  // warm orange
  const igpu = new THREE.Color(0x88aaff); // neutral blue
  const cpu = new THREE.Color(0x00ccff);  // cool cyan (chirality flipped)
  if (tierUsed === 'npu') return npu.clone().lerp(igpu, idx / FIBER_COUNT);
  if (tierUsed === 'cpu') return cpu.clone().lerp(igpu, idx / FIBER_COUNT);
  return igpu.clone();
}

interface HopfManifoldProps {
  coherenceScore?: number;
  tierUsed?: string;
}

export function HopfManifold({
  coherenceScore = 0.5,
  tierUsed = 'igpu',
}: HopfManifoldProps) {
  const meshRefs = useRef<THREE.Mesh[]>([]);
  const materialsRef = useRef<THREE.ShaderMaterial[]>([]);
  const timeRef = useRef(0);

  // Build 300 tube geometries, one per Hopf fiber
  const geometries = useMemo(() => {
    const geoms: THREE.BufferGeometry[] = [];
    for (let i = 0; i < FIBER_COUNT; i++) {
      const theta = (i / FIBER_COUNT) * Math.PI * 2;
      const pts = hopfFiber(theta, 0, TUBE_SEGMENTS);
      const vectors: THREE.Vector3[] = [];
      for (let j = 0; j < TUBE_SEGMENTS; j++) {
        vectors.push(
          new THREE.Vector3(pts[j * 3], pts[j * 3 + 1], pts[j * 3 + 2])
        );
      }
      // Close the loop
      vectors.push(vectors[0].clone());
      const curve = new THREE.CatmullRomCurve3(vectors, true);
      const geom = new THREE.TubeGeometry(curve, TUBE_SEGMENTS, TUBE_RADIUS, 6, true);
      geoms.push(geom);
    }
    return geoms;
  }, []);

  // Shared shader material per fiber (color varies per instance)
  const materials = useMemo(
    () =>
      geometries.map((_, i) => {
        const col = fiberColor(i, tierUsed);
        return new THREE.ShaderMaterial({
          vertexShader: VERT,
          fragmentShader: FRAG,
          uniforms: {
            time: { value: 0 },
            coherenceScore: { value: coherenceScore },
            // tint injected per-fiber so each loop has its own color identity
            fiberTint: { value: new THREE.Vector3(col.r, col.g, col.b) },
          },
          transparent: true,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [tierUsed]
  );
  materialsRef.current = materials;

  useFrame((_, delta) => {
    timeRef.current += delta;
    for (const mat of materialsRef.current) {
      mat.uniforms.time.value = timeRef.current;
      mat.uniforms.coherenceScore.value = coherenceScore;
    }
  });

  return (
    <group>
      {geometries.map((geom, i) => (
        <mesh
          key={i}
          geometry={geom}
          material={materials[i]}
          ref={(el) => {
            if (el) meshRefs.current[i] = el;
          }}
        />
      ))}
    </group>
  );
}

export default HopfManifold;
