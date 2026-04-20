import React, { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Activity, Shield, Cpu, MessageSquare, Terminal } from 'lucide-react';
import { clsx } from 'clsx';
import { WalletWidget } from './WalletWidget';

interface Log {
    id: string;
    text: string;
    type: 'info' | 'warning' | 'error';
}

interface CommandCenterProps {
    coherence: string;
    isOnline: boolean;
    logs: Log[];
    children: ReactNode;
}

export const CommandCenter: React.FC<CommandCenterProps> = ({
    coherence,
    isOnline,
    logs,
    children
}) => {
    return (
        <div className="hud-container">
            {/* Left Panel: Vitals */}
            <motion.div
                initial={{ x: -50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                className="hud-panel glass"
            >
                <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-2">
                    <Activity className="text-primary" size={20} />
                    <h2>VITALS</h2>
                </div>

                <div className="grid gap-4">
                    <div className="metric">
                        <span>COHERENCE</span>
                        <span className="value">{coherence}</span>
                    </div>
                    <div className="metric">
                        <span>STATUS</span>
                        <span className={clsx("value", isOnline ? "text-primary" : "text-red-500")}>
                            {isOnline ? "ONLINE" : "OFFLINE"}
                        </span>
                    </div>
                    <div className="metric">
                        <span>BRAIN</span>
                        <span className="value">GEMINI-3-PRO</span>
                    </div>
                </div>

                <div className="mt-auto">
                    <div className="text-xs text-muted uppercase tracking-widest mb-2">System Load</div>
                    <div className="h-1 bg-white/10 w-full rounded overflow-hidden">
                        <motion.div
                            className="h-full bg-primary"
                            animate={{ width: ["40%", "60%", "45%"] }}
                            transition={{ repeat: Infinity, duration: 2 }}
                        />
                    </div>
                </div>
            </motion.div>

            {/* Center: Hologram */}
            <div className="relative w-full h-full glass border-0 bg-transparent shadow-none">
                {children}
                <div className="absolute top-4 left-1/2 -translate-x-1/2 text-xs text-primary/50 tracking-[0.5em] font-bold">
                    ASCENSION PROTOCOL v1.6
                </div>
            </div>

            {/* Right Panel: Logs */}
            <motion.div
                initial={{ x: 50, opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                className="hud-panel glass"
            >
                <div className="flex items-center gap-2 mb-4 border-b border-white/10 pb-2">
                    <Terminal className="text-secondary" size={20} />
                    <h2>LOGS</h2>
                </div>

                <div className="flex flex-col gap-2 overflow-y-auto max-h-[600px] font-mono text-xs">
                    {logs.map(log => (
                        <div key={log.id} className="flex gap-2">
                            <span className="text-gray-500">[{new Date().toLocaleTimeString()}]</span>
                            <span className={clsx(
                                log.type === 'error' ? 'text-red-400' :
                                    log.type === 'warning' ? 'text-yellow-400' : 'text-primary'
                            )}>
                                {log.text}
                            </span>
                        </div>
                    ))}
                    <div className="animate-pulse">_</div>
                </div>
            </motion.div>

            {/* Phase 27: Ascension Wallet Overlay */}
            <WalletWidget />
        </div>
    );
};
