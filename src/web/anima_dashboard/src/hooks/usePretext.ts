"use client";

/**
 * Pretext hook for DOM-free text measurement in the Genesis narration overlay.
 *
 * Uses @chenglou/pretext to compute text height and line count without triggering
 * DOM reflow. This enables precise cinematic narration positioning over the 3D
 * canvas without layout thrashing.
 *
 * Triune mapping: The Doer (embodied rendering) in the Space fabric
 * Physics analog: geometry without coordinate dependence = Riemannian metric
 *
 * Attribution: Cheng Lou (@chenglou), https://github.com/chenglou/pretext (MIT)
 */

import { useMemo, useRef, useEffect, useState } from "react";

// Dynamic import to handle SSR (pretext needs Canvas API)
let pretextModule: typeof import("@chenglou/pretext") | null = null;

interface PretextLayout {
  /** Computed height in pixels */
  height: number;
  /** Number of lines the text wraps to */
  lineCount: number;
  /** Whether measurement is ready */
  ready: boolean;
}

/**
 * Measure text layout without DOM reflow.
 *
 * @param text - The text to measure
 * @param font - CSS font string (e.g., "16px monospace")
 * @param maxWidth - Maximum width for wrapping (pixels)
 * @param lineHeight - Line height multiplier (default 1.6 for cinematic)
 */
export function usePretext(
  text: string | null,
  font: string = "16px monospace",
  maxWidth: number = 600,
  lineHeight: number = 1.6
): PretextLayout {
  const [ready, setReady] = useState(false);
  const preparedRef = useRef<unknown>(null);

  // Load pretext module on mount (client-side only)
  useEffect(() => {
    if (typeof window === "undefined") return;

    import("@chenglou/pretext")
      .then((mod) => {
        pretextModule = mod;
        setReady(true);
      })
      .catch(() => {
        // Pretext not available — fall back to estimates
        setReady(false);
      });
  }, []);

  return useMemo(() => {
    if (!text || !ready || !pretextModule) {
      return { height: 0, lineCount: 0, ready: false };
    }

    try {
      // prepare() does one-time work: normalize, segment, measure via Canvas
      const prepared = pretextModule.prepare(text, font);
      preparedRef.current = prepared;

      // layout() returns height + line count via pure arithmetic (no DOM)
      const fontSize = parseFloat(font) || 16;
      const result = pretextModule.layout(prepared, maxWidth, fontSize * lineHeight);

      return {
        height: result.height,
        lineCount: result.lineCount,
        ready: true,
      };
    } catch {
      // Fallback: estimate based on character count
      const fontSize = parseFloat(font) || 16;
      const charsPerLine = Math.floor(maxWidth / (fontSize * 0.6));
      const estimatedLines = Math.ceil((text.length || 1) / charsPerLine);
      return {
        height: estimatedLines * fontSize * lineHeight,
        lineCount: estimatedLines,
        ready: false,
      };
    }
  }, [text, font, maxWidth, lineHeight, ready]);
}
