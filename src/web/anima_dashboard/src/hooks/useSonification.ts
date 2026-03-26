"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import * as Tone from "tone";

/**
 * Physics-to-audio mapping for the Genesis Engine.
 *
 * Each physics quantity maps to a specific audio parameter:
 * - Coherence → pitch (HIHO=C4, deviation=detuning)
 * - Entropy → texture (low=pure sine, high=noise)
 * - Temperature → amplitude (hot=loud, cold=quiet)
 * - SPIN rotation → stereo pan (left/right)
 * - SPIN precession → tremolo rate
 * - Gauge curvature → reverb depth
 * - Phase transitions → percussion impacts
 *
 * Inspired by:
 * - Brian Eno, "Music for Airports" (void drone)
 * - Steve Reich, "Music for 18 Musicians" (phasing/precession)
 * - Ligeti, "Atmosphères" (symmetry breaking)
 * - Ryoji Ikeda, "datamatics" (data sonification)
 */

export interface PhysicsState {
  coherence: number; // [0, 1]
  entropy: number; // [0, ∞) typically [0, 3]
  temperature: number; // [0, 200]
  spinRotation: number; // [-1, 1] ⟨σ_x⟩
  spinPrecession: number; // [-1, 1] ⟨σ_y⟩
  chargPolarity: number; // [-1, 1] ⟨σ_z⟩
  gaugeCurvature: number; // [0, ∞) Yang-Mills action
  symmetry: string; // current symmetry group
}

interface SonificationControls {
  /** Whether audio is currently playing */
  playing: boolean;
  /** Master volume [0, 1] */
  volume: number;
  /** Start the sonification engine */
  start: () => Promise<void>;
  /** Stop all audio */
  stop: () => void;
  /** Update physics state → audio parameters */
  update: (state: PhysicsState) => void;
  /** Set master volume */
  setVolume: (v: number) => void;
  /** Trigger a phase transition impact sound */
  triggerTransition: (fromSym: string, toSym: string) => void;
}

// Map coherence [0,1] to MIDI note. HIHO (0.5) = C4 (60)
function coherenceToFreq(coherence: number): number {
  // C4 = 261.63 Hz at HIHO (0.5)
  // Detuning: ±1 octave for full range
  const semitones = (coherence - 0.5) * 24; // ±12 semitones
  return 261.63 * Math.pow(2, semitones / 12);
}

// Map entropy to noise mix [0, 1]
function entropyToNoiseMix(entropy: number): number {
  return Math.min(entropy / 3.0, 1.0);
}

// Map temperature to amplitude [0, 0.3]
function temperatureToAmplitude(temperature: number): number {
  // Hot = louder, cold = quieter (but never silent)
  const normalized = Math.min(temperature / 100, 1.0);
  return 0.02 + normalized * 0.15;
}

export function useSonification(): SonificationControls {
  const [playing, setPlaying] = useState(false);
  const [volume, setVolumeState] = useState(0.5);

  // Audio nodes (refs to persist across renders)
  const synthRef = useRef<Tone.Synth | null>(null);
  const noiseRef = useRef<Tone.Noise | null>(null);
  const pannerRef = useRef<Tone.Panner | null>(null);
  const reverbRef = useRef<Tone.Reverb | null>(null);
  const gainRef = useRef<Tone.Gain | null>(null);
  const tremoloRef = useRef<Tone.Tremolo | null>(null);
  const impactSynthRef = useRef<Tone.MembraneSynth | null>(null);
  const initializedRef = useRef(false);

  // Initialize audio graph
  const initAudio = useCallback(() => {
    if (initializedRef.current) return;

    // Master gain
    const gain = new Tone.Gain(0.5).toDestination();
    gainRef.current = gain;

    // Reverb (gauge curvature → depth)
    const reverb = new Tone.Reverb({ decay: 2, wet: 0.1 }).connect(gain);
    reverbRef.current = reverb;

    // Panner (SPIN rotation → stereo)
    const panner = new Tone.Panner(0).connect(reverb);
    pannerRef.current = panner;

    // Tremolo (SPIN precession → rate)
    const tremolo = new Tone.Tremolo({ frequency: 2, depth: 0.3 })
      .connect(panner)
      .start();
    tremoloRef.current = tremolo;

    // Main synth (coherence → pitch, continuous tone)
    const synth = new Tone.Synth({
      oscillator: { type: "sine" },
      envelope: { attack: 0.5, decay: 0.2, sustain: 0.8, release: 1.0 },
    }).connect(tremolo);
    synthRef.current = synth;

    // Noise (entropy → texture)
    const noise = new Tone.Noise({ type: "pink", volume: -30 }).connect(panner);
    noiseRef.current = noise;

    // Impact synth for phase transitions
    const impact = new Tone.MembraneSynth({
      pitchDecay: 0.05,
      octaves: 6,
      envelope: { attack: 0.001, decay: 0.4, sustain: 0, release: 0.4 },
    }).connect(gain);
    impactSynthRef.current = impact;

    initializedRef.current = true;
  }, []);

  const start = useCallback(async () => {
    await Tone.start(); // Required: user gesture to start AudioContext
    initAudio();

    if (synthRef.current && !playing) {
      synthRef.current.triggerAttack(261.63); // Start at C4 (HIHO)
      noiseRef.current?.start();
      setPlaying(true);
    }
  }, [initAudio, playing]);

  const stop = useCallback(() => {
    synthRef.current?.triggerRelease();
    noiseRef.current?.stop();
    setPlaying(false);
  }, []);

  const update = useCallback((state: PhysicsState) => {
    if (!playing || !synthRef.current) return;

    // Coherence → pitch
    const freq = coherenceToFreq(state.coherence);
    synthRef.current.frequency.rampTo(freq, 0.1);

    // Entropy → noise level
    const noiseMix = entropyToNoiseMix(state.entropy);
    if (noiseRef.current) {
      noiseRef.current.volume.rampTo(-30 + noiseMix * 20, 0.1);
    }

    // Temperature → amplitude
    const amp = temperatureToAmplitude(state.temperature);
    if (gainRef.current) {
      gainRef.current.gain.rampTo(amp * volume, 0.1);
    }

    // SPIN rotation → stereo pan [-1, 1]
    if (pannerRef.current) {
      pannerRef.current.pan.rampTo(state.spinRotation, 0.1);
    }

    // SPIN precession → tremolo rate [0.5, 10]
    if (tremoloRef.current) {
      const rate = 0.5 + Math.abs(state.spinPrecession) * 9.5;
      tremoloRef.current.frequency.rampTo(rate, 0.1);
    }

    // Gauge curvature → reverb wet [0, 0.8]
    if (reverbRef.current) {
      const wet = Math.min(state.gaugeCurvature * 0.2, 0.8);
      reverbRef.current.wet.rampTo(wet, 0.3);
    }
  }, [playing, volume]);

  const setVolume = useCallback((v: number) => {
    setVolumeState(v);
    if (gainRef.current) {
      gainRef.current.gain.rampTo(v * 0.3, 0.1);
    }
  }, []);

  const triggerTransition = useCallback((fromSym: string, toSym: string) => {
    if (!impactSynthRef.current) {
      initAudio();
    }

    // Different impact sounds per transition stage
    const pitchMap: Record<string, string> = {
      "SO(12)": "C2",
      "SO(3)^4": "E2",
      "U(1)^4": "G2",
      "Z_2^4": "B2",
      "HIHO": "C3",
    };

    const note = pitchMap[toSym] ?? "C2";
    impactSynthRef.current?.triggerAttackRelease(note, "8n");
  }, [initAudio]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      synthRef.current?.dispose();
      noiseRef.current?.dispose();
      pannerRef.current?.dispose();
      reverbRef.current?.dispose();
      gainRef.current?.dispose();
      tremoloRef.current?.dispose();
      impactSynthRef.current?.dispose();
    };
  }, []);

  return { playing, volume, start, stop, update, setVolume, triggerTransition };
}
