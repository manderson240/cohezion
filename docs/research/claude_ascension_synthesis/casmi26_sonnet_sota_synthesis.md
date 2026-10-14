I wrote the re-ranker, but I haven't run it. Executing the self-test was blocked on an approval I couldn't give in this session, so everything below is untested and the code may still contain bugs. I also can't tell you whether it reaches 0.440, because that needs a held-out evaluation on the real data.

To run it: `/tmp/claude-1000/rdk/bin/python scripts/kaggle/casmi26_rerank.py --selftest`. That scratch venv has rdkit, numpy and scipy; the repo `.venv` has no rdkit. The file is `scripts/kaggle/casmi26_rerank.py`, uncommitted.

**Your brief and our records disagree.**
- `ENVEDA_PLAN_20260930.md` has our best verified score at 0.328 (v7), with v8 and v9 lower (0.308 and 0.312). The brief says 0.420. Please confirm which is current.
- The metric there is MRR@25 over InChIKey14, so duplicate structures waste ranking slots. The code dedupes on InChIKey14 and scores with `mrr_at_k`.
- The plan also infers, without verifying, that the gap is mostly molecules that appear in PubChem or COCONUT but have no public spectra. If so, candidate recall matters more than the ranking equation. Test 2 in that plan, a formula-matched recall check on held-out training structures, is cheap and worth doing first.

## Formulation

**Adducts.** For candidate m with neutral mass M, adduct A is plausible only if |M + s_A − precursor| is within tolerance. The shifts s_A are +1.00728 for [M+H]+, +18.03383 for [M+NH4]+, 22.98922 for [M+Na]+ and −17.00329 for [M−H2O+H]+. This is what keeps an [M+NH4]+ precursor from being read as [M+H]+, which would put the neutral mass about 17 Da off and drop the true molecule.

**Surrogate alignment.** ICEBERG predicts in the [M+H]+ frame. For an observed adduct, a predicted peak p may match an observed peak at p or at p + Δ_A, where Δ_A = s_A − s_[M+H]+. A match through the shift is down-weighted by γ = 0.85. This is a modified cosine on √intensity with one-to-one greedy matching:

S_ICE(m) = τ · log Σ_A π_A · exp(cos_A / τ)

The sum runs over mass-consistent adducts only, with the adduct prior π renormalised over them, and τ = 0.1.

**MetFrag-style matcher.** It enumerates fragments from at most two bond cuts, using atom bitmasks. The result is cached per SMILES. Each fragment's ion m/z is allowed H-transfer shifts of −1 to +3 with a penalty. Cleavage cost is 1, 2, 2.5 and 3.5 for single, aromatic, double and triple bonds. It is run only on the top 60 candidates by provisional score, plus any candidate ICEBERG couldn't score.

S_MF = Σ_k √I_k · exp(−cost_k / τ_f) / Σ_k √I_k, taken over the peaks below the precursor region.

**Substructure term.** It applies diagnostic neutral losses and ions: hexose 162.053, glucuronide 176.032, deoxyhexose 146.058, sulfate, phosphate, carboxylic acid, and phenyl/benzyl/benzoyl ions. A rule adds `w·e` if the SMARTS matches and subtracts `veto·w·e` if it doesn't, where e is the evidence strength. The total is clipped to ±1.

**Joint score.**

Score(m) = z(S_ICE) + 0.42 · z(log(1 + min(count, 10⁵))) + λ · z(S_MF) + δ(m)

Here z is a per-query median/MAD standardisation, with floors on the spread and missing values set to zero. λ defaults to 0.35, which is a placeholder rather than a calibrated value.

**Calibration.** `fit_weights` minimises a listwise softmax negative log-likelihood, with L2 pulled toward (1, 0.42, 0.35, 1). It is only a surrogate for MRR, so check the result with `mrr_at_k`. Split train and validation by molecule, not by spectrum, or the fit just memorises the library.

## Failure modes and guards

| Failure | Guard |
|---|---|
| The pop term swamps S_ICE: `0.42·log(1+10⁷)` is about 6.8 against a cosine in [0, 1]. | Per-query standardisation plus a count cap at 10⁵. I'm assuming your 0.42 was fit in some scale, and I couldn't confirm which. Refit if it was raw. |
| A near-constant component gets amplified into noise by standardisation. | Spread floors per component. |
| Missing ICEBERG output, or a missing PubChem lookup, is treated as zero. | Missing values are imputed to the query median and flagged in `imputed`. A true count of 0 stays 0, while `None` (lookup failed) is imputed. |
| A mass-inconsistent candidate under an unknown adduct. | Hard mass filter, switchable via `hard_mass_filter`. |
| MetFrag is run only on a subset, which biases ranks. | Subset chosen on the provisional score, unscored candidates imputed to the median. |
| Isomer or duplicate entries fill the 25 slots. | InChIKey14 dedupe. I did not add tautomer canonicalisation, which the competition applies, so tautomers may still duplicate. |
| The same rule or adduct is double-counted. | The adduct mixture is a log-sum-exp, not a sum, and the substructure term is clipped. |

## Known limitations
- The adduct prior (0.55, 0.15, 0.15, 0.12, 0.03) is my guess and not fitted. The same goes for the cleavage costs and the H-shift penalties.
- Precursor-region peaks are excluded from the fragment match entirely.
- The Pyright flags on the self-test (lists passed where arrays are expected) are harmless, because `Query.__post_init__` converts them.
- Fragment enumeration is O(bonds²) per molecule, so large molecules are skipped above 70 heavy atoms. Cost on the full candidate set is unmeasured.

Next steps, in this order: run the self-test, run the recall test, then evaluate on held-out spectra.