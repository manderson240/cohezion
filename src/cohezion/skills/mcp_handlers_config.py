"""Configuration and skill execution handlers for Cohezion MCP Server."""

import json
import os
import sys
from typing import Any


class ConfigHandlers:
    """Handlers for configuration and skill execution tools."""

    skills: dict[str, Any]
    model_registry: dict[str, Any]
    compound_config: dict[str, Any]

    def pocket_tts_generate(self, args: dict[str, Any]) -> dict[str, Any]:
        """Generate speech using Kyutai Pocket TTS"""
        try:
            text = args.get("text")
            voice = args.get("voice", "alba")
            output_path = args.get("output_path", "/tmp/pocket_tts_output.wav")
            speed = args.get("speed", 1.0)

            if not text:
                return {
                    "content": [{"type": "text", "text": "Error: text is required"}]
                }

            try:
                import scipy.io.wavfile
                import torch
                from pocket_tts import TTSModel
            except ImportError:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "Error: pocket-tts not installed. Install with: pip install pocket-tts",
                        }
                    ]
                }

            tts_model = TTSModel.load_model()
            voice_state = tts_model.get_state_for_audio_prompt(voice)

            audio = tts_model.generate_audio(voice_state, text)

            scipy.io.wavfile.write(output_path, tts_model.sample_rate, audio.numpy())

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully generated speech using Pocket TTS\nVoice: {voice}\nOutput: {output_path}\nDuration: {len(audio) / tts_model.sample_rate:.2f}s\nSize: {len(audio) * 2 / 1024 / 1024:.2f}MB",
                    }
                ]
            }

        except Exception as e:
            return {
                "content": [
                    {"type": "text", "text": f"Pocket TTS generation failed: {e}"}
                ]
            }

    def execute_skill(self, skill_name: str, inputs: dict[str, Any]) -> dict[str, Any]:
        if skill_name not in self.skills:
            return {
                "content": [
                    {"type": "text", "text": f"Error: Skill '{skill_name}' not found"}
                ]
            }
        skill = self.skills[skill_name]
        skill_path_rel = skill.get("path")
        if not skill_path_rel:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Skill path missing for '{skill_name}'",
                    }
                ]
            }

        skill_path = os.path.join(
            os.environ.get("COHEZION_ROOT", "/home/mike-anderson/dev/cohezion"),
            skill_path_rel,
        )
        if not os.path.exists(skill_path):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Skill file not found: {skill_path}",
                    }
                ]
            }
        try:
            with open(skill_path) as f:
                return {"content": [{"type": "text", "text": f.read()}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error executing skill: {e}"}]
            }

    def get_compound_config(self) -> dict[str, Any]:
        vitals = (
            self.monitor.get_vitals()
            if self.monitor
            else {"status": "monitor_not_available"}
        )
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "config": self.compound_config,
                            "models": self.model_registry.get("models", {}),
                            "vitals": vitals,
                        },
                        indent=2,
                    ),
                }
            ]
        }

    def select_model(
        self, task_type: str, complexity: int, context_needs: int
    ) -> dict[str, Any]:
        models = self.model_registry.get("models", {})

        installed_models = set()
        try:
            import subprocess

            res = subprocess.run(["ollama", "list"], capture_output=True, text=True)
            for line in res.stdout.splitlines()[1:]:
                if line.strip():
                    installed_models.add(line.split()[0].split(":")[0])
        except Exception as e:
            sys.stderr.write(f"Failed to check installed models: {e}\n")

        flat_models = {}
        for category in models.values():
            if isinstance(category, dict):
                flat_models.update(category)

        candidates = []
        for m_id, m_info in flat_models.items():
            if not isinstance(m_info, dict):
                continue
            base_id = m_id.split(":")[0]
            if m_info.get("specialization") == task_type:
                if base_id in installed_models:
                    candidates.append((base_id, m_info))
                else:
                    sys.stderr.write(
                        f"Warning: Specialist model {base_id} not installed in Ollama.\n"
                    )

        if candidates:
            candidates.sort(key=lambda x: x[1].get("priority", 99))
            recommended = candidates[0][0]
        else:
            fallback_order = [
                "qwen3-coder-next",
                "qwen3-coder-256k",
                "gpt-oss-256k",
                "phi4-256k",
                "phi4-mini",
            ]
            recommended = next(
                (m for m in fallback_order if m in installed_models), "phi4-mini"
            )

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "recommended_model": f"{recommended}:latest",
                            "all_models": [f"{m}:latest" for m in models.keys()],
                            "installed_only": list(installed_models),
                        },
                        indent=2,
                    ),
                }
            ]
        }
