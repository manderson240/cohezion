def rank_molecular_candidates(precursor_mz, fragments, candidates):
    # Define a tolerance (in Da) for matching candidate exact_mass to fragment m/z.
    tolerance = 5e-6  # 5 ppm: since m/z is often given in Th (atomic mass units), but we are using absolute difference.

    def score(candidate):
        count = 0
        cand_mass = candidate['exact_mass']
        for frag in fragments:
            if abs(cand_mass - frag) <= tolerance:
                count += 1
        return count

    # We'll sort by the score function, descending.
    candidates.sort(key=lambda x: -score(x))
    return candidates