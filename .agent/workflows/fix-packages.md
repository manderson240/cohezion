---
description: Automatically add missing __init__.py files to directory structures.
---

1. Run the package fix script.
// turbo
run_command(CommandLine="find src/cohezion/ -type d -not -path '*/__pycache__*' -exec touch {}/__init__.py \;", Cwd="/home/mike-anderson/dev/cohezion/")

2. Verify with /audit.
