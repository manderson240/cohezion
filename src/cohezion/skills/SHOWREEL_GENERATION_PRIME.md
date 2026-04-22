---
name: showreel-generation-prime
description: "Automated media synthesis and narrative visualization. Orchestrating images, audio, and metadata into a high-engagement video format."
metadata:
  version: "v1.0"
  concepts: ["Milestone Detection", "Narration Sync", "Ambient Mix", "Style Consistency"]
  source: "src/cohezion/skills/SHOWREEL_GENERATION_PRIME.md"
---

# SKILL: SHOWREEL_GENERATION_PRIME

## DOMAIN EXPERTISE
Automated media synthesis and narrative visualization. Orchestrating images, audio, and metadata into a high-engagement video format.

## KEY TEXTS & CONCEPTS
- **Milestone Detection**: Automatically identifying clips from simulation logs.
- **Narration Sync**: Aligning pocket-tts audio with visual transitions.
- **Ambient Mix**: Layering sonification chords behind the narration.
- **Style Consistency**: Ensuring generated images follow the Nexus Green/Gold aesthetic.

## INSTRUCTION
1. **Fetch Samples**: Load trajectory samples from `universal_simulation.py` results.
2. **Generate Prompts**: Create image prompts based on 12D state gradients.
3. **Trigger Narration**: Call `pocket-tts` for each milestone description.
4. **Synthesize**: Combine into a sequence for UI replay or .mp4 export.

## VERSION
v1.0

## SEE ALSO
- [GALLERY_AGENT_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/GALLERY_AGENT_PRIME.md)
- [SONIFICATION_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SONIFICATION_PRIME.md)
