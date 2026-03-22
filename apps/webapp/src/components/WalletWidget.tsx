
import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { CreditCard, TrendingUp, Trophy } from 'lucide-react';

interface WalletData {
    balance: number;
    history: Array<{
        timestamp: string;
        amount: number;
        reason: string;
        agent: string;
    }>;
}

export const WalletWidget: React.FC = () => {
    const [wallet, setWallet] = useState<WalletData | null>(null);

    useEffect(() => {
        const fetchWallet = async () => {
            try {
                const response = await fetch('http://localhost:8080/wallet');
                if (response.ok) {
                    const data = await response.json();
                    setWallet(data);
                }
            } catch (e) {
                console.error("Failed to fetch wallet", e);
            }
        };

        fetchWallet();
        const interval = setInterval(fetchWallet, 5000);
        return () => clearInterval(interval);
    }, []);

    if (!wallet) return null;

    return (
        <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="absolute top-4 right-4 z-50 pointer-events-auto"
        >
            <div className="glass p-4 rounded-xl border border-secondary/30 backdrop-blur-md shadow-[0_0_20px_rgba(0,0,0,0.5)] bg-black/40 min-w-[280px]">

                {/* Header */}
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 text-secondary">
                        <Trophy size={18} />
                        <span className="text-xs font-bold uppercase tracking-wider">Ascension Credits</span>
                    </div>
                    <div className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
                </div>

                {/* Balance */}
                <div className="flex items-end gap-1 mb-4">
                    <span className="text-4xl font-black text-white tracking-tight">
                        {wallet.balance.toLocaleString()}
                    </span>
                    <span className="text-xs text-gray-400 mb-1.5">CR</span>
                </div>

                {/* History Snippet */}
                <div className="space-y-2">
                    <div className="text-[10px] uppercase text-gray-500 font-semibold tracking-wider mb-1">Recent Transactions</div>
                    {wallet.history.slice(-2).map((tx, i) => (
                        <div key={i} className="flex justify-between items-center text-xs border-t border-white/5 pt-1">
                            <span className="text-gray-300 truncate max-w-[150px]">{tx.reason}</span>
                            <span className="text-secondary font-mono">+{tx.amount.toLocaleString()}</span>
                        </div>
                    ))}
                </div>

                <div className="mt-3 pt-2 border-t border-white/10 flex justify-between text-[10px] text-gray-500">
                    <span>Next Payout: PENDING</span>
                    <span className="flex items-center gap-1"><CreditCard size={10} /> WALLET CONNECTED</span>
                </div>

            </div>
        </motion.div>
    );
};
