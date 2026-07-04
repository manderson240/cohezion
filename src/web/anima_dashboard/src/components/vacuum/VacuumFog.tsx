'use client';

/**
 * VacuumFog — Raymarched volumetric fog from the 16³ vacuum field.
 *
 * The vacuum_field is a 16×16×16 density volume (4096 floats) uploaded
 * as a THREE.Data3DTexture. Raymarching (48 steps) samples the texture
 * along the view ray to produce volumetric attractor basin visualization.
 *
 * RDNA 3.5 safe: 48 steps at 50% pixel ratio + edge-preserving upscale.
 * mhdRipplePhase drives standing wave interference pattern.
 */

import { useRef, useMemo, useEffect } from 'react';
import { useFrame, useThree } from '@react-three/fiber';
import * as THREE from 'three';

const N = 16;

const FOG_VERT = /* glsl */ `
  varying vec3 vRayDir;
  varying vec3 vWorldPos;

  void main() {
    vec4 world = modelMatrix * vec4(position, 1.0);
    vWorldPos = world.xyz;
    vRayDir = world.xyz - cameraPosition;
    gl_Position = projectionMatrix * viewMatrix * world;
  }
`;

const FOG_FRAG = /* glsl */ `
  uniform sampler3D densityField;
  uniform float mhdRipplePhase;
  uniform float time;
  varying vec3 vRayDir;
  varying vec3 vWorldPos;

  #define STEPS 48
  #define STEP_SIZE (1.7321 / float(STEPS))  // sqrt(3) / steps

  void main() {
    vec3 rayDir = normalize(vRayDir);
    vec3 pos = vWorldPos * 0.5 + 0.5;  // map [-1,1] cube to [0,1] UVW
    float accum = 0.0;
    vec3 color = vec3(0.0);

    for (int i = 0; i < STEPS; i++) {
      if (pos.x < 0.0 || pos.x > 1.0 ||
          pos.y < 0.0 || pos.y > 1.0 ||
          pos.z < 0.0 || pos.z > 1.0) break;

      float density = texture(densityField, pos).r;
      // MHD standing wave modulation
      float mhd = 0.5 + 0.5 * sin(
        pos.x * 6.283 + mhdRipplePhase +
        pos.y * 3.14 * cos(time * 0.5)
      );
      density *= (0.7 + 0.3 * mhd);

      if (density > 0.01) {
        float step_alpha = 1.0 - exp(-density * STEP_SIZE * 8.0);
        // Color: deep violet in attractor basins, teal in free field
        vec3 stepColor = mix(
          vec3(0.2, 0.0, 0.8),   // attractor: deep violet
          vec3(0.0, 0.8, 0.6),   // free field: teal
          1.0 - density
        );
        color += stepColor * step_alpha * (1.0 - accum);
        accum += step_alpha * (1.0 - accum);
      }
      pos += rayDir * STEP_SIZE * 0.5;
      if (accum > 0.95) break;
    }

    gl_FragColor = vec4(color, accum * 0.7);
  }
`;

interface VacuumFogProps {
  vacuumField?: number[] | Float32Array;
  mhdRipplePhase?: number;
}

export function VacuumFog({
  vacuumField,
  mhdRipplePhase = 0.0,
}: VacuumFogProps) {
  const matRef = useRef<THREE.ShaderMaterial | null>(null);
  const timeRef = useRef(0);
  useThree(); // Ensures Three.js renderer context is available

  // Build Data3DTexture from density field (16^3 = 4096 values)
  const texture3D = useMemo(() => {
    const data = new Uint8Array(N * N * N);
    const field = vacuumField ?? [];
    for (let i = 0; i < N * N * N; i++) {
      // Default: Gaussian attractor at center
      if (i < field.length) {
        data[i] = Math.round(Math.min(1.0, field[i]) * 255);
      } else {
        const x = (i % N) / N - 0.5;
        const y = (Math.floor(i / N) % N) / N - 0.5;
        const z = Math.floor(i / (N * N)) / N - 0.5;
        const r2 = x * x + y * y + z * z;
        data[i] = Math.round(Math.exp(-r2 * 8) * 200);
      }
    }
    const tex = new THREE.Data3DTexture(data, N, N, N);
    tex.format = THREE.RedFormat;
    tex.type = THREE.UnsignedByteType;
    tex.minFilter = THREE.LinearFilter;
    tex.magFilter = THREE.LinearFilter;
    tex.unpackAlignment = 1;
    tex.needsUpdate = true;
    return tex;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update texture when vacuumField changes
  useEffect(() => {
    if (!vacuumField || !texture3D) return;
    const data = texture3D.image.data as Uint8Array;
    for (let i = 0; i < Math.min(vacuumField.length, N * N * N); i++) {
      data[i] = Math.round(Math.min(1.0, (vacuumField as number[])[i] ?? 0) * 255);
    }
    texture3D.needsUpdate = true;
  }, [vacuumField, texture3D]);

  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        vertexShader: FOG_VERT,
        fragmentShader: FOG_FRAG,
        uniforms: {
          densityField: { value: texture3D },
          mhdRipplePhase: { value: mhdRipplePhase },
          time: { value: 0 },
        },
        transparent: true,
        side: THREE.BackSide,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
      }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [texture3D]
  );
  matRef.current = material;

  useFrame((_, delta) => {
    timeRef.current += delta;
    if (matRef.current) {
      matRef.current.uniforms.time.value = timeRef.current;
      matRef.current.uniforms.mhdRipplePhase.value = mhdRipplePhase;
    }
  });

  // Large cube — ray entry from BackSide
  const geo = useMemo(() => new THREE.BoxGeometry(3, 3, 3), []);

  return <mesh geometry={geo} material={material} />;
}

export default VacuumFog;
