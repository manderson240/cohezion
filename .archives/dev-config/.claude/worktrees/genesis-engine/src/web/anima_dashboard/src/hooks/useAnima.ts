"use client";

import { useState, useEffect, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface AnimaStatus {
  tier: string;
  online: boolean;
  mcp_available: boolean;
  voice_available: boolean;
}

export interface ChatMessage {
  role: "user" | "anima";
  text: string;
  tier?: string;
  sources?: string[];
  timestamp: number;
}

export function useAnima() {
  const [status, setStatus] = useState<AnimaStatus | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch status on mount
  useEffect(() => {
    fetch(`${API_BASE}/api/anima/status`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => data && setStatus(data))
      .catch(() => {});
  }, []);

  const ask = useCallback(async (question: string) => {
    setMessages((prev) => [
      ...prev,
      { role: "user", text: question, timestamp: Date.now() },
    ]);
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/anima/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      if (resp.ok) {
        const data = await resp.json();
        setMessages((prev) => [
          ...prev,
          {
            role: "anima",
            text: data.answer,
            tier: data.tier,
            sources: data.sources,
            timestamp: Date.now(),
          },
        ]);
      }
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "anima",
          text: "Connection lost. Anima is in template mode.",
          tier: "template",
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  const narrate = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${API_BASE}/api/anima/narrate`, {
        method: "POST",
      });
      if (resp.ok) {
        const data = await resp.json();
        setMessages((prev) => [
          ...prev,
          {
            role: "anima",
            text: data.text,
            tier: data.tier,
            timestamp: Date.now(),
          },
        ]);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  return { status, messages, loading, ask, narrate };
}
