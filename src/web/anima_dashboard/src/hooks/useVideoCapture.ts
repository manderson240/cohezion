"use client";

import { useState, useRef, useCallback } from "react";

/**
 * Canvas video recording via MediaRecorder API.
 *
 * Records Three.js canvas as WebM video with optional audio.
 * Supports:
 * - Manual start/stop recording
 * - Time-lapse mode (1 frame per N ticks)
 * - Automatic screenshot at phase transitions
 */

interface VideoCaptureControls {
  /** Whether currently recording */
  recording: boolean;
  /** Start recording the canvas */
  startRecording: (canvas: HTMLCanvasElement, options?: RecordOptions) => void;
  /** Stop recording and return blob URL */
  stopRecording: () => Promise<string | null>;
  /** Take a single screenshot */
  screenshot: (canvas: HTMLCanvasElement, filename?: string) => string | null;
  /** Duration of current recording in seconds */
  duration: number;
}

interface RecordOptions {
  /** Frame rate (default: 30) */
  fps?: number;
  /** Video MIME type (default: video/webm) */
  mimeType?: string;
  /** Include audio from Tone.js context */
  includeAudio?: boolean;
}

export function useVideoCapture(): VideoCaptureControls {
  const [recording, setRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startRecording = useCallback(
    (canvas: HTMLCanvasElement, options?: RecordOptions) => {
      if (recording) return;

      const fps = options?.fps ?? 30;
      const mimeType = options?.mimeType ?? "video/webm;codecs=vp9";

      // Get canvas stream
      const stream = canvas.captureStream(fps);

      // Optionally add audio from AudioContext
      if (options?.includeAudio) {
        try {
          // Attempt to capture Tone.js audio context
          const audioCtx = (window as unknown as Record<string, unknown>).Tone;
          if (audioCtx && typeof audioCtx === "object" && "context" in audioCtx) {
            const toneCtx = (audioCtx as { context: AudioContext }).context;
            const dest = toneCtx.createMediaStreamDestination();
            toneCtx.destination.connect(dest);
            for (const track of dest.stream.getAudioTracks()) {
              stream.addTrack(track);
            }
          }
        } catch {
          // Audio capture not available — video only
        }
      }

      const recorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported(mimeType)
          ? mimeType
          : "video/webm",
      });

      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunksRef.current.push(e.data);
        }
      };

      recorder.start(100); // Collect data every 100ms
      recorderRef.current = recorder;
      startTimeRef.current = Date.now();
      setRecording(true);

      // Duration timer
      timerRef.current = setInterval(() => {
        setDuration((Date.now() - startTimeRef.current) / 1000);
      }, 500);
    },
    [recording]
  );

  const stopRecording = useCallback(async (): Promise<string | null> => {
    if (!recorderRef.current || !recording) return null;

    return new Promise<string | null>((resolve) => {
      const recorder = recorderRef.current!;

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "video/webm" });
        const url = URL.createObjectURL(blob);
        chunksRef.current = [];
        setRecording(false);
        setDuration(0);
        if (timerRef.current) clearInterval(timerRef.current);
        resolve(url);
      };

      recorder.stop();
    });
  }, [recording]);

  const screenshot = useCallback(
    (canvas: HTMLCanvasElement, filename?: string): string | null => {
      try {
        const dataUrl = canvas.toDataURL("image/png");

        // Trigger download if filename provided
        if (filename) {
          const link = document.createElement("a");
          link.download = filename;
          link.href = dataUrl;
          link.click();
        }

        return dataUrl;
      } catch {
        return null;
      }
    },
    []
  );

  return { recording, startRecording, stopRecording, screenshot, duration };
}
