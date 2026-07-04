"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

// Four-fabric color palette (matches GenesisScene FABRIC_COLORS_MAP)
const FABRIC_COLORS: Record<string, THREE.Color> = {
  Space: new THREE.Color("#3b82f6"),
  Field: new THREE.Color("#f59e0b"),
  Control: new THREE.Color("#10b981"),
  Precipitation: new THREE.Color("#a855f7"),
};

interface FabricPrimitive {
  fabric: string;
  x: number;
  y: number;
  z: number;
  scale: number;
}

interface TrajectoryData {
  points_3d: [number, number, number][];
  curvatures: number[];
  predicted_3d: [number, number, number][];
  fabric_primitives: FabricPrimitive[];
  n_points: number;
  n_predicted: number;
  causal_dims: number[];
}

// Lissajous fallback so the component renders even when the API is unavailable
function generateLocalTrajectory(n = 30): TrajectoryData {
  const points_3d: [number, number, number][] = [];
  const curvatures: number[] = [];
  for (let i = 0; i < n; i++) {
    const t = (i / n) * Math.PI * 4;
    points_3d.push([
      Math.sin(t) * 1.5,
      Math.sin(t * 1.3 + 0.5) * 1.2,
      Math.cos(t * 0.7) * 1.0,
    ]);
    curvatures.push(0.3 + 0.4 * Math.abs(Math.sin(t)));
  }
  const predicted_3d: [number, number, number][] = [];
  for (let i = 0; i < 5; i++) {
    const t = ((n + i) / n) * Math.PI * 4;
    predicted_3d.push([
      Math.sin(t) * 1.5,
      Math.sin(t * 1.3 + 0.5) * 1.2,
      Math.cos(t * 0.7) * 1.0,
    ]);
  }
  return {
    points_3d,
    curvatures,
    predicted_3d,
    fabric_primitives: [
      { fabric: "Space", x: 0.8, y: 0.2, z: 0.1, scale: 0.5 },
      { fabric: "Field", x: -0.5, y: 0.7, z: 0.3, scale: 0.4 },
      { fabric: "Control", x: 0.1, y: -0.6, z: 0.8, scale: 0.3 },
      { fabric: "Precipitation", x: -0.3, y: -0.4, z: -0.7, scale: 0.35 },
    ],
    n_points: n,
    n_predicted: 5,
    causal_dims: [0, 1, 2],
  };
}

// Map curvature ∈ [0,1] → HSL color: blue (stable) → red (high surprise)
function curvatureColor(c: number): THREE.Color {
  return new THREE.Color().setHSL(0.66 - c * 0.66, 1.0, 0.5);
}

// Build a TubeGeometry with per-vertex curvature coloring from a list of points
function buildTube(
  pts: [number, number, number][],
  curvatures: number[],
  radius: number,
  radialSegments = 6
): THREE.TubeGeometry | null {
  if (pts.length < 2) return null;
  const curve = new THREE.CatmullRomCurve3(
    pts.map(([x, y, z]) => new THREE.Vector3(x, y, z))
  );
  const tubularSegments = pts.length * 3;
  const geo = new THREE.TubeGeometry(curve, tubularSegments, radius, radialSegments, false);

  // Per-vertex color attribute keyed to the closest curvature sample
  const vertCount = geo.attributes.position.count;
  const colors = new Float32Array(vertCount * 3);
  const vertsPerRing = radialSegments + 1;

  for (let seg = 0; seg <= tubularSegments; seg++) {
    const t = seg / tubularSegments;
    const cIdx = Math.min(
      Math.floor(t * (curvatures.length - 1)),
      curvatures.length - 1
    );
    const col = curvatureColor(curvatures[cIdx]);
    for (let r = 0; r < vertsPerRing; r++) {
      const vi = (seg * vertsPerRing + r) * 3;
      if (vi + 2 < colors.length) {
        colors[vi] = col.r;
        colors[vi + 1] = col.g;
        colors[vi + 2] = col.b;
      }
    }
  }
  geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
  return geo;
}

export interface JEPATrajectoryMeshProps {
  /** Scale all coordinates (default 2.0 to fit Genesis scene bounds) */
  scale?: number;
  /** Refresh trajectory data on mount (default true) */
  autoFetch?: boolean;
}

/**
 * JEPATrajectoryMesh
 *
 * Renders the JEPA world model's latent trajectory as an explicit triangle
 * mesh inside the Genesis scene. Inspired by FLAT (arxiv 2606.24876):
 * the 64D latent space is projected to 3D via the top-3 causal embedding
 * dimensions, then rendered as a TubeGeometry with per-vertex curvature
 * coloring (cool=stable, warm=high surprise).
 *
 * Predicted future states appear as a semi-transparent continuation.
 * Fabric primitives (Space/Field/Control/Precipitation) appear as small
 * glowing spheres at the terminal predicted positions.
 */
export default function JEPATrajectoryMesh({
  scale = 2.0,
  autoFetch = true,
}: JEPATrajectoryMeshProps) {
  const [data, setData] = useState<TrajectoryData | null>(null);
  const groupRef = useRef<THREE.Group>(null);

  useEffect(() => {
    if (!autoFetch) {
      setData(generateLocalTrajectory());
      return;
    }
    const controller = new AbortController();
    fetch(`${API_BASE}/api/genesis/jepa/trajectory?n_steps=30&n_predict=5`, {
      signal: controller.signal,
    })
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        return r.json() as Promise<TrajectoryData>;
      })
      .then(setData)
      .catch(() => setData(generateLocalTrajectory()));
    return () => controller.abort();
  }, [autoFetch]);

  // Slow rotation so the trajectory reads as 3D
  useFrame((_, delta) => {
    if (groupRef.current) {
      groupRef.current.rotation.y += delta * 0.08;
    }
  });

  const scaledPts = useMemo(
    () =>
      data?.points_3d.map(
        ([x, y, z]) => [x * scale, y * scale, z * scale] as [number, number, number]
      ) ?? [],
    [data, scale]
  );

  const scaledPred = useMemo(
    () =>
      data?.predicted_3d.map(
        ([x, y, z]) => [x * scale, y * scale, z * scale] as [number, number, number]
      ) ?? [],
    [data, scale]
  );

  const trajectoryGeo = useMemo(
    () => buildTube(scaledPts, data?.curvatures ?? [], 0.04),
    [scaledPts, data?.curvatures]
  );

  // Join last trajectory point to predicted points for a seamless extension
  const predictedGeo = useMemo(() => {
    if (!data || scaledPts.length === 0 || scaledPred.length === 0) return null;
    const joinedPts: [number, number, number][] = [
      scaledPts[scaledPts.length - 1],
      ...scaledPred,
    ];
    const flatCurvatures = new Array(joinedPts.length).fill(0.8);
    return buildTube(joinedPts, flatCurvatures, 0.025);
  }, [scaledPts, scaledPred, data]);

  if (!data) return null;

  return (
    <group ref={groupRef}>
      {/* Past trajectory — curvature-colored explicit triangle mesh */}
      {trajectoryGeo && (
        <mesh geometry={trajectoryGeo}>
          <meshStandardMaterial
            vertexColors
            roughness={0.25}
            metalness={0.6}
            emissiveIntensity={0.15}
          />
        </mesh>
      )}

      {/* Predicted future — semi-transparent mesh extension */}
      {predictedGeo && (
        <mesh geometry={predictedGeo}>
          <meshStandardMaterial
            color="#88aaff"
            transparent
            opacity={0.38}
            roughness={0.5}
            depthWrite={false}
          />
        </mesh>
      )}

      {/* Fabric primitive markers at terminal predicted positions */}
      {data.fabric_primitives.map((p) => {
        const color = FABRIC_COLORS[p.fabric] ?? new THREE.Color("#ffffff");
        return (
          <mesh
            key={p.fabric}
            position={[p.x * scale, p.y * scale, p.z * scale]}
          >
            <sphereGeometry args={[Math.max(0.04, p.scale * 0.15), 8, 8]} />
            <meshStandardMaterial
              color={color}
              emissive={color}
              emissiveIntensity={0.5}
              roughness={0.3}
            />
          </mesh>
        );
      })}
    </group>
  );
}
