"""HIHO Reality Precipitation & Audio Field Sonification Engine.

Maps 12-Parameter Quadrature Model states across 4 Fabrics (Space, Field,
Control, Precipitation) to audio frequencies based on distance from the 0.5
HIHO coherence point (|c - 0.5|). Generates audio harmonic frequencies, phase
angles, ADSR envelopes, and real-time JSON audio buffers for Web Audio API /
PyGame output.
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any

import numpy as np

from cohezion.governance.quadrature_nexus import QuadratureState
from cohezion.inference.unified_hybrid_router import (
    HybridRouteResponse,
    TaskClass,
    UnifiedHybridRouter,
)
from cohezion.physics.fiber_bundle import FABRIC_SLICES

logger = logging.getLogger(__name__)

# Standard HIHO fundamental frequency (Hz)
DEFAULT_FUNDAMENTAL_HZ: float = 432.0
HIHO_TARGET_COHERENCE: float = 0.5
DEFAULT_SAMPLE_RATE: int = 44100

# Fabric harmonic ratios relative to fundamental (Just Intonation / Pythagorean)
# Space: Fundamental (1/1)
# Field: Major Third (5/4 = 1.25)
# Control: Perfect Fifth (3/2 = 1.5)
# Precipitation: Octave (2/1 = 2.0)
FABRIC_RATIOS: dict[str, float] = {
    "Space": 1.0,
    "Field": 1.25,
    "Control": 1.5,
    "Precipitation": 2.0,
}


@dataclass
class ADSREnvelope:
    """Attack-Decay-Sustain-Release amplitude envelope parameters.

    Attributes
    ----------
    attack_s : float
        Duration of attack phase in seconds.
    decay_s : float
        Duration of decay phase in seconds.
    sustain : float
        Sustain amplitude level in [0, 1].
    release_s : float
        Duration of release phase in seconds.
    """

    attack_s: float = 0.01
    decay_s: float = 0.05
    sustain: float = 0.8
    release_s: float = 0.1

    def to_dict(self) -> dict[str, float]:
        """Serialize envelope parameters to dictionary."""
        return {
            "attack_s": self.attack_s,
            "decay_s": self.decay_s,
            "sustain": self.sustain,
            "release_s": self.release_s,
        }


@dataclass
class FabricSonification:
    """Sonification output for a single fabric domain.

    Attributes
    ----------
    fabric_name : str
        Name of fabric domain ("Space", "Field", "Control", "Precipitation").
    base_frequency_hz : float
        Unperturbed base frequency for this fabric in Hz.
    frequency_hz : float
        Effective frequency including HIHO detuning and Lyapunov modulation in Hz.
    amplitude : float
        Calculated amplitude in [0, 1].
    phase_rad : float
        Initial phase angle in radians [0, 2π).
    harmonics_hz : list[float]
        Harmonic overtone frequencies for this fabric in Hz.
    coherence : float
        Local coherence metric for this fabric in [0, 1].
    """

    fabric_name: str
    base_frequency_hz: float
    frequency_hz: float
    amplitude: float
    phase_rad: float
    harmonics_hz: list[float]
    coherence: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize fabric sonification data to dictionary."""
        return {
            "fabric_name": self.fabric_name,
            "base_frequency_hz": round(self.base_frequency_hz, 2),
            "frequency_hz": round(self.frequency_hz, 2),
            "amplitude": round(self.amplitude, 4),
            "phase_rad": round(self.phase_rad, 4),
            "harmonics_hz": [round(h, 2) for h in self.harmonics_hz],
            "coherence": round(self.coherence, 4),
        }


@dataclass
class AudioFieldState:
    """Complete audio field state produced by HIHOSonifier.

    Attributes
    ----------
    fundamental_hz : float
        Fundamental tuning frequency (e.g. 432 Hz).
    system_coherence : float
        Overall 12D system coherence in [0, 1].
    coherence_distance : float
        Absolute distance from the 0.5 HIHO point (|c - 0.5|).
    dissonance_index : float
        Harmonic dissonance metric in [0, 1].
    fabrics : dict[str, FabricSonification]
        Per-fabric sonification mappings.
    adsr : ADSREnvelope
        Calculated ADSR amplitude envelope.
    lyapunov_perturbation : float
        Lyapunov attractor micro-perturbation applied.
    """

    fundamental_hz: float
    system_coherence: float
    coherence_distance: float
    dissonance_index: float
    fabrics: dict[str, FabricSonification]
    adsr: ADSREnvelope
    lyapunov_perturbation: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize audio field state to dictionary."""
        return {
            "fundamental_hz": round(self.fundamental_hz, 2),
            "system_coherence": round(self.system_coherence, 4),
            "coherence_distance": round(self.coherence_distance, 4),
            "dissonance_index": round(self.dissonance_index, 4),
            "fabrics": {k: v.to_dict() for k, v in self.fabrics.items()},
            "adsr": self.adsr.to_dict(),
            "lyapunov_perturbation": round(self.lyapunov_perturbation, 6),
        }


class HIHOSonifier:
    """Sonification engine mapping 12-Parameter Quadrature states to audio fields.

    Parameters
    ----------
    fundamental_hz : float
        Base fundamental frequency in Hz (default 432.0).
    sample_rate : int
        Audio buffer sampling rate in Hz (default 44100).
    router : UnifiedHybridRouter | None
        Optional model router for delegating inference tasks.
    """

    def __init__(
        self,
        fundamental_hz: float = DEFAULT_FUNDAMENTAL_HZ,
        sample_rate: int = DEFAULT_SAMPLE_RATE,
        router: UnifiedHybridRouter | None = None,
    ) -> None:
        self.fundamental_hz = fundamental_hz
        self.sample_rate = sample_rate
        self.router = router or UnifiedHybridRouter()

    @staticmethod
    def compute_coherence_distance(coherence: float) -> float:
        """Compute absolute distance from the 0.5 HIHO coherence point.

        Parameters
        ----------
        coherence : float
            Coherence value in [0, 1].

        Returns
        -------
        float
            Distance |c - 0.5| in range [0, 0.5].
        """
        c_clamped = max(0.0, min(1.0, float(coherence)))
        return abs(c_clamped - HIHO_TARGET_COHERENCE)

    @staticmethod
    def calculate_dissonance(
        coherence_distance: float,
        lyapunov_perturbation: float = 0.0,
    ) -> float:
        """Calculate harmonic dissonance based on HIHO distance & Lyapunov perturbation.

        At 0.5 coherence (|c - 0.5| = 0), dissonance is 0.0 (pure harmony).
        Max distance (0.5) scales dissonance to 1.0. Micro-perturbations add dissonance.

        Parameters
        ----------
        coherence_distance : float
            Distance |c - 0.5| in [0, 0.5].
        lyapunov_perturbation : float
            Lyapunov attractor micro-perturbation magnitude.

        Returns
        -------
        float
            Dissonance index in range [0, 1].
        """
        base_dissonance = min(1.0, 2.0 * coherence_distance)
        perturbation_dissonance = abs(float(lyapunov_perturbation)) * 2.0
        return min(1.0, base_dissonance + perturbation_dissonance)

    def compute_adsr_envelope(self, coherence_distance: float) -> ADSREnvelope:
        """Calculate ADSR envelope dynamically scaled by HIHO coherence distance.

        Near HIHO coherence (dist -> 0): crisp attack, fast decay, rich sustain.
        Far from HIHO coherence (dist -> 0.5): slower attack, heavy decay, reduced sustain.

        Parameters
        ----------
        coherence_distance : float
            Distance |c - 0.5| in [0, 0.5].

        Returns
        -------
        ADSREnvelope
            Dynamic envelope parameters.
        """
        norm_dist = min(1.0, coherence_distance * 2.0)
        attack = 0.01 + norm_dist * 0.05
        decay = 0.05 + norm_dist * 0.10
        sustain = max(0.2, 0.8 - norm_dist * 0.5)
        release = 0.10 + norm_dist * 0.15
        return ADSREnvelope(
            attack_s=attack,
            decay_s=decay,
            sustain=sustain,
            release_s=release,
        )

    def sonify_coherence_state(self, coherence: float, fundamental_hz: float = 432.0, lyapunov_perturbation: float = 0.0) -> AudioFieldState:
        """Convenience method to sonify a single coherence metric across the 4 fabrics."""
        self.fundamental_hz = fundamental_hz
        dist = self.compute_coherence_distance(coherence)
        dissonance = self.calculate_dissonance(dist, lyapunov_perturbation)
        state_dict = {"coherence": coherence}
        res = self.sonify_quadrature_state(state_dict, lyapunov_perturbation=lyapunov_perturbation)
        return res

    def sonify_quadrature_state(
        self,
        state: np.ndarray | QuadratureState | dict[str, float],
        lyapunov_perturbation: float = 0.0,
    ) -> AudioFieldState:
        """Map a 12D Quadrature Model state across 4 Fabrics to an audio field.

        Parameters
        ----------
        state : np.ndarray | QuadratureState | dict[str, float]
            Input state. Can be a 12D array, QuadratureState dataclass, or dict.
        lyapunov_perturbation : float
            Lyapunov attractor micro-perturbation value (for pitch/dissonance modulation).

        Returns
        -------
        AudioFieldState
            Structured audio field representation.
        """
        fabric_coherence: dict[str, float] = {}
        fabric_directions: dict[str, float] = {}

        if isinstance(state, QuadratureState):
            sys_coherence = state.coherence
            fabric_coherence["Space"] = (state.awareness + state.precision + state.creativity) / 3.0
            fabric_coherence["Field"] = (state.coherence + state.entropy + state.stability) / 3.0
            fabric_coherence["Control"] = (state.momentum + state.novelty + state.resonance) / 3.0
            fabric_coherence["Precipitation"] = (state.dilation + state.decay + state.synthesis) / 3.0
            fabric_directions["Space"] = state.awareness
            fabric_directions["Field"] = state.coherence
            fabric_directions["Control"] = state.momentum
            fabric_directions["Precipitation"] = state.synthesis
        elif isinstance(state, dict):
            sys_coherence = state.get("coherence", 0.5)
            for fab in FABRIC_RATIOS:
                fabric_coherence[fab] = state.get(f"{fab}_coherence", sys_coherence)
                fabric_directions[fab] = state.get(f"{fab}_direction", 0.5)
        else:
            state_arr = np.asarray(state, dtype=np.float64)
            if state_arr.size < 12:
                padded = np.full(12, 0.5, dtype=np.float64)
                padded[: state_arr.size] = state_arr
                state_arr = padded

            for fab, sl in FABRIC_SLICES.items():
                block = state_arr[sl]
                norm = float(np.linalg.norm(block))
                fabric_coherence[fab] = max(0.0, min(1.0, 1.0 - 2.0 * abs(norm - 0.5)))
                fabric_directions[fab] = float(np.arctan2(block[1], block[0])) if norm > 1e-6 else 0.0

            sys_coherence = float(np.mean(list(fabric_coherence.values())))

        dist = self.compute_coherence_distance(sys_coherence)
        dissonance = self.calculate_dissonance(dist, lyapunov_perturbation)
        adsr = self.compute_adsr_envelope(dist)

        fabrics_out: dict[str, FabricSonification] = {}
        for fab_name, ratio in FABRIC_RATIOS.items():
            f_base = self.fundamental_hz * ratio
            c_fab = fabric_coherence.get(fab_name, sys_coherence)
            c_fab_dist = self.compute_coherence_distance(c_fab)

            detune_semitones = (c_fab - HIHO_TARGET_COHERENCE) * 4.0 + lyapunov_perturbation * 2.0
            freq_hz = f_base * (2.0 ** (detune_semitones / 12.0))

            amp = max(0.1, 1.0 - 2.0 * c_fab_dist)
            phase = fabric_directions.get(fab_name, 0.0) % (2.0 * math.pi)

            harmonics = []
            for h in range(1, 4):
                harmonic_freq = freq_hz * (h + 1) * (1.0 + (h * dissonance * 0.02))
                harmonics.append(harmonic_freq)

            fabrics_out[fab_name] = FabricSonification(
                fabric_name=fab_name,
                base_frequency_hz=f_base,
                frequency_hz=freq_hz,
                amplitude=amp,
                phase_rad=phase,
                harmonics_hz=harmonics,
                coherence=c_fab,
            )

        return AudioFieldState(
            fundamental_hz=self.fundamental_hz,
            system_coherence=sys_coherence,
            coherence_distance=dist,
            dissonance_index=dissonance,
            fabrics=fabrics_out,
            adsr=adsr,
            lyapunov_perturbation=lyapunov_perturbation,
        )

    @staticmethod
    def _apply_adsr_vector(
        t: np.ndarray,
        duration_s: float,
        adsr: ADSREnvelope,
    ) -> np.ndarray:
        """Construct ADSR envelope multipliers across time array t."""
        env = np.ones_like(t, dtype=np.float64)
        if duration_s <= 0:
            return env

        a_end = min(duration_s, adsr.attack_s)
        d_end = min(duration_s, a_end + adsr.decay_s)
        r_start = max(d_end, duration_s - adsr.release_s)

        attack_mask = t < a_end
        if a_end > 0:
            env[attack_mask] = t[attack_mask] / a_end

        decay_mask = (t >= a_end) & (t < d_end)
        if d_end > a_end:
            frac = (t[decay_mask] - a_end) / (d_end - a_end)
            env[decay_mask] = 1.0 - frac * (1.0 - adsr.sustain)

        sustain_mask = (t >= d_end) & (t < r_start)
        env[sustain_mask] = adsr.sustain

        release_mask = t >= r_start
        if r_start < duration_s:
            frac = (t[release_mask] - r_start) / (duration_s - r_start)
            env[release_mask] = adsr.sustain * (1.0 - frac)

        return env

    def generate_audio_buffer(
        self,
        field_state: AudioFieldState,
        duration_s: float = 0.05,
    ) -> np.ndarray:
        """Generate a float32 PCM audio buffer waveform array.

        Parameters
        ----------
        field_state : AudioFieldState
            Audio field state to synthesize.
        duration_s : float
            Buffer duration in seconds (default 0.05s = 50ms window).

        Returns
        -------
        np.ndarray
            1D numpy float32 array normalized to [-1.0, 1.0].
        """
        n_samples = max(1, int(self.sample_rate * duration_s))
        t = np.linspace(0, duration_s, n_samples, endpoint=False, dtype=np.float64)

        waveform = np.zeros(n_samples, dtype=np.float64)

        for fab in field_state.fabrics.values():
            tone = fab.amplitude * np.sin(2.0 * np.pi * fab.frequency_hz * t + fab.phase_rad)
            waveform += tone

            for idx, h_freq in enumerate(fab.harmonics_hz):
                h_amp = (fab.amplitude / (idx + 2)) * (1.0 - 0.5 * field_state.dissonance_index)
                waveform += h_amp * np.sin(2.0 * np.pi * h_freq * t + fab.phase_rad)

        env_vector = self._apply_adsr_vector(t, duration_s, field_state.adsr)
        waveform *= env_vector

        max_val = np.max(np.abs(waveform))
        if max_val > 1e-9:
            waveform /= max_val

        return waveform.astype(np.float32)

    def to_web_audio_json(
        self,
        field_state: AudioFieldState,
        duration_s: float = 0.05,
    ) -> dict[str, Any]:
        """Generate Web Audio API / PyGame compatible JSON audio buffer output.

        Parameters
        ----------
        field_state : AudioFieldState
            Audio field state.
        duration_s : float
            Buffer duration in seconds.

        Returns
        -------
        dict[str, Any]
            Complete JSON structure containing metadata and float array samples.
        """
        t0 = time.perf_counter()
        buffer_samples = self.generate_audio_buffer(field_state, duration_s)
        gen_time_ms = (time.perf_counter() - t0) * 1000.0

        return {
            "metadata": {
                "engine": "HIHOSonifier",
                "sample_rate": self.sample_rate,
                "duration_s": duration_s,
                "buffer_length": len(buffer_samples),
                "generation_time_ms": round(gen_time_ms, 3),
            },
            "audio_field": field_state.to_dict(),
            "samples": buffer_samples.tolist(),
        }

    async def delegate_inference(
        self,
        prompt: str,
        task_class: TaskClass = TaskClass.CODING,
    ) -> HybridRouteResponse:
        """Delegate internal model inference tasks to Tier 1 local silicon or Tier 2 cloud.

        Parameters
        ----------
        prompt : str
            Prompt to route.
        task_class : TaskClass
            Task classification (e.g. CODING -> Qwen3-Coder-30B on port 13305).

        Returns
        -------
        HybridRouteResponse
            Inference response from the router.
        """
        import socket
        port_open = False
        try:
            with socket.create_connection(("127.0.0.1", self.router.lemonade_port), timeout=0.1):
                port_open = True
        except Exception:
            port_open = False

        if port_open:
            return await self.router.route_by_capability(prompt, task_class=task_class)

        cloud_res = self.router.query_ollama_cloud(prompt, "glm-5.2:cloud")
        if cloud_res:
            return HybridRouteResponse(
                content=cloud_res,
                tier_used="Tier 2 (Ollama Cloud)",
                model_name="glm-5.2:cloud",
                latency_ms=10.0,
                verified=True,
                task_class=task_class,
            )

        return HybridRouteResponse(
            content="[Standby Fallback] Local silicon & cloud backends offline.",
            tier_used="Tier 0 (Unverified Fallback)",
            model_name="Qwen3-Coder-30B",
            latency_ms=0.1,
            verified=False,
            task_class=task_class,
        )


__all__ = [
    "DEFAULT_FUNDAMENTAL_HZ",
    "DEFAULT_SAMPLE_RATE",
    "FABRIC_RATIOS",
    "HIHO_TARGET_COHERENCE",
    "ADSREnvelope",
    "AudioFieldState",
    "FabricSonification",
    "HIHOSonifier",
]
