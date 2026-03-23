---
title: "Exoplanets"
date: 2026-03-04
tags: [concept, astrophysics, exoplanets, habitability]
aspect: knower
neural:
  activation: 0.91
  stage: mature
  synapse_in: 9
  synapse_out: 11
---

# Exoplanets

## Definition

Exoplanets are planets that orbit stars outside our solar system, or in rarer cases, free-floating rogue planets unbound to any star. The first confirmed exoplanet orbiting a Sun-like star, 51 Pegasi b, was discovered in 1995 by Michel Mayor and Didier Queloz, earning them the 2019 Nobel Prize in Physics. As of early 2026, over 6,000 exoplanets have been confirmed, with thousands more candidates awaiting validation. The field has revealed an extraordinary diversity of planetary systems -- from hot Jupiters orbiting their stars in days to potentially habitable rocky worlds in stellar habitable zones.

## Key Properties

- **Transit photometry:** The most productive detection method, used by NASA's Kepler and TESS missions. Measures periodic dips in starlight when a planet passes in front of its host star. The dip depth reveals planetary radius; combined with radial velocity mass measurements, it yields bulk density and composition constraints.
- **Radial velocity (Doppler spectroscopy):** Detects the gravitational "wobble" a planet induces on its host star by measuring periodic Doppler shifts in stellar spectral lines. Pioneered the first exoplanet discoveries and remains essential for mass determination.
- **Habitable zone:** The circumstellar region where conditions permit liquid water on a planetary surface, dependent on stellar luminosity, planetary atmosphere, and albedo. Approximately 1 in 5 Sun-like stars are estimated to host an Earth-sized planet in the habitable zone, suggesting ~11 billion potentially habitable worlds in the Milky Way.
- **Atmospheric characterization:** JWST and ground-based spectrographs can detect molecular absorption features (H2O, CO2, CH4, O3) in transiting exoplanet atmospheres via transmission spectroscopy, enabling the search for biosignatures.
- **Machine learning in exoplanet science:** ML classifiers (Random Forest, XGBoost, neural networks) validate transit candidates from TESS lightcurves, achieving >99% accuracy and accelerating the confirmation pipeline.

## Examples

- Kepler-725c, a super-Earth 10 times Earth's mass, was discovered in 2025 via transit timing variations within the habitable zone of a Sun-like star (published in Nature Astronomy).
- GJ 251c, identified in 2025 at only 18 light-years away, is a rocky super-Earth in the middle of its star's habitable zone and one of the best prospects for direct imaging of a potentially habitable world.
- The TRAPPIST-1 system contains seven Earth-sized planets, three in the habitable zone, making it a prime target for JWST atmospheric characterization.

## Primary Sources

- Mayor, M. & Queloz, D. (1995). *A Jupiter-mass companion to a solar-type star*. Nature. [DOI:10.1038/378355a0](https://doi.org/10.1038/378355a0)
- Borucki, W. J. et al. (2010). *Kepler Planet-Detection Mission: Introduction and First Results*. Science.
- NASA Exoplanet Archive. [exoplanetarchive.ipac.caltech.edu](https://exoplanetarchive.ipac.caltech.edu/)

## Related Concepts

- [[exoplanet-habitability]] — analysis of conditions that make exoplanets potentially habitable
- [[habitable-zone]] — the circumstellar region permitting liquid water
- [[stellar-evolution]] — host star properties determine habitable zone boundaries and planetary system evolution
- [[astrophysics-observations]] — the observational techniques (photometry, spectroscopy) used to detect and characterize exoplanets
- [[jwst-observations]] — JWST's infrared capabilities enable atmospheric characterization of transiting exoplanets
- [[astronomy]] — the observational science framework within which exoplanet discovery operates
- [[cosmology]] — exoplanet demographics inform models of planet formation across cosmic time

## Related Papers

- [[rethinking-exoplanet-habitability]] — revisiting habitability criteria beyond the traditional habitable zone definition
- [[tidally-locked-exoplanet-habitability]] — habitability of tidally locked planets around M-dwarf stars
- [[super-earth-magnetic-protection-magma]] — magnetic field generation in super-Earths and its role in atmospheric retention
- [[runaway-stars-milky-way]] — high-velocity runaway stars constrain the galactic habitable zone through stellar passage radiation

## Relevance to Cohezion

Exoplanets represent a significant research thread in Cohezion's astrophysics knowledge graph, connecting papers on habitability, stellar evolution, and JWST observations. The vault's cross-linking capabilities enable agents to trace connections from exoplanet detection methods to atmospheric characterization techniques, from habitability models to the stellar physics that determines habitable zone boundaries -- exemplifying multi-hop knowledge synthesis across observational and theoretical domains.
