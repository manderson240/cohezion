#!/usr/bin/env python3
"""Packs Embedded Poincaré JEPA World Model into Kaggle Airgapped Dataset."""

import json
import os
import shutil

DIST_DIR = "dist/kaggle_bundle/cohezion_core/competitions/world_models"
os.makedirs(DIST_DIR, exist_ok=True)

src = "src/cohezion/competitions/world_models/embedded_adajepa_poincare_world_model.py"
dest = os.path.join(DIST_DIR, "embedded_adajepa_poincare_world_model.py")
shutil.copyfile(src, dest)

print("✓ Packed embedded world model into Kaggle airgapped bundle.")
print("• Path:", dest)
