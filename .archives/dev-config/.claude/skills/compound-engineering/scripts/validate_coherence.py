#!/usr/bin/env python3
"""Validate coherence score for a compound engineering request.

Deterministic check that verifies alignment scores meet HIHO thresholds.
Bundled with the compound-engineering skill per Anthropic's recommendation
to use scripts for critical validations rather than language instructions.

Usage:
    python scripts/validate_coherence.py --score 0.85
    python scripts/validate_coherence.py --score 0.3 --strict
"""

import argparse
import sys


HIHO_THRESHOLD = 0.5
STRICT_THRESHOLD = 0.7


def validate(score: float, strict: bool = False) -> tuple[bool, str]:
    threshold = STRICT_THRESHOLD if strict else HIHO_THRESHOLD

    if score < 0.0 or score > 1.0:
        return False, f"Invalid coherence score {score}: must be between 0.0 and 1.0"

    if score < threshold:
        return False, (
            f"Coherence {score:.2f} below {'strict ' if strict else ''}"
            f"threshold {threshold:.2f}. "
            f"Decompose request into smaller sub-tasks or escalate."
        )

    return True, f"Coherence {score:.2f} meets threshold {threshold:.2f}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate coherence score")
    parser.add_argument("--score", type=float, required=True, help="Coherence score (0.0-1.0)")
    parser.add_argument("--strict", action="store_true", help="Use strict threshold (0.7)")
    args = parser.parse_args()

    passed, message = validate(args.score, args.strict)
    print(message)
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
