"use client";

import React from "react";
import { Activity, Zap, ShieldAlert, Cpu } from "lucide-react";
import { useUniverse } from "@/context/UniverseProvider";

export default function OuroborosControlRoom() {
    const { state, connected } = useUniverse();

    const coherence = state?.coherence ?? 0.5;
    const evoCount = state?.evo_states.length ?? 0;
    const tick = state?.tick ?? 0;

    return (
        <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-6 text-[#faf9f5] font-mono shadow-2xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-64 h-64 bg-amber-500/5 rounded-full blur-3xl -mx-10 -my-10 pointer-events-none"></div>
            <h2 className="text-xl font-bold mb-6 flex items-center text-amber-500 relative z-10 drop-shadow-[0_0_8px_rgba(245,158,11,0.5)]">
                <ShieldAlert className="w-5 h-5 mr-3" />
                OUROBOROS CONTROL ROOM
                {!connected && <span className="ml-3 text-xs text-gray-500 font-normal animate-pulse">connecting...</span>}
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 relative z-10">
                {/* Coherence — driven by real HIHO engine */}
                <div className="p-5 bg-black/40 rounded-xl border border-white/5 backdrop-blur-sm relative overflow-hidden group/card shadow-inner flex flex-col justify-between transition-colors hover:border-white/10">
                    <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover/card:opacity-100 transition-opacity"></div>
                    <div className="text-xs text-gray-400 mb-3 flex items-center font-bold tracking-widest relative z-10">
                        <Activity className="w-4 h-4 mr-2" />
                        GLOBAL COHERENCE
                    </div>
                    <div className={`text-4xl font-black tracking-tighter relative z-10 drop-shadow-md ${coherence >= 0.85 ? 'text-emerald-400' : coherence >= 0.5 ? 'text-amber-400' : 'text-red-500'}`}>
                        {coherence.toFixed(3)}
                    </div>
                    <div className="mt-5 w-full bg-gray-900 rounded-full h-1.5 overflow-hidden relative z-10">
                        <div
                            className={`h-1.5 rounded-full transition-all duration-500 relative overflow-hidden ${coherence >= 0.85 ? 'bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.8)]' : coherence >= 0.5 ? 'bg-amber-500 shadow-[0_0_10px_rgba(245,158,11,0.8)]' : 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.8)]'}`}
                            style={{ width: `${coherence * 100}%` }}
                        >
                            <div className="absolute inset-0 bg-white/30 animate-[slide_2s_ease-in-out_infinite] w-1/3"></div>
                        </div>
                    </div>
                </div>

                {/* Tick counter — driven by real physics simulation */}
                <div className="p-5 bg-black/40 rounded-xl border border-white/5 backdrop-blur-sm relative overflow-hidden group/card shadow-inner flex flex-col justify-between transition-colors hover:border-white/10">
                    <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover/card:opacity-100 transition-opacity"></div>
                    <div className="text-xs text-gray-400 mb-3 flex items-center font-bold tracking-widest relative z-10">
                        <Zap className="w-4 h-4 mr-2" />
                        SIMULATION TICK
                    </div>
                    <div className="text-4xl font-black tracking-tighter text-blue-400 relative z-10 drop-shadow-[0_0_8px_rgba(96,165,250,0.5)]">
                        {tick.toLocaleString()} <span className="text-sm text-gray-500 font-normal">t</span>
                    </div>
                    <div className="mt-5 text-[10px] text-gray-500 tracking-widest uppercase relative z-10">
                        Time: {(state?.time ?? 0).toFixed(4)}s
                    </div>
                </div>

                {/* EVO Count — driven by real EVO swarm */}
                <div className="p-5 bg-black/40 rounded-xl border border-white/5 backdrop-blur-sm relative overflow-hidden group/card shadow-inner flex flex-col justify-between transition-colors hover:border-white/10">
                    <div className="absolute inset-0 bg-gradient-to-br from-white/5 to-transparent opacity-0 group-hover/card:opacity-100 transition-opacity"></div>
                    <div className="text-xs text-gray-400 mb-3 flex items-center font-bold tracking-widest relative z-10">
                        <Cpu className="w-4 h-4 mr-2" />
                        ACTIVE EVOs
                    </div>
                    <div className="text-4xl font-black tracking-tighter text-purple-400 relative z-10 drop-shadow-[0_0_8px_rgba(168,85,247,0.5)]">
                        {evoCount}
                    </div>
                    <div className="mt-5 flex space-x-1.5 relative z-10">
                        {Array.from({ length: Math.min(evoCount, 12) }).map((_, i) => (
                            <div key={i} className="w-2.5 h-2.5 rounded-full bg-purple-500 shadow-[0_0_8px_rgba(168,85,247,0.8)] animate-pulse" style={{ animationDelay: `${i * 0.15}s` }}></div>
                        ))}
                    </div>
                </div>
            </div>

            <div className="mt-8 p-5 bg-[#050505]/80 rounded-xl font-mono text-[11px] leading-relaxed text-emerald-400/80 h-36 overflow-y-auto border border-white/5 shadow-inner relative z-10 backdrop-blur-md">
                <div className="opacity-50 hover:opacity-100 transition-opacity">[SYSTEM] Mycelium network synced across {evoCount} nodes. VLIW state nominal.</div>
                <div className="opacity-75 hover:opacity-100 transition-opacity">[OUROBOROS] Execution exhaust analyzed. Refining 12D manifold alignment prompts.</div>
                <div className="text-emerald-300 drop-shadow-[0_0_2px_rgba(110,231,183,1)]">[HIHO] Fabric stability nominal. Coherence at {coherence.toFixed(4)}. Tensor Beam active.</div>
                {state?.evo_states.map((evo, i) => (
                    <div key={i} className="opacity-60 hover:opacity-100 transition-opacity">
                        [EVO-{i}] charge={(evo.charge_density ?? 0).toFixed(3)} helicity={(evo.magnetic_helicity ?? 0).toFixed(3)} toroidal={(evo.toroidal_moment ?? 0).toFixed(3)} C={(evo.coherence ?? 0).toFixed(4)}
                    </div>
                ))}
            </div>
        </div>
    );
}
