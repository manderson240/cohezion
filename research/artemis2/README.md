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
  T and RH to ≤0.05 °C. The exact residual depends on which coefficient set is used.
- **Cross-calibration is good:** on the pad the two loggers have a **mean offset of 0.05 °C
  and 0.27 % RH**. Single-minute differences reach 0.4 °C and 3 % RH. Differences beyond
  that later in the record are environmental, not instrumental.
- **The timezone is CDT (UTC−5), as labelled.** The PDS label start (16:25:46Z) equals the
  first CSV row (11:25:46 CDT) + 5 h. DST started 2026-03-08, so the offset does not change
  anywhere in the record. As a consistency check, both loggers show a small RH step 6–8
  minutes before the 00:07 UTC splashdown, and Locker E humidity starts climbing about
  10 minutes after it. This is consistent with the timeline, but it is not independent proof
  of the clock.

### What the data tells us
1. **The lockers stayed dry in flight.** Mean absolute humidity was **5.1 g/m³ in flight**,
   the same as on the pad (5.1 g/m³). RH was 18–37 %. The closest the air came to its dew
   point during flight was about 15 °C away, so condensation was never a risk.
2. **The lockers warmed slowly.** The trend was +0.37 °C/day in Locker E and +0.49 °C/day in
   D→F. Locker E peaked at about 25.3 °C (12-hour mean) on 04-07/08 and then cooled to
   about 22.8 °C by reentry. The flight maximum was 26.0 °C (SN 1105, just after its move). A
   detrended power spectrum shows no clear periodicity: there is no 24-hour crew-schedule line
   and no attitude-cycling signal (`figures/hobo_flight_spectrum.png`).
3. **The lunar flyby left no thermal trace.** At closest approach (2026-04-06 23:00 UTC) and
   through the roughly 56-minute solar eclipse (geometric sunset 00:35 to sunrise 01:32,
   from the target file), Locker E stayed between 23.74 and 23.98 °C. That 0.24 °C range is
   typical of any 4-hour stretch of the flight. This is expected inside an actively
   controlled cabin.
4. **Moisture exposure started at splashdown, not at handover.** Absolute humidity in
   Locker E began rising around 00:15 UTC, just after splashdown, and accelerated after
   power-down (00:30). It went **from 5.7 g/m³ at 00:30 to 9.5 g/m³ at 02:00** and passed
   10 g/m³ by 02:48. It stayed high for the rest of the record. Locker F was better isolated:
   it climbed more slowly, from 4.7 to 6.9 g/m³ over 8 hours, and stayed at or below 7 g/m³
   until a handling event at about 14:45 UTC. The cargo handover came more than 3.5 days
   later, so for sample-curation planning the terrestrial-humidity clock starts at
   power-down and differs by locker.
5. **Most of the extreme values in the archive are post-mission.** SN 1105's label maxima
   (27.1 °C, 78 % RH), both loggers' RH and dew-point maxima, and the smallest dew-point
   margin (3.9 °C) all come from recovery and shipping. The one exception is SN 1104's
   25.57 °C temperature maximum, which occurred in flight (04-07 23:43 UTC). Examples are 2026-04-11 20:56 UTC aboard ship and 2026-04-15/16 in transit.
   Anyone who uses the label statistics as "flight environment" will overstate it.

### Anomalies and curiosities
- **Filename error.** Both files are named `art002_086-…`. The guide's filename spec for the
  HOBO loggers is `art002_<UTC Start Date in DOY-hhmmss>_<UTC End Date in DOY-hhmmss>_…`
  (Appendix, "HOBO data loggers"). The actual start, 2026-03-26, is **DOY 085** in both UTC
  and CDT. The end field `111` is correct, so this is an off-by-one in the start field.
- **An undocumented disturbance in Locker E on FD09.** The guide says SN 1104 sat untouched
  in Locker E. At **2026-04-09 19:49 UTC** it recorded the **largest in-flight humidity
  transient in the whole dataset: +12.9 % RH**. RH returns to baseline within about
  3 minutes, but temperature rises about 0.5 °C and stays elevated for 15+ minutes, and the
  absolute humidity stays shifted. That coupled, lasting response rules out a
  single-sample sensor glitch; it is the signature of the bag or locker being opened. It
  falls inside the documented 18:00–21:00 move window, about 65 minutes after the move time
  the data gives (below), and during FD09 "final cabin stowage". It may be bag handling
  connected with the move. It is **by far the largest** access-like event in Locker E. The
  only other one is a +1.1 % excursion at 04-02 23:31.
- **The FD09 relocation can be timed from the data.** The guide only gives the move as
  "between 18:00 and 21:00 UTC". SN 1105 shows a handling transient peaking at **18:45 UTC**,
  then a step warm-up into Locker F. Over the 6 hours on either side of the move, SN 1105's
  mean rose about 2.6 °C (23.1 → 25.7 °C) while Locker E rose only 0.25 °C. Assuming Locker D
  followed the same trend as E, Locker F was about 2.3–2.4 °C warmer than Locker D.
- **The loggers worked as locker-access sensors.** A sealed locker's RH changes slowly. Sharp,
  decaying excursions mean the locker was opened. The count depends on the threshold and the
  detector. With this script's detector (`transient_events`, excess over a 31-minute rolling
  median), Locker D/F (SN 1105) has 2 events at ≥3 % RH, 5 at ≥1.5 % and 10 at ≥1 %. Locker E
  has 1 at ≥1.5 % and 2 at ≥1 %. An independently written detector found 3, 5–7 and 14 for
  Locker D/F. Locker D was opened far more
  often than Locker E. Its largest pre-move excursion, **04-06 18:09 (part of a multi-peak
  cluster from 17:56)**, falls inside "Pre-Flyby Crew Conference and Camera Setup"
  (17:03–18:17) in Table 4. This is a coincidence in time, not proof of what was stored
  where.
- **A humidity step during parachute descent.** Both loggers show an RH step within about a
  minute of each other at 23:59–00:00 UTC, before splashdown. The step is +1.9 % in SN 1105
  and only +0.4 % in SN 1104.
  These data cannot show what caused it, for example a cabin vent or pressure-equalisation
  event during descent.

![flight](figures/hobo_flight.png)

## 2. Lunar Targeting Package / Outgoing Target Request (`artemis2_outgoing_target_request.json`)

This file lists 39 entries: 30 numbered observation targets and 9 lettered crew-swap or
break entries. The crew request times run from **18:45 to 01:23 UTC**. The geographic targets were
Glushko, Ohm (each scheduled twice), the Aristarchus Plateau, Reiner Gamma, Orientale Basin
(twice), Vavilov and Hertzsprung. Non-geographic targets included Earthset and Earthrise
around loss of signal, **Impact Flashes**, **Lofted Lunar Dust**, and the eclipse sequence
(Sunset, Eclipsed Moon / Deep Space, Sunrise). The file's geometric event times are Earthset
22:42–22:46, Earthrise 23:25, Sunset 00:35 and Sunrise 01:31–01:33, so loss of signal lasted
about 40 minutes and the solar eclipse about 56 minutes. The "request" times are crew
prompts and differ from these by up to 8 minutes; the Sunrise request (01:23) came 8 minutes
before the event.

Defects in the file:
- **Hertzsprung Basin has latitude, longitude and diameter all 0.** It is a real ~570 km
  farside basin, and it has no science-objective (STM) flags. The other geographic targets
  have coordinates, and spot checks against IAU positions agree for Glushko, Ohm,
  Aristarchus and Reiner Gamma. Reiner Gamma's diameter is 0, which may be deliberate for an
  albedo swirl. Hertzsprung looks like an incomplete late addition.
- **Inconsistent time formats.** The time fields use three formats (`06 Apr 2026
  18:00:00.000000`, `6 Apr 2026 18:00:00.000`, and blank for 6 entries), so a naive parser
  will fail. The guide's Table 4 also has a typo: `2026:04:05`.

## 3. Crew camera, Orion camera and mission audio bundles

_In progress: inventory and transcript survey pending._
