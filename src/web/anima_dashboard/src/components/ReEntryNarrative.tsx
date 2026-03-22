"use client";

import { useState, useEffect, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

/**
 * Re-Entry Narrative (FR13).
 * Fetches history summary on mount and displays Anima's first-person
 * narration of what happened while the user was away.
 * Fades out after 10 seconds or on click.
 */
export default function ReEntryNarrative() {
  const [narrative, setNarrative] = useState<string | null>(null);
  const [displayText, setDisplayText] = useState("");
  const [visible, setVisible] = useState(true);
  const [fading, setFading] = useState(false);
  const fetchedRef = useRef(false);

  useEffect(() => {
    if (fetchedRef.current) return;
    fetchedRef.current = true;

    fetch(`${API_BASE}/api/universe/history/summary`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data?.narrative && data.ticks_elapsed > 0) {
          setNarrative(data.narrative);
        }
      })
      .catch(() => {});
  }, []);

  // Typewriter animation
  useEffect(() => {
    if (!narrative) return;
    let i = 0;
    const timer = setInterval(() => {
      i++;
      setDisplayText(narrative.slice(0, i));
      if (i >= narrative.length) clearInterval(timer);
    }, 15);
    return () => clearInterval(timer);
  }, [narrative]);

  // Auto-fade after 10 seconds
  useEffect(() => {
    if (!narrative) return;
    const timer = setTimeout(() => {
      setFading(true);
      setTimeout(() => setVisible(false), 1000);
    }, 10000);
    return () => clearTimeout(timer);
  }, [narrative]);

  if (!narrative || !visible) return null;

  return (
    <div
      onClick={() => {
        setFading(true);
        setTimeout(() => setVisible(false), 500);
      }}
      className={`fixed inset-x-0 top-20 z-40 flex justify-center pointer-events-auto transition-opacity duration-1000 ${
        fading ? "opacity-0" : "opacity-100"
      }`}
    >
      <div
        className="max-w-2xl mx-6 p-5 bg-black/90 backdrop-blur-xl rounded-2xl border font-mono text-sm text-gray-300 leading-relaxed cursor-pointer shadow-2xl"
        style={{ borderColor: "var(--hiho-glow-color, #00ff00)40" }}
      >
        <div className="text-[10px] tracking-widest text-gray-500 mb-2">
          ANIMA — RE-ENTRY NARRATIVE
        </div>
        <p className="italic">
          {displayText}
          <span className="animate-pulse">_</span>
        </p>
        <div className="text-[9px] text-gray-600 mt-3">Click to dismiss</div>
      </div>
    </div>
  );
}
