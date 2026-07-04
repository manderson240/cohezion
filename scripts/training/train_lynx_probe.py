"""Train the LYNX escalation probe from collected decision data.

Loads decision records from ~/.cohezion-engine/lynx-data/decisions_*.jsonl,
fits a logistic regression probe, and saves weights to escalation_probe.npz.

Usage:
    uv run python scripts/training/train_lynx_probe.py
    uv run python scripts/training/train_lynx_probe.py --threshold 0.4
    uv run python scripts/training/train_lynx_probe.py --data-dir /custom/path

Expected data format (one JSON per line):
    {"ts": 1234.5, "text_len": 142, "escalated": false,
     "confidence": 0.32, "output_type": "short_answer"}
    # After flush_data with igpu comparison:
    {"ts": ..., "text_len": 88, "escalated": true,
     "confidence": 0.71, "output_type": "short_categorical", "igpu_text_len": 212}

When igpu_text_len is present, the label is derived from whether escalation helped
(igpu_text_len > text_len * 1.5 → escalation was beneficial).  When absent, the
recorded `escalated` decision is used as a noisy pseudo-label for warm-starting.
"""

from __future__ import annotations

import argparse
import glob
import json
import math
import sys
from pathlib import Path

import numpy as np


# Match _DATA_DIR and _PROBE_PATH from lynx_gate.py
_DATA_DIR = Path.home() / ".cohezion-engine" / "lynx-data"
_PROBE_PATH = _DATA_DIR / "escalation_probe.npz"


def extract_features_from_record(record: dict) -> np.ndarray:
    """Reconstruct the feature vector from a saved decision record.

    Mirrors _extract_features() in lynx_gate.py using only the fields
    that flush_data() actually saves (text_len, output_type).
    Features 1-4 that require the full text default to their population means.
    """
    text_len: int = record.get("text_len", 0)
    output_type: str = record.get("output_type", "short_answer")

    f0 = math.log1p(text_len) / 10.0  # length signal (same formula as live extraction)
    f1 = 0.5  # completeness — unknown from text_len, use neutral prior
    f2 = 0.6  # vocab diversity — typical English prose prior
    f3 = 0.5  # avg word length — neutral prior
    f4 = 0.0  # question words — conservative (assume not present)
    f5 = 1.0 if output_type == "short_categorical" else 0.0
    f6 = 1.0 if output_type == "short_answer" else 0.0
    f7 = 1.0 if output_type not in ("short_categorical", "short_answer") else 0.0

    return np.array([f0, f1, f2, f3, f4, f5, f6, f7], dtype=np.float32)


def derive_label(record: dict) -> int | None:
    """Derive binary escalation label from a decision record.

    Returns 1 = should escalate, 0 = should not escalate, None = skip.

    Priority:
    1. If igpu_text_len present: supervised signal (did escalation produce more?)
    2. Otherwise: use recorded `escalated` decision as pseudo-label.
    """
    if "igpu_text_len" in record:
        text_len = record.get("text_len", 0)
        igpu_text_len = record["igpu_text_len"]
        # Escalation helped if iGPU produced ≥50% more text
        return 1 if igpu_text_len >= text_len * 1.5 else 0

    # Pseudo-label: trust the probe's own recorded decision
    escalated = record.get("escalated")
    if escalated is None:
        return None
    return 1 if escalated else 0


def load_data(data_dir: Path) -> tuple[np.ndarray, np.ndarray]:
    """Load all JSONL files and return (X, y) arrays."""
    pattern = str(data_dir / "decisions_*.jsonl")
    files = sorted(glob.glob(pattern))

    if not files:
        print(f"No data files found at {pattern}")
        sys.exit(1)

    X_rows: list[np.ndarray] = []
    y_rows: list[int] = []

    for path in files:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                label = derive_label(record)
                if label is None:
                    continue

                X_rows.append(extract_features_from_record(record))
                y_rows.append(label)

    if not X_rows:
        print("No valid labeled records found.")
        sys.exit(1)

    X = np.stack(X_rows)
    y = np.array(y_rows, dtype=np.int32)
    return X, y


def train_probe(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    """Fit logistic regression, return (weights, bias).

    Uses sklearn's LogisticRegression with L2 regularisation.  The probe
    aims for high precision on escalation decisions (escalate only when sure).
    """
    try:
        from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]
        from sklearn.preprocessing import StandardScaler  # type: ignore[import-untyped]
    except ImportError:
        print("scikit-learn required: uv pip install scikit-learn")
        sys.exit(1)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    clf = LogisticRegression(C=1.0, class_weight="balanced", max_iter=1000, random_state=42)
    clf.fit(X_scaled, y)

    # Bake the scaler into the weights so inference needs no scaler
    # w_eff = w / sigma,  b_eff = b - w · (mu / sigma)
    w = clf.coef_[0]
    b = float(clf.intercept_[0])
    mu = scaler.mean_
    sigma = scaler.scale_

    w_eff = w / sigma
    b_eff = b - float(np.dot(w, mu / sigma))

    return w_eff.astype(np.float32), b_eff


def find_threshold(
    X: np.ndarray, y: np.ndarray, weights: np.ndarray, bias: float, target_recall: float = 0.80
) -> float:
    """Find probability threshold that achieves target_recall on escalation class.

    Higher recall = escalate more conservatively (fewer false accepts of bad NPU output).
    Lower threshold = escalate more aggressively.
    """
    logits = X @ weights + bias
    probs = 1.0 / (1.0 + np.exp(-logits))

    # Sweep thresholds from high to low, pick lowest that meets target recall
    positives = y == 1
    n_pos = positives.sum()
    if n_pos == 0:
        return 0.5

    for threshold in np.linspace(0.9, 0.1, 80):
        predicted_pos = probs >= threshold
        tp = (predicted_pos & positives).sum()
        recall = tp / n_pos
        if recall >= target_recall:
            return float(threshold)

    return 0.5


def evaluate(X: np.ndarray, y: np.ndarray, weights: np.ndarray, bias: float, threshold: float):
    logits = X @ weights + bias
    probs = 1.0 / (1.0 + np.exp(-logits))
    predicted = (probs >= threshold).astype(int)

    positives = y == 1
    negatives = y == 0
    tp = ((predicted == 1) & positives).sum()
    fp = ((predicted == 1) & negatives).sum()
    tn = ((predicted == 0) & negatives).sum()
    fn = ((predicted == 0) & positives).sum()

    n = len(y)
    accuracy = (tp + tn) / n
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    escalation_rate = (tp + fp) / n

    print(f"  Samples    : {n} ({positives.sum()} should-escalate, {negatives.sum()} accept)")
    print(f"  Accuracy   : {accuracy:.1%}")
    print(f"  Precision  : {precision:.1%}  (of escalations, how many were right?)")
    print(f"  Recall     : {recall:.1%}  (of bad NPU outputs, how many caught?)")
    print(f"  Esc. rate  : {escalation_rate:.1%}  (target: <10%)")


def main():
    parser = argparse.ArgumentParser(description="Train the LYNX escalation probe")
    parser.add_argument("--data-dir", type=Path, default=_DATA_DIR)
    parser.add_argument("--output", type=Path, default=_PROBE_PATH)
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Fixed probability threshold (default: auto-select for 80%% recall)",
    )
    parser.add_argument(
        "--target-recall",
        type=float,
        default=0.80,
        help="Target recall for escalation class when auto-selecting threshold",
    )
    args = parser.parse_args()

    print(f"Loading data from {args.data_dir} ...")
    X, y = load_data(args.data_dir)
    print(f"Loaded {len(y)} samples")

    print("Training logistic regression probe ...")
    weights, bias = train_probe(X, y)

    if args.threshold is not None:
        threshold = args.threshold
        print(f"Using fixed threshold: {threshold}")
    else:
        threshold = find_threshold(X, y, weights, bias, target_recall=args.target_recall)
        print(f"Auto-selected threshold: {threshold:.3f}  (target recall={args.target_recall:.0%})")

    print("\nTraining-set evaluation:")
    evaluate(X, y, weights, bias, threshold)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    np.savez(args.output, weights=weights, bias=np.float32(bias), threshold=np.float32(threshold))
    print(f"\nProbe saved to {args.output}")
    print("To use: LYNXGate.from_probe() will auto-load the trained weights.")


if __name__ == "__main__":
    main()
