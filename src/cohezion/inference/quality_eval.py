"""Task-specific quality evaluation for tiered inference routing.

Evaluates whether a tier's output is good enough to accept, or whether to
escalate to the next tier. Calibrated by output_type from task_classifier.

Design rule: rework costs 2-5x the original generation. Gates must be
strict enough to prevent bad output from passing, but loose enough to
avoid unnecessary escalation (which burns TTFT budget on the higher tier).

TTFT hierarchy (measured on AMD Strix Halo):
  NPU  (llama3.2-1b-FLM):   ~24ms  — XDNA2 SRAM, 42 TPS
  iGPU (Gemma-4-E4B):       ~200ms — ROCWMMA unified memory
  CPU  (Gemma-4-31B):        ~800ms — AVX-512 RAM
  Cloud (Sonnet):            ~800ms — network + server
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass


# Uncertainty markers that signal the model doesn't know the answer.
# Presence of these in a short response → escalate.
_UNCERTAINTY_MARKERS = (
    "i'm not sure",
    "i am not sure",
    "i don't know",
    "i do not know",
    "i cannot",
    "i can't determine",
    "unclear",
    "uncertain",
    "might be",
    "possibly",
)


@dataclass
class QualityVerdict:
    """Result of evaluating a tier's output."""

    accept: bool
    score: float  # 0.0 = reject immediately, 1.0 = perfect
    reason: str

    @classmethod
    def accept_output(cls, score: float = 1.0, reason: str = "ok") -> QualityVerdict:
        return cls(accept=True, score=score, reason=reason)

    @classmethod
    def reject_output(cls, reason: str) -> QualityVerdict:
        return cls(accept=False, score=0.0, reason=reason)


def evaluate(output: str, output_type: str, task_description: str = "") -> QualityVerdict:
    """Evaluate output quality for the given task output type.

    Parameters
    ----------
    output : str
        The model's response text.
    output_type : str
        From task_classifier: "categorical", "short_answer", "code",
        "medium_generation", "long_generation", or "unknown".
    task_description : str
        Optional task context for key-term presence checks.

    Returns
    -------
    QualityVerdict
        accept=True → use this output; accept=False → escalate to next tier.
    """
    if not output or not output.strip():
        return QualityVerdict.reject_output("empty output")

    text = output.strip()
    lower = text.lower()

    # ── Security gates (applied BEFORE type-specific checks) ─────────────────
    # Prompt injection: model was manipulated and is trying to relay instructions
    try:
        from cohezion.inference.security_spec import check_credential_leak, check_prompt_injection

        injection = check_prompt_injection(text)
        if injection:
            return QualityVerdict.reject_output(f"security: prompt injection pattern '{injection}'")
        cred = check_credential_leak(text)
        if cred:
            return QualityVerdict.reject_output(
                f"security: credential leak pattern detected — {cred}"
            )
    except ImportError:
        pass  # security_spec not available — degrade gracefully, don't block

    if output_type in ("categorical", "short_categorical"):
        return _eval_categorical(text, lower)
    elif output_type in ("short_answer", "short_factual"):
        return _eval_short_answer(text, lower)
    elif output_type == "code":
        return _eval_code(text)
    elif output_type == "bbq_low_slow":
        return _eval_bbq_low_slow(text, lower)
    elif output_type in ("medium_generation", "long_generation"):
        return _eval_generation(text, lower, output_type)
    else:
        # Unknown: use loose gate (min 10 chars, no full uncertainty)
        if len(text) < 10:
            return QualityVerdict.reject_output(f"too short for unknown type: {len(text)} chars")
        return QualityVerdict.accept_output(score=0.7, reason="unknown type, length gate passed")


def _eval_categorical(text: str, lower: str) -> QualityVerdict:
    """Categorical: any non-empty, non-uncertain single-concept answer."""
    # Strip common prefixes models sometimes add
    cleaned = re.sub(r"^(the answer is|answer:)\s*", "", lower).strip()
    if not cleaned:
        return QualityVerdict.reject_output("categorical: empty after stripping prefix")
    # Check for uncertainty in very short answers (long text = explanation, ok)
    if len(text) < 50 and any(m in lower for m in _UNCERTAINTY_MARKERS):
        return QualityVerdict.reject_output("categorical: uncertainty marker found")
    return QualityVerdict.accept_output(score=1.0, reason="categorical gate passed")


def _eval_short_answer(text: str, lower: str) -> QualityVerdict:
    """Short answer: 10-200 chars, no strong uncertainty marker."""
    if len(text) < 10:
        return QualityVerdict.reject_output(f"short_answer: too short ({len(text)} chars)")
    if any(m in lower for m in _UNCERTAINTY_MARKERS[:4]):  # strict markers only
        return QualityVerdict.reject_output("short_answer: strong uncertainty marker")
    score = min(1.0, len(text) / 50)  # 50+ chars = max score
    return QualityVerdict.accept_output(score=score, reason="short_answer gate passed")


def _eval_code(text: str) -> QualityVerdict:
    """Code: must contain parseable Python or identifiable code block."""
    # Extract code blocks
    code_blocks = re.findall(r"```(?:python)?\n?(.*?)```", text, re.DOTALL)
    candidate = "\n".join(code_blocks).strip() if code_blocks else text.strip()

    # Try Python parse
    try:
        ast.parse(candidate)
        return QualityVerdict.accept_output(score=1.0, reason="code: valid Python AST")
    except SyntaxError:
        pass

    # Fallback: has code-like markers?
    code_markers = ("def ", "class ", "import ", "return ", "for ", "if ", "while ")
    has_code = any(m in candidate for m in code_markers)
    if has_code and len(candidate) > 20:
        return QualityVerdict.accept_output(score=0.7, reason="code: has code markers")

    return QualityVerdict.reject_output("code: no parseable code found")


def _eval_generation(text: str, lower: str, output_type: str) -> QualityVerdict:
    """Medium/long generation: length gate + no strong uncertainty opener."""
    min_len = 100 if output_type == "medium_generation" else 300
    if len(text) < min_len:
        return QualityVerdict.reject_output(f"{output_type}: too short ({len(text)} < {min_len})")
    # Check if first sentence is an uncertainty disclaimer (escalate)
    first_sentence = text.split(".")[0].lower()
    if any(m in first_sentence for m in _UNCERTAINTY_MARKERS[:4]):
        return QualityVerdict.reject_output(f"{output_type}: opens with uncertainty")
    score = min(1.0, len(text) / (min_len * 3))
    return QualityVerdict.accept_output(score=score, reason=f"{output_type} gate passed")


def _eval_bbq_low_slow(text: str, lower: str) -> QualityVerdict:
    """BBQ Low-and-Slow: deeply rendered, unctuous output for very hard questions.

    Requirements:
    - Minimum 500 chars (renders the fat cap — substantial output)
    - Does NOT open with an uncertainty disclaimer
    - Contains at least 3 distinct sentences (measured by '. ')
    """
    if len(text) < 500:
        return QualityVerdict.reject_output(
            f"bbq_low_slow: too short ({len(text)} chars, need ≥ 500 for unctuous output)"
        )
    first_sentence = lower.split(".")[0]
    if any(m in first_sentence for m in _UNCERTAINTY_MARKERS[:4]):
        return QualityVerdict.reject_output("bbq_low_slow: opens with uncertainty — escalate")
    sentence_count = text.count(". ") + 1
    if sentence_count < 3:
        return QualityVerdict.reject_output(
            f"bbq_low_slow: only {sentence_count} sentences — needs more depth"
        )
    score = min(1.0, len(text) / 2000)  # full score at 2000+ chars
    return QualityVerdict.accept_output(
        score=score, reason="bbq_low_slow: unctuous output accepted"
    )


def ttft_budget_ms(output_type: str) -> float:
    """Maximum acceptable TTFT in ms before we skip this tier.

    If the tier is taking longer than this to produce the first token, the
    user experience degrades and we should fail fast.
    """
    return {
        "categorical": 200.0,
        "short_categorical": 200.0,
        "short_answer": 500.0,
        "short_factual": 500.0,
        "code": 2000.0,
        "medium_generation": 3000.0,
        "long_generation": 5000.0,
        "bbq_low_slow": float("inf"),  # no TTFT deadline — patience required
        "unknown": 1000.0,
    }.get(output_type, 1000.0)
