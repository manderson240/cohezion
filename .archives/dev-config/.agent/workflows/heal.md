---
description: Trigger the autonomic self-healing protocol.
---

1. Execute the immune system check.
// turbo
run_command(CommandLine="python3 src/cohezion/healing/immune_system.py", Cwd="/home/mike-anderson/dev/cohezion/")

2. Apply corrections if drift is detected.
// turbo
run_command(CommandLine="python3 -c \"import asyncio; from cohezion.healing import get_healing_system; sys = get_healing_system(); asyncio.run(sys.heal(asyncio.run(sys.health_check())))\"", Cwd="/home/mike-anderson/dev/cohezion/src/")

3. Update the MISSION_JOURNAL with healing outcomes.
