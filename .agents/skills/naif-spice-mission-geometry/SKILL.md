---
name: naif-spice-mission-geometry
description: |
  Compute spacecraft viewing geometry (sub-observer point, range, Earth's view of a body) from a
  mission's own NAIF SPICE trajectory kernels instead of hand-copied JPL Horizons rows. Use when:
  (1) an analysis types Horizons numbers into code as constants, (2) a mission's official PDS
  SPICE bundle is "delayed" and you assume no kernels exist yet, (3) you need lunar or planetary
  longitudes in the body's official frame (e.g. MOON_ME), (4) a NAIF directory name looks like it
  might be a different mission, (5) a computation lands inside a trajectory kernel's coverage gap.
  Key insight: NAIF often posts trajectory SPKs under pub/naif/<MISSION>/kernels/ months before
  the PDS bundle, and spacecraft IDs there differ from Horizons IDs.
author: Claude Code
version: 1.0.0
source: session 2026-11-05 (Artemis II flash map, research/artemis2/spice_geometry.py)
---

# NAIF SPICE Mission Geometry

## Problem

Hand-copied Horizons values are a linear trace: nobody re-derives them, the query that made them
is half-remembered, and they cannot be re-evaluated at a new time. When the mission's PDS SPICE
bundle is "delayed", it is easy to assume there is nothing better. Often there is.

## Where the kernels actually are

1. **Look in NAIF's operational tree, not only PDS.** `https://naif.jpl.nasa.gov/pub/naif/<MISSION>/kernels/`
   (spk/, ck/, fk/ ...) can hold a reconstructed trajectory long before
   `pub/naif/pds/pds4/<mission>/` exists. Artemis II: `ARTEMIS/kernels/spk/` had the JSC
   best-estimated trajectory on 2026-07-21; the PDS bundle was still missing on 2026-11-05.
2. **Open the directory before deciding what it is.** `ARTEMIS/` read like THEMIS-ARTEMIS; its
   files are `art002_*` / `EM2_*` (Artemis II). Read `aareadme.txt` and the `.cmt` companion.
3. **Read the `.cmt` for the NAIF ID and coverage gaps.** Artemis II Orion is `-24` in the SPK;
   Horizons calls the same craft `-1024`. The `.cmt` also lists coverage intervals. One gap
   (2026-04-07 00:54:48-00:55:00) fell inside the window being studied.

## Recipe

```python
import spiceypy as sp
# Load order matters: for overlapping coverage the LATER kernel wins.
# Load a gap-fill SPK BEFORE the main SPK so it only supplies what the main one lacks.
for k in ("naif0012.tls",                     # leap seconds
          "de440s.bsp",                       # planets + Moon (small DE440, ~32 MB)
          "pck00011.tpc",                     # body radii
          "moon_pa_de440_200625.bpc",         # lunar orientation (binary PCK)
          "moon_de440_250416.tf",             # defines MOON_ME / MOON_PA frames
          "<mission>_gapfill.bsp", "<mission>_main.bsp"):
    sp.furnsh(k)
et = sp.str2et("2026-04-07T01:04:00")
point, _, _ = sp.subpnt("INTERCEPT/ELLIPSOID", "MOON", et, "MOON_ME", "LT+S", "-24")
_, lon, lat = sp.reclat(point)                  # radians; lon % 360 for deg E
pos, _ = sp.spkpos("MOON", et, "J2000", "LT+S", "-24")
range_km = sp.vnorm(pos)
```

- **Lunar longitudes are quoted in MOON_ME** (Mean Earth/polar axis), which needs the DE440
  lunar PCK + FK. IAU_MOON (text PCK only) is a different rotation model: measured here it moved
  the sub-point by 0.0012 deg longitude, 0.0004 deg latitude. That is small, but it is a silent
  frame change, so name the frame and use MOON_ME.
- **Earth's view** is the same call with observer `"EARTH"`. Earth sees the hemisphere within
  90 deg of that sub-point, so "far side" = great-circle distance from it > 90 deg. Do not
  compare longitudes alone: latitude moved one result from 13 deg to 14.6 deg beyond the limb.

## Operational rules

- **Pin your own checksums.** NAIF publishes none. Record SHA-256 on first download, verify every
  run, and verify the `.part` file *before* renaming so a bad download is never kept.
- **Keep kernels out of git** (`data/` is ignored; a full set is ~50 MB).
- **Import spiceypy lazily** inside the function that needs it, so unit tests and CI do not
  require it (`--with spiceypy` in the full-run reproduce command only).
- **Keep the replaced source as a recorded cross-check, then make agreement a standing check.**
  Store "SPICE minus Horizons" in the output and fail a goal if it exceeds a tolerance. Two
  independent sources agreeing (Artemis II: 0.004 deg longitude, 2.4 km range) is stronger
  evidence than either alone, and the check catches a wrong frame, ID or load order immediately.

## Verification

- Compare one epoch against Horizons by hand before switching (sub-lon/lat within ~0.01 deg,
  range within a few km for a reconstructed trajectory). A difference of degrees means a wrong
  frame (IAU vs ME), wrong observer ID, or missing light-time correction.
- Query a time inside a documented coverage gap: without the gap-fill kernel SPICE raises
  `SPKINSUFFDATA`; with it the result is continuous.
- Re-run the downstream fit and diff its outputs against the Horizons-based version. Expect
  sub-0.1 deg changes; anything larger needs an explanation before committing.

## Notes

- SPICE trajectory is not pointing. Camera fields of view need CK (attitude) and IK/FK
  (instrument) kernels; a trajectory-only release cannot test whether a target was in frame.
- `str2et` needs the leap-second kernel loaded first; a missing LSK fails with `MISSINGTIMEINFO`.
