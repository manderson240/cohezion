---
title: Neutrinos Sculpting Large Scale Structure (DESI)
date: 2026-02-26
tags: [neutrinos, cosmology, desi, large-scale-structure, dark-matter, astrophysics]
source: https://search.app/8hEQJ
---

## Summary
Using DESI galaxy survey data covering millions of galaxies, researchers detected a faint but unmistakable suppression of cosmic structure on smaller scales — the telltale signature of free-streaming neutrinos. Unlike cold dark matter which clumps gravitationally, ultra-light neutrinos stream freely in the early universe, damping structure formation below certain scales.

## Key Concepts
- Neutrino free-streaming suppresses small-scale cosmic structure
- DESI provides most precise measurement of galaxy clustering to date
- Baryon Acoustic Oscillations used as cosmic ruler
- First precision measurement of neutrino mass contribution to structure

## COHEZION Integration
- **fractal_universe.py**: Critical input for large-scale structure simulation — neutrino damping must be included in realistic universe simulation power spectra
- **enhanced_simulator.py**: Neutrino physics as a simulation parameter — mass hierarchy constraints from DESI
- **TODO**: Incorporate neutrino damping scale into fractal_universe.py's power spectrum generation — use DESI constraints for realistic Pk(k) suppression at small scales

## Related Concepts

- [[neutrino-physics]] — this paper is the primary empirical result for the neutrino physics domain in the Cohezion knowledge graph

## Related Papers

- [[jwst-dark-matter-map]] — JWST maps dark matter via gravitational lensing at large scales; DESI maps neutrino-induced damping via galaxy clustering — both probe how matter (dark and light) is distributed across the cosmic web, using complementary techniques
- [[axion-dark-matter-quantum-sensors]] — neutrinos and axions are both ultra-light, weakly-interacting particles that shape large-scale structure; DESI's neutrino constraints and axion quantum sensor limits are parallel precision measurements constraining different corners of the beyond-standard-model particle physics relevant to cosmology
- [[early-hot-galaxy-cluster-14-billion-years]] — DESI's neutrino constraints directly bear on the same ΛCDM structure formation models that fail to predict this early hot cluster; neutrino free-streaming affects exactly the small-scale structure suppression that makes early cluster formation so anomalous
- [[dark-matter]] — neutrinos are the "hot" component of cosmic structure alongside cold dark matter; DESI's first precision neutrino mass measurement from structure is a direct complement to dark matter detection efforts
