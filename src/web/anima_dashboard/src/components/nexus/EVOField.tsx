import { useMemo } from 'react';
import { Canvas } from '@react-three/fiber';
import * as THREE from 'three';
import { EVOEvent } from '../../hooks/useEVOStream';

// Color mapping for voices
const VOICE_COLORS: Record<string, string> = {
  architect: '#00ffff', // Cyan
  engineer: '#ff8c00',  // Orange
  ethicist: '#ee82ee',  // Violet
  resource: '#00ff00',  // Green
  unknown: '#ffffff',   // White
};

const DEFAULT_COLOR = '#ffffff';

/**
 * Build a Three.js BufferGeometry whose position attribute carries the EVO
 * points projected from the 256D z-vector onto [-3, 3]^3. We construct the
 * geometry imperatively (rather than via R3F's JSX `<bufferAttribute args=…>`)
 * because the `args` constructor-arg pattern is awkward in TS strict mode and
 * the per-point size attribute needs a custom shader to be honored by WebGL.
 */
function buildPointsGeometry(events: EVOEvent[]): THREE.BufferGeometry {
  const positions = new Float32Array(events.length * 3);
  const colors = new Float32Array(events.length * 3);
  const sizes = new Float32Array(events.length);

  events.forEach((event, i) => {
    // Project z_256[0..2] to (x, y, z) on [-3, 3]. z_256 is in [0, 1]
    // (per the FLUME VAE HIHO band), so we multiply by 6 and offset by 3.
    const x = (event.z_256[0] ?? 0.5) * 6 - 3;
    const y = (event.z_256[1] ?? 0.5) * 6 - 3;
    const z = (event.z_256[2] ?? 0.5) * 6 - 3;

    positions[i * 3] = x;
    positions[i * 3 + 1] = y;
    positions[i * 3 + 2] = z;

    const voiceColor = VOICE_COLORS[event.voice] || DEFAULT_COLOR;
    const color = new THREE.Color(voiceColor);
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;

    // Size = 0.05 + score*0.1 (clamped so score out of [0,1] doesn't blow up)
    sizes[i] = 0.05 + Math.min(1, Math.max(0, event.score)) * 0.1;
  });

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1));
  return geometry;
}

function EVOPointsShader({ events }: { events: EVOEvent[] }) {
  // The shader version: uses an inline shader that honors the per-vertex
  // `size` attribute (which default PointsMaterial does not).
  const geometry = useMemo(() => buildPointsGeometry(events), [events]);

  if (events.length === 0) return null;

  return (
    <points geometry={geometry}>
      <shaderMaterial
        vertexShader={`
          attribute float size;
          varying vec3 vColor;
          void main() {
            vColor = color;
            vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
            gl_PointSize = size * (300.0 / -mvPosition.z);
            gl_Position = projectionMatrix * mvPosition;
          }
        `}
        fragmentShader={`
          varying vec3 vColor;
          void main() {
            // Circular point
            vec2 coord = gl_PointCoord - vec2(0.5);
            if(length(coord) > 0.5) discard;
            gl_FragColor = vec4(vColor, 1.0);
          }
        `}
        vertexColors
        transparent
      />
    </points>
  );
}

export function EVOField({ events }: { events: EVOEvent[] }) {
  return (
    <div style={{ width: '100%', height: '100%', aspectRatio: '1/1', position: 'relative' }}>
      <Canvas
        camera={{ position: [0, 0, 10], fov: 50 }}
        style={{ width: '100%', height: '100%' }}
      >
        <ambientLight intensity={0.5} />
        <EVOPointsShader events={events} />

        {/* HIHO Halo — translucent sphere at the (0.5, 0.5, 0.5) attractor */}
        <mesh position={[0.5, 0.5, 0.5]}>
          <sphereGeometry args={[0.5, 32, 32]} />
          <meshBasicMaterial color="gold" transparent opacity={0.15} />
        </mesh>
      </Canvas>
    </div>
  );
}
