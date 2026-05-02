"use client";

import { useState, useRef, useEffect } from "react";
import { useAnima, type ChatMessage } from "@/hooks/useAnima";

interface AnimaChatPanelProps {
  open: boolean;
  onClose: () => void;
}

/**
 * Slide-out chat panel for Anima (FR15).
 * Triggered by clicking the Anima Sigil in TriuneNav.
 */
export default function AnimaChatPanel({ open, onClose }: AnimaChatPanelProps) {
  const { status, messages, loading, ask } = useAnima();
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    ask(input.trim());
    setInput("");
  };

  const tierLabel =
    status?.tier === "voice"
      ? "Voice Active"
      : status?.tier === "mcp"
        ? "MCP Grounded"
        : "Template Mode";

  return (
    <div
      className={`fixed top-0 right-0 h-full w-96 bg-black/95 backdrop-blur-xl border-l z-50 flex flex-col transition-transform duration-500 ${
        open ? "translate-x-0" : "translate-x-full"
      }`}
      style={{ borderColor: "var(--hiho-glow-color, #00ff00)30" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
        <div>
          <h3 className="text-sm font-bold font-mono tracking-wider text-white">
            ANIMA
          </h3>
          <span
            className="text-[9px] font-mono tracking-widest"
            style={{ color: "var(--hiho-glow-color, #00ff00)" }}
          >
            {tierLabel}
          </span>
        </div>
        <button
          onClick={onClose}
          className="text-gray-500 hover:text-white text-lg transition-colors"
        >
          &times;
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-600 font-mono text-xs mt-8">
            <p className="mb-2">Ask me about HIHO physics, EVOs,</p>
            <p>cellular automata, or the Triune Self.</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        {loading && (
          <div className="text-gray-500 font-mono text-xs animate-pulse">
            Anima is thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-4 py-3 border-t border-white/10">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Anima..."
            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm font-mono text-white placeholder-gray-600 focus:outline-none focus:border-[var(--hiho-glow-color)]"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2 rounded-lg font-mono text-xs font-bold tracking-wider transition-all disabled:opacity-30"
            style={{
              backgroundColor: "var(--hiho-glow-color, #00ff00)20",
              color: "var(--hiho-glow-color, #00ff00)",
              border: "1px solid var(--hiho-glow-color, #00ff00)40",
            }}
          >
            ASK
          </button>
        </div>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isAnima = message.role === "anima";
  return (
    <div className={`flex ${isAnima ? "justify-start" : "justify-end"}`}>
      <div
        className={`max-w-[85%] px-4 py-3 rounded-2xl text-sm font-mono ${
          isAnima
            ? "bg-white/5 border border-white/10 text-gray-300"
            : "bg-white/10 text-white"
        }`}
      >
        {isAnima && (
          <div className="text-[9px] text-gray-500 tracking-widest mb-1">
            ANIMA {message.tier ? `[${message.tier}]` : ""}
          </div>
        )}
        <p className={isAnima ? "italic leading-relaxed" : "leading-relaxed"}>
          {message.text}
        </p>
        {message.sources && message.sources.length > 0 && message.sources[0] !== "template" && (
          <div className="mt-2 text-[9px] text-gray-600">
            Sources: {message.sources.join(", ")}
          </div>
        )}
      </div>
    </div>
  );
}
