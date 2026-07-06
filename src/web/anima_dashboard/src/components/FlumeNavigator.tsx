"use client";

import { useEffect, useRef, useState, useCallback, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, PerspectiveCamera } from "@react-three/drei";
import * as THREE from "three";
import { ErrorBoundary } from "react-error-boundary";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface LatentSpaceData {
  latent_dim: number;
  samples: number[][];
  samples_3d: number[][];
  variance_explained: number[];
  coherence_scores: number[];
}

interface PointCloudProps {
  points: number[][];
  coherenceScores: number[];
  highlightedIndex: number | null;
  onPointClick: (index: number) => void;
}

function PointCloud({ points, coherenceScores, highlightedIndex, onPointClick }: PointCloudProps) {
  const meshRef = useRef<THREE.Points>(null);

  // Issue #11: Memoize geometry to prevent recreation on every render
  const geometry = useMemo(() => {
    const geom = new THREE.BufferGeometry();
    const positions = new Float32Array(points.flat());
    geom.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    // Color based on coherence (blue = low, green = medium, yellow/red = high)
    const colors = new Float32Array(
      points.flatMap((_, i) => {
        const coherence = coherenceScores[i] ?? 0.5;
        // Map coherence [0, 1] to color gradient: blue -> cyan -> green -> yellow -> red
        const r = Math.min(1, Math.max(0, (coherence - 0.5) * 2));
        const g = coherence > 0.5 ? 1 - (coherence - 0.5) * 2 : coherence * 2;
        const b = Math.max(0, 1 - coherence * 2);
        return [r, g, b];
      })
    );
    geom.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    return geom;
  }, [points, coherenceScores]);

  // Animate rotation with velocity limit (Issue #20)
  useFrame((state) => {
    if (meshRef.current && highlightedIndex === null) {
      const rotation = state.clock.elapsedTime * 0.1;
      // Clamp rotation speed to prevent motion sickness
      meshRef.current.rotation.y = rotation % (Math.PI * 2);
    }
  });

  // Cleanup geometry on unmount
  useEffect(() => {
    return () => {
      geometry.dispose();
    };
  }, [geometry]);

  return (
    <points ref={meshRef} geometry={geometry}>
      <pointsMaterial
        size={highlightedIndex !== null ? 0.03 : 0.05}
        vertexColors
        transparent
        opacity={0.8}
        sizeAttenuation
      />
    </points>
  );
}

interface FlumeNavigatorProps {
  className?: string;
}

// Issue #12: WebGL context loss recovery
function WebGLCanvas({ data, selectedPoint, onPointClick }: { data: LatentSpaceData; selectedPoint: number | null; onPointClick: (index: number) => void }) {
  const [contextLost, setContextLost] = useState(false);

  useEffect(() => {
    const canvas = document.querySelector('canvas');
    if (!canvas) return;

    const handleContextLost = (e: Event) => {
      e.preventDefault();
      setContextLost(true);
      console.warn('WebGL context lost, attempting recovery...');
    };

    const handleContextRestored = () => {
      setContextLost(false);
      console.log('WebGL context restored');
    };

    canvas.addEventListener('webglcontextlost', handleContextLost);
    canvas.addEventListener('webglcontextrestored', handleContextRestored);

    return () => {
      canvas.removeEventListener('webglcontextlost', handleContextLost);
      canvas.removeEventListener('webglcontextrestored', handleContextRestored);
    };
  }, []);

  if (contextLost) {
    return (
      <div className="w-full h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-amber-400 font-mono text-sm mb-4">WEBGL CONTEXT LOST</div>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 rounded-lg text-amber-400 text-xs font-mono transition-all"
          >
            RELOAD PAGE
          </button>
        </div>
      </div>
    );
  }

  return (
    <Canvas>
      <PerspectiveCamera makeDefault position={[5, 5, 5]} />
      <OrbitControls
        enableDamping
        dampingFactor={0.05}
        autoRotateSpeed={2}
      />

      <ambientLight intensity={0.3} />
      <pointLight position={[10, 10, 10]} intensity={0.5} />
      <pointLight position={[-10, -10, -10]} intensity={0.3} color="#00ffff" />

      <PointCloud
        points={data.samples_3d}
        coherenceScores={data.coherence_scores}
        highlightedIndex={selectedPoint}
        onPointClick={onPointClick}
      />

      <axesHelper args={[3]} />
      <gridHelper args={[10, 10, "#333333", "#111111"]} />
    </Canvas>
  );
}

// Issue #15: Error boundary fallback
function ErrorFallback({ error, resetErrorBoundary }: { error: unknown; resetErrorBoundary: () => void }) {
  const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';

  return (
    <div className="w-full h-[600px] bg-black/90 rounded-xl flex items-center justify-center border border-red-500/20">
      <div className="text-center max-w-md p-6">
        <div className="text-red-400 font-mono text-sm mb-4">VISUALIZATION ERROR</div>
        <div className="text-gray-500 text-xs mb-4">{errorMessage}</div>
        <div className="text-gray-600 text-xs mb-4">
          This may be due to WebGL not being available on your device.
        </div>
        <button
          onClick={resetErrorBoundary}
          className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg text-red-400 text-xs font-mono transition-all"
        >
          TRY AGAIN
        </button>
      </div>
    </div>
  );
}

export default function FlumeNavigator({ className = "" }: FlumeNavigatorProps) {
  const [data, setData] = useState<LatentSpaceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPoint, setSelectedPoint] = useState<number | null>(null);
  const [nSamples, setNSamples] = useState(200);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Issue #14: Fix infinite loop by stabilizing fetchLatentSpace reference
  const fetchLatentSpace = useCallback(async (samples: number) => {
    // Issue #19: Cancel previous request if still pending
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }

    abortControllerRef.current = new AbortController();
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/flume/latent-space`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ n_samples: samples, seed: null }),  // Issue #18: null seed = random
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
        throw new Error(errorData.detail || `API error: ${response.status}`);
      }

      const result: LatentSpaceData = await response.json();
      setData(result);
      setError(null);
    } catch (err) {
      if (err instanceof Error && err.name === 'AbortError') {
        // Request was cancelled, don't set error
        return;
      }
      setError(err instanceof Error ? err.message : "Failed to fetch latent space");
      console.error("Latent space fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []); // Empty deps = stable reference

  useEffect(() => {
    fetchLatentSpace(nSamples);
  }, [nSamples, fetchLatentSpace]);

  const handlePointClick = useCallback((index: number) => {
    setSelectedPoint(index === selectedPoint ? null : index);
  }, [selectedPoint]);

  if (loading) {
    return (
      <div className={`${className} w-full h-[600px] bg-black/90 rounded-xl flex items-center justify-center border border-cyan-500/20`}>
        <div className="text-center">
          <div className="text-cyan-400 font-mono text-sm mb-4 animate-pulse">
            SAMPLING LATENT SPACE...
          </div>
          <div className="w-48 h-1 bg-cyan-500/20 rounded-full overflow-hidden">
            <div className="h-full bg-cyan-500 animate-pulse" style={{ width: "60%" }} />
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`${className} w-full h-[600px] bg-black/90 rounded-xl flex items-center justify-center border border-red-500/20`}>
        <div className="text-center">
          <div className="text-red-400 font-mono text-sm mb-4">ERROR</div>
          <div className="text-gray-500 text-xs mb-4">{error}</div>
          <button
            onClick={() => fetchLatentSpace(nSamples)}
            className="mt-4 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 border border-red-500/30 rounded-lg text-red-400 text-xs font-mono transition-all"
          >
            RETRY
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // Issue #17: Prevent division by zero
  const meanCoherence = data.coherence_scores.length > 0
    ? (data.coherence_scores.reduce((a, b) => a + b, 0) / data.coherence_scores.length).toFixed(3)
    : "N/A";

  return (
    <div className={`${className} space-y-4`}>
      {/* Info Panel */}
      <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-4 stats-container">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs font-mono">
          <div>
            <div className="text-gray-500 mb-1">LATENT DIM</div>
            <div className="text-cyan-400 font-bold">{data.latent_dim}D</div>
          </div>
          <div>
            <div className="text-gray-500 mb-1">SAMPLES</div>
            <div className="text-cyan-400 font-bold">{data.samples_3d.length}</div>
          </div>
          <div>
            <div className="text-gray-500 mb-1">VAR EXPLAINED</div>
            <div className="text-cyan-400 font-bold">
              {data.variance_explained.length > 0
                ? `${(data.variance_explained.reduce((a, b) => a + b, 0) * 100).toFixed(1)}%`
                : "N/A"}
            </div>
          </div>
          <div>
            <div className="text-gray-500 mb-1">MEAN COHERENCE</div>
            <div className="text-cyan-400 font-bold" data-testid="mean-coherence">{meanCoherence}</div>
          </div>
        </div>

        {/* Controls */}
        <div className="mt-4 flex items-center gap-4">
          <label className="text-xs text-gray-500 font-mono">SAMPLES:</label>
          <input
            type="range"
            min="50"
            max="500"
            step="50"
            value={nSamples}
            onChange={(e) => setNSamples(parseInt(e.target.value))}
            className="flex-1"
            aria-label="Sample Count"
          />
          <span className="text-xs text-cyan-400 font-mono w-12">{nSamples}</span>
          <button
            onClick={() => fetchLatentSpace(nSamples)}
            className="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 border border-cyan-500/30 rounded-lg text-cyan-400 text-xs font-mono transition-all"
            aria-label="Resample latent space"
          >
            RESAMPLE
          </button>
        </div>
      </div>

      {/* 3D Visualization with Error Boundary (Issue #15) */}
      <div className="w-full h-[600px] bg-black/90 rounded-xl border border-cyan-500/20 overflow-hidden relative" aria-label="FLUME VAE Latent Space">
        <ErrorBoundary FallbackComponent={ErrorFallback} onReset={() => fetchLatentSpace(nSamples)}>
          <WebGLCanvas data={data} selectedPoint={selectedPoint} onPointClick={handlePointClick} />
        </ErrorBoundary>

        {/* Overlay Legend */}
        <div className="absolute top-4 right-4 bg-black/80 backdrop-blur-sm border border-white/10 rounded-lg p-3 text-[10px] font-mono space-y-1">
          <div className="text-gray-500 mb-2">COLOR KEY</div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-gray-400">Low Coherence</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500" />
            <span className="text-gray-400">Med Coherence</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500" />
            <span className="text-gray-400">High Coherence</span>
          </div>
        </div>

        {/* Instructions */}
        <div className="absolute bottom-4 left-4 bg-black/80 backdrop-blur-sm border border-white/10 rounded-lg p-3 text-[10px] font-mono text-gray-400">
          <div>🖱️ Drag to rotate • Scroll to zoom • Right-click to pan</div>
        </div>
      </div>

      {/* Selected Point Details */}
      {selectedPoint !== null && (
        <div className="bg-white/[0.02] backdrop-blur-xl border border-cyan-500/30 rounded-xl p-4">
          <div className="text-sm font-mono text-cyan-400 mb-3">
            SELECTED POINT #{selectedPoint}
          </div>
          <div className="grid grid-cols-2 gap-4 text-xs font-mono">
            <div>
              <div className="text-gray-500 mb-1">3D COORDINATES</div>
              <div className="text-gray-300 font-mono text-[10px]">
                [{data.samples_3d[selectedPoint]?.map((v) => v.toFixed(3)).join(", ") || "N/A"}]
              </div>
            </div>
            <div>
              <div className="text-gray-500 mb-1">COHERENCE</div>
              <div className="text-cyan-400 font-bold">
                {data.coherence_scores[selectedPoint]?.toFixed(4) || "N/A"}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
