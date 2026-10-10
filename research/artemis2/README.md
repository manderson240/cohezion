# Artemis II science archive — first look (PDS release 2026-10-07)

Source: PDS Geosciences Node, <https://pds-geosciences.wustl.edu/missions/artemis2/index.htm>.
The first delivery has four bundles: crew cameras, Orion cameras, mission audio (all at the
PDS Cartography and Imaging Sciences Node), and the Mission Bundle (documents plus Orion
locker temperature/humidity) at the Geosciences Node. The SPICE geometry bundle is still
**delayed**, so nothing here depends on pointing or footprints.

Reproduce the locker analysis (it downloads its own inputs into the git-ignored `data/` directory):

```bash
uv run --no-project --with pandas --with matplotlib python research/artemis2/analyze_hobo.py
```

Outputs: `hobo_results.json` (every number quoted below) and `figures/`.

## 1. Orion locker environment (2 × HOBO MX1101, 60 s cadence)

Two loggers sat in bags in the crew-cabin storage lockers that future missions will use for
returned lunar samples. SN 1104 stayed in **Locker E** for the whole mission. SN 1105 started
in **Locker D** and was moved to **Locker F** on FD09. The logs run from 2026-03-26 to
2026-04-21: six days on the pad, the 9.1-day flight, and ten days of recovery and shipping.

![overview](figures/hobo_overview.png)

### Data quality: clean
- **Complete:** 37,706 and 37,690 records with no gaps. Every interval is exactly 60 s and
  the sequence numbers are continuous.
- **Labels are accurate:** the PDS4 label statistics (min, max, mean, std) match the data to
  rounding.
- **Dew point checks out:** the logged dew point matches a Magnus–Tetens recomputation from
  T and RH to ≤0.036 °C. There is a constant +0.02 °C bias, so the logger uses slightly
  different coefficients.
- **Cross-calibration is good:** on the pad the two loggers agree to **0.05 °C and 0.27 % RH**.
  Every difference later in the record is therefore environmental, not instrumental.
- **The clock and timezone are right.** The files are in CDT. When converted to UTC, a
  cabin-wide humidity step appears in both loggers 7–9 minutes before the documented 00:07
  UTC splashdown, which is during parachute descent. A CST/CDT mix-up would put that step an
  hour away from splashdown.

### What the data tells us
1. **The lockers stayed dry in flight.** Mean absolute humidity was **5.1 g/m³ in flight**,
   the same as on the pad (5.1 g/m³). RH was 18–37 %. The closest the air came to its dew
   point during flight was about 15 °C away, so condensation was never a risk.
2. **The lockers warmed slowly.** The trend was +0.37 °C/day in Locker E and +0.49 °C/day in
   D→F, rising from about 21 °C to about 25–26 °C. The flight maximum was 26.0 °C. A
   detrended power spectrum shows no clear periodicity: there is no 24-hour crew-schedule line
   and no attitude-cycling signal (`figures/hobo_flight_spectrum.png`).
3. **The lunar flyby left no thermal trace.** At closest approach (2026-04-06 23:00 UTC) and
   through the roughly 47-minute solar eclipse (the "Sunset" target at 00:36 to "Sunrise" at
   01:23), Locker E stayed between 23.74 and 23.98 °C. The lockers are thermally decoupled
   from the outside on timescales of hours.
4. **Moisture exposure started at splashdown, not at handover.** After Orion powered down
   (00:30 UTC), absolute humidity in Locker E rose **from 5.7 to 9.5 g/m³ within 90 minutes** and passed
   10 g/m³ by 02:48 UTC. It stayed high for the rest of the record. Locker F was much better
   isolated: it stayed at or below about 7 g/m³ for roughly 14 hours, until a handling event
   around 15:00 UTC. The cargo handover came more than 3.5 days
   later, so for sample-curation planning the terrestrial-humidity clock starts at
   power-down and differs by locker.
5. **The highest values in the archive are post-mission.** The label maxima (27.1 °C, 78 %
   RH) and the smallest dew-point margin (3.9 °C) all come from recovery and shipping, not
   from flight. Examples are 2026-04-11 20:56 UTC aboard ship and 2026-04-15/16 in transit.
   Anyone who uses the label statistics as "flight environment" will overstate it.

### Anomalies and curiosities
- **Filename error.** Both files are named `art002_086-…`. The guide defines the field as UTC
  start DOY, and the actual start (2026-03-26) is **DOY 085**. The end field `111` is correct.
- **An undocumented disturbance in Locker E on FD09.** The guide says SN 1104 sat untouched
  in Locker E. At **2026-04-09 19:49 UTC** it recorded the **largest in-flight humidity
  transient in the whole dataset: +12.9 % RH**, with a +0.5 °C spike, decaying within about
  10 minutes. This is the signature of the bag or locker being opened. It came about 65
  minutes after the documented SN 1105 move and falls in the FD09 "final cabin stowage"
  period. It is the **only** access-like event in Locker E during the entire flight.
- **The FD09 relocation can be timed from the data.** The guide only gives the move as
  "between 18:00 and 21:00 UTC". SN 1105 shows a handling transient peaking at **18:45 UTC**,
  then a step warm-up into Locker F. Over the 6 hours on either side of the move, SN 1105's
  mean rose 2.7 °C (23.1 → 25.8 °C) while Locker E rose only 0.3 °C, so Locker F was about
  2.4 °C warmer than Locker D.
- **The loggers worked as locker-access sensors.** A sealed locker's RH changes slowly. Sharp,
  decaying excursions mean the locker was opened. In flight, Locker D (SN 1105) shows 5 such
  events and Locker E shows 1. Two of Locker D's events fall inside crew camera activities
  in the Table 4 timeline:
  - 04-06 16:37, during an unscheduled Moon imaging session (16:14–16:38)
  - 04-06 18:09, the largest, during "Pre-Flyby Crew Conference and Camera Setup" (17:03–18:17)

  The other three are 04-02 23:35, 04-04 05:18 and the FD09 move at 04-09 18:45. This is a
  coincidence in time, not proof of what was stored where.
- **A humidity step during parachute descent.** Both loggers show a simultaneous RH step at
  23:58–00:00 UTC, before splashdown. Both see it within about a minute, so it was cabin-wide.
  These data cannot show what caused it, for example a cabin vent or pressure-equalisation
  event during descent.

![flight](figures/hobo_flight.png)

## 2. Lunar Targeting Package / Outgoing Target Request (`artemis2_outgoing_target_request.json`)

This file lists 39 entries: 30 numbered observation targets and 9 lettered crew-swap or
break entries. The flyby plan ran from **18:45 to 01:23 UTC**. The geographic targets were
Glushko, Ohm (each scheduled twice), the Aristarchus Plateau, Reiner Gamma, Orientale Basin
(twice), Vavilov and Hertzsprung. Non-geographic targets included Earthset (22:38) and
Earthrise (23:18) around loss of signal, **Impact Flashes (23:02)**, **Lofted Lunar Dust
(23:10)**, and the eclipse sequence (Sunset 00:36, Eclipsed Moon / Deep Space, Sunrise 01:23).

Defects in the file:
- **Hertzsprung Basin has latitude, longitude and diameter all 0.** It is a real ~570 km
  farside basin, and it has no science-objective (STM) flags. Every other geographic target
  is filled in correctly; spot checks against IAU positions agree for Glushko, Ohm,
  Aristarchus and Reiner Gamma. This looks like an incomplete late addition.
- **Inconsistent time formats.** The time fields use three formats (`06 Apr 2026
  18:00:00.000000`, `6 Apr 2026 18:00:00.000`, and blank for 6 entries), so a naive parser
  will fail. The guide's Table 4 also has a typo: `2026:04:05`.

## 3. Crew camera, Orion camera and mission audio bundles

_In progress: inventory and transcript survey pending._
