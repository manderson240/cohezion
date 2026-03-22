"use client";

import { useEffect } from "react";
import { useUniverse } from "@/context/UniverseProvider";

/**
 * Headless component that maps coherence to CSS custom properties.
 * Renders nothing — updates :root CSS variables every tick.
 *
 * Coherence zones:
 *   0.0-0.3  → CRITICAL_LOW (reds, fast pulse)
 *   0.3-0.45 → WARNING (golds, medium pulse)
 *   0.45-0.55 → STABLE (greens, calm — HIHO sweet spot)
 *   0.55-0.7  → WARNING (golds → blues)
 *   0.7-1.0  → CRITICAL_HIGH (deep blues, fast pulse)
 */
export default function HIHOBridge() {
  const { state } = useUniverse();
  const coherence = state?.coherence ?? 0.5;

  useEffect(() => {
    const root = document.documentElement;

    let hue: number;
    let glowColor: string;
    let pulseSpeed: string;
    let particleDensity: number;

    if (coherence < 0.3) {
      // CRITICAL LOW — red zone
      hue = 0;
      glowColor = "#FF3B3B";
      pulseSpeed = "2s";
      particleDensity = 0.8;
    } else if (coherence < 0.45) {
      // WARNING — gold zone
      hue = 45;
      glowColor = "#F6D365";
      pulseSpeed = "4s";
      particleDensity = 0.5;
    } else if (coherence <= 0.55) {
      // STABLE — green zone (HIHO sweet spot at 0.5)
      hue = 120;
      glowColor = "#00FF00";
      pulseSpeed = "8s";
      particleDensity = 0.3;
    } else if (coherence <= 0.7) {
      // WARNING — transitioning to blue
      hue = 200;
      glowColor = "#4facfe";
      pulseSpeed = "4s";
      particleDensity = 0.5;
    } else {
      // CRITICAL HIGH — deep blue/purple
      hue = 260;
      glowColor = "#0077BE";
      pulseSpeed = "2s";
      particleDensity = 0.8;
    }

    root.style.setProperty("--hiho-hue", String(hue));
    root.style.setProperty("--hiho-glow-color", glowColor);
    root.style.setProperty("--hiho-pulse-speed", pulseSpeed);
    root.style.setProperty("--hiho-particle-density", String(particleDensity));
  }, [coherence]);

  return null;
}
