"use client";

import React, { useRef, useEffect } from "react";
import { HardDriveDownload } from "lucide-react";

/**
 * Renders a 256-cell CA grid as a 16x16 heatmap on a canvas.
 * Active cells (1) are emerald, inactive (0) are near-black.
 */
function CAGridCanvas({ grid, size = 128 }: { grid: number[]; size?: number }) {
    const canvasRef = useRef<HTMLCanvasElement>(null);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas || grid.length === 0) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const dim = Math.ceil(Math.sqrt(grid.length)); // 16 for 256
        const cellSize = size / dim;

        ctx.fillStyle = "#050505";
        ctx.fillRect(0, 0, size, size);

        for (let i = 0; i < grid.length; i++) {
            const x = (i % dim) * cellSize;
            const y = Math.floor(i / dim) * cellSize;
            ctx.fillStyle = grid[i] === 1 ? "#10b981" : "#111111";
            ctx.fillRect(x, y, cellSize - 0.5, cellSize - 0.5);
        }
    }, [grid, size]);

    return (
        <canvas
            ref={canvasRef}
            width={size}
            height={size}
            className="rounded-lg border border-emerald-900/30 shadow-inner"
        />
    );
}

export default function SnapshotGallery({ caGrid, coherence, tick }: {
    caGrid?: number[];
    coherence?: number;
    tick?: number;
}) {
    const density = caGrid && caGrid.length > 0 ? caGrid.reduce((s, v) => s + v, 0) / caGrid.length : 0;

    return (
        <div className="bg-white/[0.02] backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl relative overflow-hidden group">
            <div className="absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-emerald-900/10 to-transparent pointer-events-none"></div>
            <h2 className="text-xl font-bold mb-8 font-mono text-white flex items-center relative z-10 drop-shadow-[0_0_5px_rgba(255,255,255,0.3)]">
                <HardDriveDownload className="w-6 h-6 mr-3 text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.8)]" />
                CELLULAR AUTOMATA FABRIC
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10">
                {/* Live CA grid heatmap */}
                <div className="flex flex-col items-center gap-4">
                    <CAGridCanvas grid={caGrid ?? []} size={192} />
                    <div className="text-[10px] font-mono text-gray-500 tracking-widest">
                        WOLFRAM RULE 30 // {caGrid?.length ?? 0} CELLS
                    </div>
                </div>

                {/* CA metrics */}
                <div className="flex flex-col gap-5 justify-center">
                    <div className="p-4 bg-black/40 rounded-xl border border-white/5">
                        <div className="text-[10px] text-gray-500 font-mono tracking-widest mb-2">CA DENSITY</div>
                        <div className="text-2xl font-black font-mono text-emerald-400">
                            {(density * 100).toFixed(1)}%
                        </div>
                        <div className="mt-3 w-full bg-gray-900 rounded-full h-1.5 overflow-hidden">
                            <div
                                className="h-1.5 rounded-full bg-emerald-500 transition-all duration-500"
                                style={{ width: `${density * 100}%` }}
                            />
                        </div>
                    </div>

                    <div className="p-4 bg-black/40 rounded-xl border border-white/5">
                        <div className="text-[10px] text-gray-500 font-mono tracking-widest mb-2">HIHO COHERENCE</div>
                        <div className={`text-2xl font-black font-mono ${(coherence ?? 0.5) >= 0.5 ? 'text-amber-400' : 'text-red-400'}`}>
                            {(coherence ?? 0.5).toFixed(4)}
                        </div>
                    </div>

                    <div className="p-4 bg-black/40 rounded-xl border border-white/5">
                        <div className="text-[10px] text-gray-500 font-mono tracking-widest mb-2">SIMULATION TICK</div>
                        <div className="text-2xl font-black font-mono text-blue-400">
                            {(tick ?? 0).toLocaleString()}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
