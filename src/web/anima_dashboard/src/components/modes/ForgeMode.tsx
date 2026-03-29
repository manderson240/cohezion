"use client";

import { useState, useEffect, useCallback } from "react";
import { useUniverse } from "@/context/UniverseProvider";
import ProvenanceTag from "@/components/ProvenanceTag";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface HardwareTelemetry {
  cpu_temp: number;
  gpu_temp: number;
  cpu_power: number;
  gpu_power: number;
  memory_used_gb: number;
  gpu_clock_mhz: number;
  timestamp: number;
}

interface BenchmarkResult {
  passed: boolean;
  score_us: number;
  kernel: string;
  mode: string;
  elapsed_s: number;
  error: string | null;
  stdout: string;
  stderr: string;
}

export default function ForgeMode() {
  const { connected } = useUniverse();
  const [telemetry, setTelemetry] = useState<HardwareTelemetry | null>(null);
  const [benchmarking, setBenchmarking] = useState(false);
  const [lastResult, setLastResult] = useState<BenchmarkResult | null>(null);
  const [selectedKernel, setSelectedKernel] = useState<"gemm" | "moe" | "mla">("gemm");

  const fetchTelemetry = useCallback(async () => {
    try {
      const resp = await fetch(`${API_BASE}/api/forge/telemetry`);
      if (resp.ok) {
        setTelemetry(await resp.json());
      }
    } catch (err) {
      console.error("Failed to fetch telemetry", err);
    }
  }, []);

  useEffect(() => {
    const timer = setInterval(fetchTelemetry, 2000);
    fetchTelemetry();
    return () => clearInterval(timer);
  }, [fetchTelemetry]);

  const runBenchmark = async () => {
    setBenchmarking(true);
    setLastResult(null);
    try {
      const resp = await fetch(`${API_BASE}/api/forge/benchmark`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kernel: selectedKernel, mode: "benchmark" }),
      });
      if (resp.ok) {
        setLastResult(await resp.json());
      } else {
        const err = await resp.json();
        alert(`Benchmark failed: ${err.detail}`);
      }
    } catch (err) {
      console.error("Benchmark error", err);
    } finally {
      setBenchmarking(false);
    }
  };

  return (
    <div className="grid grid-cols-1 xl:grid-cols-12 gap-8 font-mono">
      {/* Header Banner */}
      <div className="xl:col-span-12 bg-orange-500/10 border border-orange-500/20 rounded-xl p-6 backdrop-blur-md">
        <h2 className="text-2xl font-bold text-orange-400 flex items-center gap-3">
          <span className="w-3 h-3 bg-orange-500 rounded-full animate-pulse" />
          GENESIS FORGE ENGINE
        </h2>
        <p className="text-gray-400 mt-2 max-w-2xl text-sm">
          Substrate-level hardware orchestration for the Strix Halo architecture. 
          Real-time telemetry and MXFP4 kernel benchmarking via popcorn-cli.
        </p>
      </div>

      {/* Hardware Telemetry Section */}
      <div className="xl:col-span-12 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          { label: "CPU TEMP", value: `${telemetry?.cpu_temp.toFixed(1)}°C`, color: "text-blue-400", source: "HardwareMonitor.get_cpu_temp()" },
          { label: "GPU TEMP", value: `${telemetry?.gpu_temp.toFixed(1)}°C`, color: "text-emerald-400", source: "HardwareMonitor.get_gpu_temp()" },
          { label: "CPU POWER", value: `${telemetry?.cpu_power.toFixed(1)}W`, color: "text-amber-400", source: "HardwareMonitor.get_cpu_power()" },
          { label: "GPU POWER", value: `${telemetry?.gpu_power.toFixed(1)}W`, color: "text-rose-400", source: "HardwareMonitor.get_gpu_power()" },
        ].map((item) => (
          <div key={item.label} className="bg-white/5 border border-white/10 rounded-xl p-5 group hover:bg-white/10 transition-all">
            <div className="text-[10px] text-gray-500 mb-1">{item.label}</div>
            <ProvenanceTag source={item.source}>
               <div className={`text-2xl font-bold ${item.color}`}>{telemetry ? item.value : "---"}</div>
            </ProvenanceTag>
          </div>
        ))}
      </div>

      {/* Main Forge Interface */}
      <div className="xl:col-span-8 flex flex-col gap-6">
        <section className="bg-black/40 border border-white/5 rounded-2xl p-8 backdrop-blur-xl h-full">
          <h3 className="text-lg font-bold text-white mb-6 uppercase tracking-widest border-b border-white/5 pb-4">
            Kernel Forge
          </h3>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
            {(["gemm", "moe", "mla"] as const).map((k) => (
              <button
                key={k}
                onClick={() => setSelectedKernel(k)}
                className={`p-6 rounded-xl border transition-all text-left ${
                  selectedKernel === k 
                    ? "bg-orange-500/20 border-orange-500/50 shadow-[0_0_20px_rgba(249,115,22,0.15)]" 
                    : "bg-white/5 border-white/10 hover:border-white/20"
                }`}
              >
                <div className="text-xs text-gray-400 mb-1 uppercase">Kernel Type</div>
                <div className={`text-xl font-bold ${selectedKernel === k ? "text-orange-400" : "text-white"}`}>
                  {k.toUpperCase()}
                </div>
                <div className="text-[10px] text-gray-500 mt-2">
                  {k === "gemm" && "Dense Matrix Multiplication"}
                  {k === "moe" && "Mixture of Experts (Sparse)"}
                  {k === "mla" && "Multi-Head Latent Attention"}
                </div>
              </button>
            ))}
          </div>

          <div className="flex flex-col gap-4">
             <button
               onClick={runBenchmark}
               disabled={benchmarking || !connected}
               className={`w-full py-4 rounded-xl font-bold text-sm tracking-[0.2em] transition-all ${
                 benchmarking 
                   ? "bg-white/10 text-gray-500 cursor-not-allowed" 
                   : "bg-orange-500 hover:bg-orange-600 text-black shadow-lg shadow-orange-500/20"
               }`}
             >
               {benchmarking ? "BENCHMARKING SUBSTRATE..." : "IGNITE FORGE"}
             </button>
             {!connected && <p className="text-center text-red-500 text-[10px] animate-pulse">DISCONNECTED FROM NEURAL BACKEND</p>}
          </div>

          {lastResult && (
            <div className={`mt-8 p-6 rounded-xl border animate-in fade-in slide-in-from-bottom-4 duration-500 ${
              lastResult.passed ? "bg-emerald-500/5 border-emerald-500/20" : "bg-red-500/5 border-red-500/20"
            }`}>
              <div className="flex justify-between items-start mb-4">
                <div>
                  <div className="text-[10px] text-gray-500 uppercase tracking-widest">Benchmark Result</div>
                  <div className={`text-xl font-bold ${lastResult.passed ? "text-emerald-400" : "text-red-400"}`}>
                    {lastResult.passed ? "NOMINAL" : "CRITICAL FAILURE"}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[10px] text-gray-500 uppercase">Execution Time</div>
                  <div className="text-xl font-bold text-white">{lastResult.score_us.toFixed(2)} μs</div>
                </div>
              </div>
              
              <div className="bg-black/40 rounded-lg p-4 font-mono text-[10px] max-h-48 overflow-y-auto border border-white/5">
                <div className="text-gray-500 mb-2">// STDOUT</div>
                <pre className="text-gray-300 whitespace-pre-wrap">{lastResult.stdout}</pre>
                {lastResult.stderr && (
                  <>
                    <div className="text-red-500/50 mt-4 mb-2">// STDERR</div>
                    <pre className="text-red-400 whitespace-pre-wrap">{lastResult.stderr}</pre>
                  </>
                )}
              </div>
            </div>
          )}
        </section>
      </div>

      {/* Right Sidebar: Substrate Details */}
      <div className="xl:col-span-4 flex flex-col gap-6">
        <section className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 backdrop-blur-xl">
          <h3 className="text-sm font-bold text-gray-400 mb-6 font-mono tracking-widest uppercase">
            Substrate Logic
          </h3>
          <div className="space-y-4">
             {[
               { label: "Architecture", value: "Strix Halo (2025)", source: "substrate.profile" },
               { label: "Precision", value: "MXFP4 / OC8", source: "substrate.precision_gate" },
               { label: "GPU Memory", value: `${telemetry?.memory_used_gb.toFixed(2)} GB`, source: "HardwareMonitor.get_memory_info()" },
               { label: "Clock Speed", value: `${telemetry?.gpu_clock_mhz.toFixed(0)} MHz`, color: "text-cyan-400", source: "HardwareMonitor.get_gpu_clock()" },
             ].map((item) => (
               <div key={item.label} className="flex justify-between items-center border-b border-white/5 pb-2">
                 <span className="text-xs text-gray-500">{item.label}</span>
                 <ProvenanceTag source={item.source}>
                   <span className={`text-xs font-bold ${item.color ?? "text-white"}`}>{item.value}</span>
                 </ProvenanceTag>
               </div>
             ))}
          </div>
          
          <div className="mt-8">
            <div className="text-[10px] text-gray-500 uppercase tracking-[0.2em] mb-4">Real-time Performance</div>
            <div className="h-24 w-full bg-white/5 rounded-lg relative overflow-hidden flex items-end px-1 gap-0.5">
               {/* Mock performance bars */}
               {Array.from({ length: 40 }).map((_, i) => (
                 <div 
                   key={i} 
                   className="flex-1 bg-orange-500/30 rounded-t-sm" 
                   style={{ 
                     height: `${20 + Math.random() * 60}%`,
                     opacity: 0.3 + (i / 40) * 0.7
                   }} 
                 />
               ))}
            </div>
          </div>
        </section>

        <section className="bg-orange-500/5 border border-orange-500/10 rounded-2xl p-6">
           <h4 className="text-xs font-bold text-orange-400 mb-4 uppercase tracking-widest">System Alert</h4>
           <p className="text-[11px] text-gray-400 leading-relaxed font-mono">
             High-power resonance detected in MXFP4 accumulator. Coherence stability requires active thermal management for kernels exceeding 500μs.
           </p>
        </section>
      </div>
    </div>
  );
}
