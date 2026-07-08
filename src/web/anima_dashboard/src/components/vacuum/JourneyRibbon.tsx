'use client';

/**
 * JourneyRibbon — CatmullRom spline through agentic journey VizPoints.
 *
 * Fetches VizFrame from /api/journey-nexus/frame every 2s.
 * Maps VizPoint {pos_x, pos_y, pos_z} to THREE.Vector3 for CatmullRomCurve3.
 * Tube radius and color hue derived from VizPoint physics properties.
 * Glow pulses at VizPoint.rotation_speed * coherence (vortex winding rate).
 */

import { useRef, useState, useEffect, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import * as THREE from 'three';

interface VizPointData {
  pos_x: number;
  pos_y: number;
  pos_z: number;
  color_hue: number;
  color_saturation: number;
  luminosity: number;
  radius: number;
  glow: number;
  alpha: number;
  rotation_speed: number;
  coherence: number;
  tier_used: string;
  winding_number: number;
}

// Stub ribbon when API is unavailable: equilateral triangle in latent space
const STUB_POINTS: VizPointData[] = [
  { pos_x: 0.6, pos_y: 0, pos_z: 0, color_hue: 0.08, color_saturation: 0.9, luminosity: 0.7, radius: 0.05, glow: 0.7, alpha: 0.8, rotation_speed: 1.5, coherence: 0.5, tier_used: 'npu', winding_number: 1 },
  { pos_x: -0.3, pos_y: 0.52, pos_z: 0.1, color_hue: 0.55, color_saturation: 0.8, luminosity: 0.6, radius: 0.04, glow: 0.5, alpha: 0.7, rotation_speed: 0.9, coherence: 0.4, tier_used: 'igpu', winding_number: 0 },
  { pos_x: -0.3, pos_y: -0.52, pos_z: -0.1, color_hue: 0.67, color_saturation: 0.7, luminosity: 0.5, radius: 0.06, glow: 0.4, alpha: 0.75, rotation_speed: 0.6, coherence: 0.3, tier_used: 'cpu', winding_number: -1 },
];

function hslToColor(h: number, s: number, l: number): THREE.Color {
  return new THREE.Color().setHSL(h, s, l);
}

interface JourneyRibbonProps {
  apiBase?: string;
  refreshMs?: number;
}

export function JourneyRibbon({
  apiBase = '/api/journey-nexus',
  refreshMs = 2000,
}: JourneyRibbonProps) {
  const [points, setPoints] = useState<VizPointData[]>(STUB_POINTS);
  const timeRef = useRef(0);
  const groupRef = useRef<THREE.Group | null>(null);

  // Fetch VizFrame from /frame endpoint
  useEffect(() => {
    let mounted = true;
    const fetchFrame = async () => {
      try {
        const resp = await fetch(`${apiBase}/frame`);
        if (resp.ok && mounted) {
          const frame = await resp.json();
          if (frame.points && frame.points.length > 0) {
            setPoints(frame.points);
          }
        }
      } catch {
        // Keep stub data on failure
      }
    };
    fetchFrame();
    const id = setInterval(fetchFrame, refreshMs);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, [apiBase, refreshMs]);

  // Shared unit sphere for node markers — scaled per instance instead of
  // allocating a new SphereGeometry per point per render (that leaked one
  // geometry+material set every poll cycle).
  const unitSphere = useMemo(() => new THREE.SphereGeometry(1, 16, 16), []);
  useEffect(() => () => unitSphere.dispose(), [unitSphere]);

  const nodeMaterials = useMemo(
    () =>
      points.map(
        (pt) =>
          new THREE.MeshStandardMaterial({
            color: hslToColor(pt.color_hue, pt.color_saturation, pt.luminosity),
            emissive: hslToColor(pt.color_hue, pt.color_saturation, pt.luminosity * 0.5),
            emissiveIntensity: pt.glow,
            transparent: true,
            opacity: pt.alpha,
          })
      ),
    [points]
  );
  useEffect(
    () => () => {
      for (const m of nodeMaterials) m.dispose();
    },
    [nodeMaterials]
  );

  // Build tube geometry from current points
  const { geometry, material } = useMemo(() => {
    if (points.length < 2) {
      return { geometry: null, material: null };
    }
    const vectors = points.map(
      (p) => new THREE.Vector3(p.pos_x, p.pos_y, p.pos_z)
    );
    // Close loop if 3+ points
    const closed = vectors.length >= 3;
    const curve = new THREE.CatmullRomCurve3(vectors, closed);
    const avgRadius = points.reduce((s, p) => s + p.radius, 0) / points.length;
    const geom = new THREE.TubeGeometry(curve, 128, avgRadius, 8, closed);

    // Per-vertex color gradient along tube (hue interpolated between first/last)
    const posAttr = geom.attributes.position;
    const colors = new Float32Array(posAttr.count * 3);
    const firstColor = hslToColor(points[0].color_hue, points[0].color_saturation, points[0].luminosity);
    const lastColor = hslToColor(
      points[points.length - 1].color_hue,
      points[points.length - 1].color_saturation,
      points[points.length - 1].luminosity
    );
    const tmp = new THREE.Color();
    for (let i = 0; i < posAttr.count; i++) {
      const t = i / posAttr.count;
      tmp.copy(firstColor).lerp(lastColor, t);
      colors[i * 3] = tmp.r;
      colors[i * 3 + 1] = tmp.g;
      colors[i * 3 + 2] = tmp.b;
    }
    geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));

    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      emissive: new THREE.Color(0x444444),
      emissiveIntensity: 0.5,
      transparent: true,
      opacity: points[0].alpha,
      roughness: 0.3,
      metalness: 0.6,
    });

    return { geometry: geom, material: mat };
  }, [points]);

  // Dispose superseded tube geometry/material (rebuilt each points change)
  useEffect(
    () => () => {
      geometry?.dispose();
      material?.dispose();
    },
    [geometry, material]
  );

  useFrame((_, delta) => {
    timeRef.current += delta;
    if (groupRef.current) {
      // Gentle rotation driven by mean winding number
      const meanWinding = points.reduce((s, p) => s + p.winding_number, 0) / points.length;
      groupRef.current.rotation.y += delta * 0.05 * meanWinding;
    }
    if (material) {
      // Pulse glow based on mean coherence and time
      const meanGlow = points.reduce((s, p) => s + p.glow, 0) / points.length;
      const meanSpeed = points.reduce((s, p) => s + p.rotation_speed, 0) / points.length;
      material.emissiveIntensity =
        meanGlow * (0.5 + 0.5 * Math.sin(timeRef.current * meanSpeed));
    }
  });

  if (!geometry || !material) return null;

  return (
    <group ref={groupRef}>
      <mesh geometry={geometry} material={material} />
      {/* Node spheres at each journey point — shared geometry, scaled */}
      {points.map((pt, i) => (
        <mesh
          key={i}
          position={[pt.pos_x, pt.pos_y, pt.pos_z]}
          scale={pt.radius * 1.5}
          geometry={unitSphere}
          material={nodeMaterials[i]}
        />
      ))}
    </group>
  );
}

export default JourneyRibbon;
