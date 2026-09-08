from cohezion.multimodal.orchestrator import (
    MultimodalModality,
    UnifiedMultimodalOrchestrator,
)


def test_multimodal_modality_resolution():
    # Text Modality (NPU Primary)
    text_entry = UnifiedMultimodalOrchestrator.resolve_model(
        MultimodalModality.TEXT, prefer_npu=True
    )
    assert text_entry.model_id == "qwen3.6-moe-35b-a3b-FLM"
    assert text_entry.hardware_lane == "NPU"

    # Vision Modality (NPU Primary)
    vis_entry = UnifiedMultimodalOrchestrator.resolve_model(
        MultimodalModality.VISION, prefer_npu=True
    )
    assert vis_entry.hardware_lane == "NPU"

    # Audio Modality
    audio_entry = UnifiedMultimodalOrchestrator.resolve_model(MultimodalModality.AUDIO)
    assert audio_entry.modality == MultimodalModality.AUDIO

    # 3D Mesh Modality
    mesh_entry = UnifiedMultimodalOrchestrator.resolve_model(MultimodalModality.MESH_3D)
    assert mesh_entry.model_id == "TRELLIS-3D"

    # Music Modality
    music_entry = UnifiedMultimodalOrchestrator.resolve_model(MultimodalModality.MUSIC)
    assert music_entry.model_id == "ACE-Step-Music"


def test_multimodal_preflight_safety():
    safe, msg = UnifiedMultimodalOrchestrator.check_preflight_safety()
    assert isinstance(safe, bool)
    assert isinstance(msg, str)
