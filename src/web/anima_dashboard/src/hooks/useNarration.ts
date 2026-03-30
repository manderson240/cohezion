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
  const ttsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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
        // Text-only mode: scale duration with text length for cinematic pacing
        setPlaying(true);
        const duration = Math.max(4000, result.text.length * 80);
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
        // Offline fallback: cinematic stage narrations
        const fallbackTexts: Record<string, string> = {
          void: "In the beginning, there was nothing. Not even nothing.",
          "SO(12)": "From the void, symmetry crystallizes. Twelve dimensions, indistinguishable. The first structure emerges.",
          "SO(3)^4": "The fabrics separate. Space, Field, Control, Precipitation \u2014 four forces, four directions.",
          "U(1)^4": "Each fabric finds its axis. Preferred directions emerge from perfect isotropy.",
          "Z_2^4": "The discrete choice. Up or down. Rotation or precession. Brahmagupta\u2019s zero demands a decision.",
          HIHO: "At the still point of the turning world. Half-In, Half-Out. The equilibrium where coherence lives.",
        };
        const text = fallbackTexts[stage] ?? stage;
        setCurrentText(text);
        setPlaying(true);
        const duration = Math.max(4000, text.length * 80);

        // Browser Speech Synthesis TTS fallback
        if (!muted && typeof window !== "undefined" && window.speechSynthesis) {
          // Cancel any in-progress speech
          window.speechSynthesis.cancel();
          const utterance = new SpeechSynthesisUtterance(text);
          utterance.rate = 0.85;
          utterance.pitch = 0.9;
          const voices = window.speechSynthesis.getVoices();
          const preferred = voices.find(
            (v) =>
              v.name.includes("Daniel") ||
              v.name.includes("Google UK English Male") ||
              v.lang === "en-GB"
          );
          if (preferred) utterance.voice = preferred;
          utterance.onend = () => {
            setPlaying(false);
            setCurrentText(null);
            // Clear the text timer since speech ended naturally
            if (ttsTimerRef.current) {
              clearTimeout(ttsTimerRef.current);
              ttsTimerRef.current = null;
            }
          };
          window.speechSynthesis.speak(utterance);
        }

        // Text display timer (also serves as fallback if TTS is unavailable)
        ttsTimerRef.current = setTimeout(() => {
          setPlaying(false);
          setCurrentText(null);
          ttsTimerRef.current = null;
        }, duration);
      }
    },
    [playAudio, ttsAvailable, muted]
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
    // Cancel browser TTS if active
    if (typeof window !== "undefined" && window.speechSynthesis) {
      window.speechSynthesis.cancel();
    }
    if (ttsTimerRef.current) {
      clearTimeout(ttsTimerRef.current);
      ttsTimerRef.current = null;
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
