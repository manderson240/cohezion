"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import * as Tone from "tone";

/**
 * Physics-to-audio mapping for the Genesis Engine.
 *
 * Each physics quantity maps to a specific audio parameter:
 * - Coherence -> pitch (HIHO=C4, deviation=detuning)
 * - Entropy -> texture (low=pure sine, high=noise)
 * - Temperature -> amplitude (hot=loud, cold=quiet)
 * - SPIN rotation -> stereo pan (left/right)
 * - SPIN precession -> tremolo rate
 * - Gauge curvature -> reverb depth
 * - Phase transitions -> percussion impacts
 *
 * Cinematic additions (Part 5):
 * - Void drone: quiet sine wave at C2 (-40dB)
 * - Explosion impact: MembraneSynth hit + rising sweep C2->C4
 * - Fabric chord: Em7 spread (E3, G3, B3, D4) from unison
 * - Settling pad: warm sustained chord resolving to final state
 *
 * Inspired by:
 * - Brian Eno, "Music for Airports" (void drone)
 * - Steve Reich, "Music for 18 Musicians" (phasing/precession)
 * - Ligeti, "Atmospheres" (symmetry breaking)
 * - Ryoji Ikeda, "datamatics" (data sonification)
 */

export interface PhysicsState {
  coherence: number; // [0, 1]
  entropy: number; // [0, inf) typically [0, 3]
  temperature: number; // [0, 200]
  spinRotation: number; // [-1, 1] <sigma_x>
  spinPrecession: number; // [-1, 1] <sigma_y>
  chargPolarity: number; // [-1, 1] <sigma_z>
  gaugeCurvature: number; // [0, inf) Yang-Mills action
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
  /** Update physics state -> audio parameters */
  update: (state: PhysicsState) => void;
  /** Set master volume */
  setVolume: (v: number) => void;
  /** Trigger a phase transition impact sound */
  triggerTransition: (fromSym: string, toSym: string) => void;
  /** Start the void drone (quiet C2 sine, -40dB) */
  startVoidDrone: () => Promise<void>;
  /** Stop the void drone */
  stopVoidDrone: () => void;
  /** Trigger the explosion impact + rising sweep */
  triggerExplosion: () => void;
  /** Start 4 fabric oscillators spreading from unison to Em7 */
  startFabricChord: () => void;
  /** Resolve to warm sustained pad */
  settleToSustainedPad: () => void;
}

// Map coherence [0,1] to MIDI note. HIHO (0.5) = C4 (60)
function coherenceToFreq(coherence: number): number {
  // C4 = 261.63 Hz at HIHO (0.5)
  // Detuning: +/-1 octave for full range
  const semitones = (coherence - 0.5) * 24; // +/-12 semitones
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

// Note name to frequency
function noteToFreq(note: string): number {
  const map: Record<string, number> = {
    C1: 32.7,
    C2: 65.41,
    E3: 164.81,
    G3: 196.0,
    B3: 246.94,
    D4: 293.66,
    C4: 261.63,
  };
  return map[note] ?? 261.63;
}

export function useSonification(): SonificationControls {
  const [playing, setPlaying] = useState(false);
  const [volume, setVolumeState] = useState(0.3);

  // Audio nodes (refs to persist across renders)
  const synthRef = useRef<Tone.Synth | null>(null);
  const noiseRef = useRef<Tone.Noise | null>(null);
  const pannerRef = useRef<Tone.Panner | null>(null);
  const reverbRef = useRef<Tone.Reverb | null>(null);
  const gainRef = useRef<Tone.Gain | null>(null);
  const tremoloRef = useRef<Tone.Tremolo | null>(null);
  const impactSynthRef = useRef<Tone.MembraneSynth | null>(null);
  const initializedRef = useRef(false);

  // Cinematic audio nodes
  const voidDroneRef = useRef<Tone.Synth | null>(null);
  const voidDroneGainRef = useRef<Tone.Gain | null>(null);
  const sweepSynthRef = useRef<Tone.Synth | null>(null);
  const fabricSynthsRef = useRef<Tone.Synth[]>([]);
  const fabricGainRef = useRef<Tone.Gain | null>(null);

  // Initialize audio graph
  const initAudio = useCallback(() => {
    if (initializedRef.current) return;

    // Master gain
    const gain = new Tone.Gain(0.15).toDestination();
    gainRef.current = gain;

    // Reverb (gauge curvature -> depth)
    const reverb = new Tone.Reverb({ decay: 2, wet: 0.1 }).connect(gain);
    reverbRef.current = reverb;

    // Panner (SPIN rotation -> stereo)
    const panner = new Tone.Panner(0).connect(reverb);
    pannerRef.current = panner;

    // Tremolo (SPIN precession -> rate)
    const tremolo = new Tone.Tremolo({ frequency: 2, depth: 0.3 })
      .connect(panner)
      .start();
    tremoloRef.current = tremolo;

    // Main synth (coherence -> pitch, continuous tone)
    const synth = new Tone.Synth({
      oscillator: { type: "sine" },
      envelope: { attack: 1.5, decay: 0.5, sustain: 0.6, release: 2.0 },
    }).connect(tremolo);
    synthRef.current = synth;

    // Noise (entropy -> texture)
    const noise = new Tone.Noise({ type: "pink", volume: -40 }).connect(
      panner
    );
    noiseRef.current = noise;

    // Impact synth for phase transitions
    const impact = new Tone.MembraneSynth({
      pitchDecay: 0.05,
      octaves: 6,
      envelope: { attack: 0.001, decay: 0.4, sustain: 0, release: 0.4 },
    }).connect(gain);
    impactSynthRef.current = impact;

    // --- Cinematic nodes ---

    // Void drone: very quiet sine at C2
    const voidDroneGain = new Tone.Gain(0).connect(gain);
    voidDroneGainRef.current = voidDroneGain;
    const voidDrone = new Tone.Synth({
      oscillator: { type: "sine" },
      envelope: { attack: 2.0, decay: 0.5, sustain: 1.0, release: 3.0 },
    }).connect(voidDroneGain);
    voidDroneRef.current = voidDrone;

    // Sweep synth for explosion rising glissando
    const sweep = new Tone.Synth({
      oscillator: { type: "triangle" },
      envelope: { attack: 0.3, decay: 0.2, sustain: 0.6, release: 2.0 },
    }).connect(gain);
    sweepSynthRef.current = sweep;

    // Fabric chord: 4 oscillators, one per fabric
    const fabricGain = new Tone.Gain(0).connect(gain);
    fabricGainRef.current = fabricGain;
    const fabricSynths: Tone.Synth[] = [];
    for (let i = 0; i < 4; i++) {
      const s = new Tone.Synth({
        oscillator: { type: "triangle" },
        envelope: { attack: 1.0, decay: 0.3, sustain: 0.9, release: 2.0 },
      }).connect(fabricGain);
      fabricSynths.push(s);
    }
    fabricSynthsRef.current = fabricSynths;

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
    voidDroneRef.current?.triggerRelease();
    sweepSynthRef.current?.triggerRelease();
    fabricSynthsRef.current.forEach((s) => s.triggerRelease());
    setPlaying(false);
  }, []);

  const update = useCallback(
    (state: PhysicsState) => {
      if (!playing || !synthRef.current) return;

      // Coherence -> pitch
      const freq = coherenceToFreq(state.coherence);
      synthRef.current.frequency.rampTo(freq, 0.1);

      // Entropy -> noise level
      const noiseMix = entropyToNoiseMix(state.entropy);
      if (noiseRef.current) {
        noiseRef.current.volume.rampTo(-30 + noiseMix * 20, 0.1);
      }

      // Temperature -> amplitude
      const amp = temperatureToAmplitude(state.temperature);
      if (gainRef.current) {
        gainRef.current.gain.rampTo(amp * volume, 0.1);
      }

      // SPIN rotation -> stereo pan [-1, 1]
      if (pannerRef.current) {
        pannerRef.current.pan.rampTo(state.spinRotation, 0.1);
      }

      // SPIN precession -> tremolo rate [0.5, 10]
      if (tremoloRef.current) {
        const rate = 0.5 + Math.abs(state.spinPrecession) * 9.5;
        tremoloRef.current.frequency.rampTo(rate, 0.1);
      }

      // Gauge curvature -> reverb wet [0, 0.8]
      if (reverbRef.current) {
        const wet = Math.min(state.gaugeCurvature * 0.2, 0.8);
        reverbRef.current.wet.rampTo(wet, 0.3);
      }
    },
    [playing, volume]
  );

  const setVolume = useCallback((v: number) => {
    setVolumeState(v);
    if (gainRef.current) {
      gainRef.current.gain.rampTo(v * 0.3, 0.1);
    }
  }, []);

  const triggerTransition = useCallback(
    (fromSym: string, toSym: string) => {
      if (!impactSynthRef.current) {
        initAudio();
      }

      // Different impact sounds per transition stage
      const pitchMap: Record<string, string> = {
        "SO(12)": "C2",
        "SO(3)^4": "E2",
        "U(1)^4": "G2",
        "Z_2^4": "B2",
        HIHO: "C3",
      };

      const note = pitchMap[toSym] ?? "C2";
      impactSynthRef.current?.triggerAttackRelease(note, "8n");
    },
    [initAudio]
  );

  // --- Cinematic: Void drone ---
  const startVoidDrone = useCallback(async () => {
    try {
      await Tone.start();
      initAudio();

      if (voidDroneRef.current && voidDroneGainRef.current) {
        // -40dB is ~ 0.01 gain
        voidDroneGainRef.current.gain.rampTo(0.01, 0.5);
        // Schedule slightly in the future to avoid "start time" race
        const now = Tone.now();
        voidDroneRef.current.triggerAttack(noteToFreq("C2"), now + 0.1);
      }
    } catch {
      // AudioContext not ready yet (no user gesture) — silently skip
    }
  }, [initAudio]);

  const stopVoidDrone = useCallback(() => {
    if (voidDroneRef.current) {
      voidDroneRef.current.triggerRelease();
    }
    if (voidDroneGainRef.current) {
      voidDroneGainRef.current.gain.rampTo(0, 2.0);
    }
  }, []);

  // --- Cinematic: Explosion impact + rising sweep ---
  const triggerExplosion = useCallback(() => {
    initAudio();

    // Impact hit: C1 on MembraneSynth
    impactSynthRef.current?.triggerAttackRelease("C1", "4n");

    // Rising sweep: C2 -> C4 over 2 seconds
    if (sweepSynthRef.current) {
      sweepSynthRef.current.triggerAttack(noteToFreq("C2"));
      sweepSynthRef.current.frequency.rampTo(noteToFreq("C4"), 2.0);
      // Release after the sweep
      setTimeout(() => {
        sweepSynthRef.current?.triggerRelease();
      }, 2200);
    }

    // Fade out void drone
    stopVoidDrone();
  }, [initAudio, stopVoidDrone]);

  // --- Cinematic: Fabric chord (Em7: E3, G3, B3, D4) ---
  const startFabricChord = useCallback(() => {
    initAudio();

    const targetNotes = ["E3", "G3", "B3", "D4"];
    const startFreq = noteToFreq("E3"); // All start at unison E3

    if (fabricGainRef.current) {
      fabricGainRef.current.gain.rampTo(0.03, 1.0);
    }

    fabricSynthsRef.current.forEach((synth, i) => {
      // Start all at unison, then spread over 2 seconds
      synth.triggerAttack(startFreq);
      synth.frequency.rampTo(noteToFreq(targetNotes[i]), 2.0);
    });
  }, [initAudio]);

  // --- Cinematic: Settle to sustained pad ---
  const settleToSustainedPad = useCallback(() => {
    // Fabric chord is already playing; just lower volume and add warmth
    if (fabricGainRef.current) {
      fabricGainRef.current.gain.rampTo(0.02, 3.0);
    }

    // If tremolo is active, sync to gentle rate (HIHO coherence)
    if (tremoloRef.current) {
      tremoloRef.current.frequency.rampTo(1.5, 2.0);
      tremoloRef.current.depth.rampTo(0.15, 2.0);
    }

    // Increase reverb for warmth
    if (reverbRef.current) {
      reverbRef.current.wet.rampTo(0.4, 3.0);
    }
  }, []);

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
      voidDroneRef.current?.dispose();
      voidDroneGainRef.current?.dispose();
      sweepSynthRef.current?.dispose();
      fabricSynthsRef.current.forEach((s) => s.dispose());
      fabricGainRef.current?.dispose();
    };
  }, []);

  return {
    playing,
    volume,
    start,
    stop,
    update,
    setVolume,
    triggerTransition,
    startVoidDrone,
    stopVoidDrone,
    triggerExplosion,
    startFabricChord,
    settleToSustainedPad,
  };
}
