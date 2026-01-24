import logging
import subprocess
import os

logger = logging.getLogger(__name__)

class JourneyNarrator:
    """
    Provides natural language narration for agentic journeys.
    Supports asynchronous text-to-speech via CLI commands.
    """
    def __init__(self, tts_command: str | None = None):
        # Default to a generic 'say' or 'espeak' if available
        self.tts_command = tts_command or os.getenv("COHEZION_TTS_CMD", "echo")

    def generate_narration(self, agent_name: str, task: str, thought: str) -> str:
        """
        Creates a first-person narration string for the agent's current step.
        """
        # Truncate content for narration
        excerpt = thought[:200].replace("\n", " ").strip()
        return f"I am {agent_name}. I am {task}. My analysis reveals: {excerpt}."

    async def narrate(self, text: str, persistence_id: str | None = None):
        """
        Dispatches the text to the configured TTS command.
        Also persists the text as a pseudo-audio file for 'playback' later.
        """
        try:
            # Persistence path
            safe_id = persistence_id or f"thought_{int(time.time()*1000)}"
            audio_dir = "/home/mike-anderson/dev/cohezion/audio/narrations"
            text_path = os.path.join(audio_dir, f"{safe_id}.txt")

            # Save the text of the narration (audit trail)
            with open(text_path, "w") as f:
                f.write(text)

            cmd = f"{self.tts_command} \"{text}\""
            logger.info(f"🎙️ Narration [{safe_id}]: {text[:50]}...")

            # If we have a real TTS engine (not echo), we would save to .mp3 here
            # For now, we simulate the 'location' where audio lives

            process = await asyncio.create_subprocess_shell(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.warning(f"Narration playback/persistence failed: {e}")

import asyncio
import time
