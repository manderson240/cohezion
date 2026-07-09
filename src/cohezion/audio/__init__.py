"""Audio subsystem: bioacoustic encoding, TTS narration, neural audio streaming."""

import contextlib


# Wiring-sweep 2026-06-22: all audio sub-modules were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.audio.narrator import CosmoNarrator as CosmoNarrator
    from cohezion.audio.narrator import get_narrator as get_narrator

with contextlib.suppress(Exception):
    from cohezion.audio.neural_audio import (
        AudioStreamState as AudioStreamState,
    )
    from cohezion.audio.neural_audio import (
        NeuralAudioStream as NeuralAudioStream,
    )

with contextlib.suppress(Exception):
    from cohezion.audio.moshi_client import MoshiClient as MoshiClient

with contextlib.suppress(Exception):
    from cohezion.audio.bioacoustic_encoder import (
        BioacousticEncoder as BioacousticEncoder,
    )
    from cohezion.audio.bioacoustic_encoder import (
        BirdCLEFDataProduct as BirdCLEFDataProduct,
    )

with contextlib.suppress(Exception):
    from cohezion.audio.protoclr import ProtoCLR as ProtoCLR
