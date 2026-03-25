"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, BookOpen } from "lucide-react";
import dynamic from "next/dynamic";

// Dynamic import to prevent SSR issues with Three.js
const FlumeNavigator = dynamic(() => import("@/components/FlumeNavigator"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[600px] bg-black/90 rounded-xl flex items-center justify-center border border-cyan-500/20">
      <span className="text-cyan-500/50 font-mono text-xs tracking-widest animate-pulse">
        INITIALIZING FLUME NAVIGATOR...
      </span>
    </div>
  ),
});

export default function FlumeDemoPage() {
  const [activeTab, setActiveTab] = useState<"demo" | "explanation">("demo");

  return (
    <div className="min-h-screen bg-[#000000] text-white">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-cyan-500/10 rounded-full blur-[150px] animate-pulse" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-[150px] animate-pulse" style={{ animationDelay: "1s" }} />
      </div>

      <div className="relative z-10">
        {/* Header */}
        <nav className="border-b border-white/10 backdrop-blur-xl bg-black/50">
          <div className="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
            <Link href="/portfolio" className="flex items-center gap-2 text-cyan-400 hover:text-cyan-300 transition-colors">
              <ArrowLeft className="w-5 h-5" />
              <span className="font-mono text-sm">BACK TO PORTFOLIO</span>
            </Link>
            <div className="flex gap-4">
              <button
                onClick={() => setActiveTab("demo")}
                className={`px-4 py-2 rounded-lg font-mono text-xs transition-all ${
                  activeTab === "demo"
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                DEMO
              </button>
              <button
                onClick={() => setActiveTab("explanation")}
                className={`px-4 py-2 rounded-lg font-mono text-xs transition-all ${
                  activeTab === "explanation"
                    ? "bg-cyan-500/20 text-cyan-400 border border-cyan-500/30"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                EXPLANATION
              </button>
              <Link
                href="/portfolio/blog/flume-vae"
                className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 border border-white/20 rounded-lg text-white font-mono text-xs transition-all"
              >
                <BookOpen className="w-4 h-4" />
                <span>BLOG POST</span>
              </Link>
            </div>
          </div>
        </nav>

        <div className="max-w-7xl mx-auto px-6 py-12">
          {/* Title Section */}
          <div className="mb-12">
            <div className="inline-block mb-4 px-4 py-2 bg-cyan-500/10 border border-cyan-500/30 rounded-full">
              <span className="text-xs font-mono text-cyan-400 tracking-widest">
                PILLAR #1 — CONTINUOUS LATENT NAVIGATION
              </span>
            </div>
            <h1 className="text-5xl font-bold mb-4 font-mono">
              FLUME VAE
              <span className="text-cyan-400">.</span>
            </h1>
            <p className="text-xl text-gray-400 max-w-3xl leading-relaxed">
              Navigate a 256-dimensional software state space through continuous latent embeddings.
              Trained on git commit histories to enable smooth interpolation between discrete code snapshots.
            </p>
          </div>

          {activeTab === "demo" ? (
            <div className="space-y-8">
              {/* Interactive Demo */}
              <FlumeNavigator className="w-full" />

              {/* Quick Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-6">
                  <div className="text-3xl font-bold font-mono text-cyan-400 mb-2">256D</div>
                  <div className="text-sm text-gray-400">Input Dimension</div>
                  <div className="text-xs text-gray-600 mt-2">Software state vectors</div>
                </div>
                <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-6">
                  <div className="text-3xl font-bold font-mono text-cyan-400 mb-2">~32D</div>
                  <div className="text-sm text-gray-400">Latent Dimension</div>
                  <div className="text-xs text-gray-600 mt-2">Compressed representation</div>
                </div>
                <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-6">
                  <div className="text-3xl font-bold font-mono text-cyan-400 mb-2">∞</div>
                  <div className="text-sm text-gray-400">Continuous Space</div>
                  <div className="text-xs text-gray-600 mt-2">Smooth interpolation</div>
                </div>
              </div>

              {/* How to Use */}
              <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-8">
                <h2 className="text-2xl font-bold mb-6 font-mono text-cyan-400">
                  How to Use This Demo
                </h2>
                <div className="space-y-4 text-gray-400">
                  <div className="flex gap-4">
                    <div className="text-cyan-400 font-mono font-bold">1.</div>
                    <div>
                      <strong className="text-white">Explore the Point Cloud:</strong> Each point represents a sample
                      from the VAE's latent space. Colors indicate coherence (blue = low, green = medium, yellow/red = high).
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="text-cyan-400 font-mono font-bold">2.</div>
                    <div>
                      <strong className="text-white">Adjust Sample Count:</strong> Use the slider to change the number
                      of points rendered. More samples = denser visualization, but slower rendering.
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="text-cyan-400 font-mono font-bold">3.</div>
                    <div>
                      <strong className="text-white">Navigate in 3D:</strong> Drag to rotate, scroll to zoom, right-click
                      to pan. The point cloud slowly rotates when not interacting.
                    </div>
                  </div>
                  <div className="flex gap-4">
                    <div className="text-cyan-400 font-mono font-bold">4.</div>
                    <div>
                      <strong className="text-white">Click Points:</strong> (Coming soon) Click individual points to see
                      their latent coordinates and decode them back to 256D space.
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-8">
              {/* Explanation Content */}
              <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-8">
                <h2 className="text-2xl font-bold mb-6 font-mono text-cyan-400">
                  What is FLUME?
                </h2>
                <div className="space-y-4 text-gray-400 leading-relaxed">
                  <p>
                    <strong className="text-white">FLUME (Fluid Latent Universe Model Engine)</strong> is a Variational
                    Autoencoder (VAE) trained on software state representations. Unlike traditional version control systems
                    that treat code as discrete snapshots, FLUME learns a continuous latent space where similar code states
                    are nearby.
                  </p>
                  <p>
                    This enables <strong className="text-white">semantic interpolation</strong>: you can smoothly navigate
                    between two git commits, generating intermediate states that never existed but are semantically coherent.
                    Think of it as "filling in the blanks" between code versions.
                  </p>
                </div>
              </div>

              <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-8">
                <h2 className="text-2xl font-bold mb-6 font-mono text-cyan-400">
                  Technical Architecture
                </h2>
                <div className="space-y-6">
                  <div>
                    <h3 className="text-lg font-bold text-white mb-2 font-mono">Encoder</h3>
                    <p className="text-gray-400 text-sm">
                      Maps 256D input vectors (software states) to ~32D latent space via neural network.
                      Outputs mean (μ) and log-variance (log σ²) for each latent dimension.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white mb-2 font-mono">Latent Space</h3>
                    <p className="text-gray-400 text-sm">
                      Continuous, lower-dimensional representation where similar code states cluster together.
                      Enables semantic operations like interpolation, extrapolation, and nearest-neighbor search.
                    </p>
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white mb-2 font-mono">Decoder</h3>
                    <p className="text-gray-400 text-sm">
                      Reconstructs 256D output from latent vector. Trained to minimize reconstruction error (MSE)
                      while maintaining smooth latent space structure (KL divergence regularization).
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-xl p-8">
                <h2 className="text-2xl font-bold mb-6 font-mono text-cyan-400">
                  Why This Matters for AI Research
                </h2>
                <div className="space-y-4 text-gray-400 leading-relaxed">
                  <p>
                    Traditional RL environments use <strong className="text-white">discrete observation spaces</strong> —
                    a fixed set of possible states. FLUME demonstrates how to build{" "}
                    <strong className="text-white">continuous state spaces</strong> for complex domains like software
                    engineering, enabling:
                  </p>
                  <ul className="list-disc list-inside space-y-2 ml-4">
                    <li>
                      <strong className="text-white">Gradient-based navigation:</strong> Move through state space using
                      calculus, not discrete search.
                    </li>
                    <li>
                      <strong className="text-white">Semantic similarity:</strong> Measure "distance" between code states
                      in meaningful ways.
                    </li>
                    <li>
                      <strong className="text-white">Generalization:</strong> Generate novel states by sampling or
                      interpolating in latent space.
                    </li>
                    <li>
                      <strong className="text-white">Curriculum learning:</strong> Gradually increase task difficulty by
                      navigating from simple to complex regions.
                    </li>
                  </ul>
                </div>
              </div>

              <div className="bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border border-cyan-500/30 rounded-xl p-8">
                <h2 className="text-2xl font-bold mb-4 font-mono text-cyan-400">
                  Anthropic Universes Relevance
                </h2>
                <p className="text-gray-300 leading-relaxed">
                  This approach directly applies to building <strong className="text-white">scalable simulation
                  environments</strong> for agent training. Instead of hand-crafting discrete observation spaces,
                  FLUME-style VAEs can learn continuous representations of complex domains (code, text, multimodal
                  data), enabling agents to explore and learn in richer state spaces.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
