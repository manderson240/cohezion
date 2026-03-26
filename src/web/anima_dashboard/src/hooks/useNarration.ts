"use client";

import { useState, useCallback, useRef } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8080";

interface NarrationResult {
  text: string;
  audio_path: string | null;
  cached: boolean;
  voice: string;
  fallback?: boolean;
}

interface NarrationControls {
  /** Whether narration is currently playing */
  playing: boolean;
  /** Current narration text being played */
  currentText: string | null;
  /** Whether TTS is available on the backend */
  ttsAvailable: boolean | null;
  /** Narrate a cosmogony stage */
  narrateStage: (stage: string) => Promise<void>;
  /** Narrate a physics concept */
  narrateConcept: (concept: string) => Promise<void>;
  /** Narrate arbitrary text */
  narrateCustom: (text: string) => Promise<void>;
  /** Stop current narration */
  stop: () => void;
  /** Mute/unmute */
  muted: boolean;
  setMuted: (m: boolean) => void;
}

export function useNarration(): NarrationControls {
  const [playing, setPlaying] = useState(false);
  const [currentText, setCurrentText] = useState<string | null>(null);
  const [ttsAvailable, setTtsAvailable] = useState<boolean | null>(null);
  const [muted, setMuted] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const queueRef = useRef<string[]>([]);

  const playAudio = useCallback(
    async (result: NarrationResult) => {
      setCurrentText(result.text);

      if (result.audio_path && !muted) {
        // Play the audio file
        const audio = new Audio(`${API_BASE}/${result.audio_path}`);
        audioRef.current = audio;
        setPlaying(true);

        audio.onended = () => {
          setPlaying(false);
          setCurrentText(null);
          // Process queue
          if (queueRef.current.length > 0) {
            const next = queueRef.current.shift();
            if (next) narrateCustom(next);
          }
        };

        audio.onerror = () => {
          setPlaying(false);
          setCurrentText(null);
        };

        await audio.play().catch(() => {
          setPlaying(false);
        });
      } else {
        // Text-only mode: show for 3 seconds per sentence
        setPlaying(true);
        const duration = Math.max(3000, result.text.length * 50);
        setTimeout(() => {
          setPlaying(false);
          setCurrentText(null);
        }, duration);
      }
    },
    [muted]
  );

  const narrateStage = useCallback(
    async (stage: string) => {
      try {
        const resp = await fetch(`${API_BASE}/api/genesis/narration/stage/${stage}`, {
          method: "POST",
        });
        if (resp.ok) {
          const result: NarrationResult = await resp.json();
          if (ttsAvailable === null) setTtsAvailable(!result.fallback);
          await playAudio(result);
        }
      } catch {
        // Offline fallback: display stage text
        const fallbackTexts: Record<string, string> = {
          void: "In the beginning, there was nothing.",
          "SO(12)": "Symmetry crystallized. Twelve dimensions.",
          "SO(3)^4": "The fabrics separated.",
          "U(1)^4": "Preferred directions emerged.",
          "Z_2^4": "The discrete choice. Up or down.",
          HIHO: "At the still point, the dance began.",
        };
        setCurrentText(fallbackTexts[stage] ?? stage);
        setPlaying(true);
        setTimeout(() => {
          setPlaying(false);
          setCurrentText(null);
        }, 4000);
      }
    },
    [playAudio, ttsAvailable]
  );

  const narrateConcept = useCallback(
    async (concept: string) => {
      try {
        const resp = await fetch(
          `${API_BASE}/api/genesis/narration/concept/${concept}`,
          { method: "POST" }
        );
        if (resp.ok) {
          const result: NarrationResult = await resp.json();
          await playAudio(result);
        }
      } catch {
        setCurrentText(`Explaining: ${concept}`);
        setTimeout(() => setCurrentText(null), 3000);
      }
    },
    [playAudio]
  );

  const narrateCustom = useCallback(
    async (text: string) => {
      if (playing) {
        // Queue if already playing
        queueRef.current.push(text);
        return;
      }
      try {
        const resp = await fetch(`${API_BASE}/api/genesis/narration/custom`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text }),
        });
        if (resp.ok) {
          const result: NarrationResult = await resp.json();
          await playAudio(result);
        }
      } catch {
        setCurrentText(text);
        setTimeout(() => setCurrentText(null), 3000);
      }
    },
    [playing, playAudio]
  );

  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
    queueRef.current = [];
    setPlaying(false);
    setCurrentText(null);
  }, []);

  return {
    playing,
    currentText,
    ttsAvailable,
    narrateStage,
    narrateConcept,
    narrateCustom,
    stop,
    muted,
    setMuted,
  };
}
