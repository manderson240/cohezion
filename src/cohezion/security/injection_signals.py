"""Prompt-injection detection signals: normalization + intent-directed phrases.

Replaces a six-substring blocklist that failed in both directions at once, because
matching raw text has no notion of meaning:

* **Evasion.** Any semantic-preserving transform walked past it. Measured against our own
  OWASP corpus, the old guard caught 9 of 106 attacks (8.5%); ROT13, Base64, leetspeak,
  character-stream and multilingual variants all evaded. Worst case, ``"ignore previous"``
  matched *zero* corpus attacks -- the corpus says "Ignore **all** previous instructions",
  and one interposed word breaks a literal substring.
* **False positives.** Bare words ``override`` / ``bypass`` / ``disregard`` are ordinary
  engineering vocabulary. 4 of 7 realistic task descriptions were blocked, and a BLOCK
  hard-fails the task before execution.

Two corrections, one per direction:

1. :func:`normalize_variants` folds a text into the forms an attacker would use to hide
   the same words, so the matcher sees through the transform.
2. :data:`INJECTION_PATTERNS` matches *instruction-directed* phrases rather than bare
   words. The distinguishing feature of an injection is that it addresses the model's
   own instructions or constraints -- "override **your** alignment", not "override the
   default timeout". `\\W+` between tokens tolerates the filler that broke the literal.

Deliberately NOT an arms race: decoding is limited to the transforms that actually
appear in the corpus. Encoding obfuscation is unbounded, so this narrows the gap, it does
not close it. The ratchet in tests/security/test_production_guardrail_ratchet.py is what
tells you where the gap actually is.
"""

from __future__ import annotations

import base64
import codecs
import re
import unicodedata


# Instruction-directed phrases. Each requires the loaded verb AND a target that refers to
# the model's own instructions/constraints -- which is what separates an attack from
# ordinary prose. `\W+` (not `\s+`) also absorbs the character-stream spacing variant.
_FILLER = r"(?:\W+\w+){0,3}\W+"
_PATTERN_SOURCES: list[tuple[str, str]] = [
    # "ignore/forget/disregard [all|the above|your] previous ... instructions/rules"
    (
        "ignore_previous",
        rf"(?:ignore|disregard|forget){_FILLER}"
        rf"(?:previous|prior|above|earlier|initial|original|system)",
    ),
    # "ignore/forget everything above"
    ("ignore_everything", rf"(?:ignore|disregard|forget){_FILLER}(?:everything|all)"),
    # instructions are "cancelled/void/no longer apply"
    (
        "instructions_void",
        r"instructions?\W+(?:are|is)\W+(?:canceled|cancelled|void|revoked|no\W+longer)",
    ),
    # Asking for the system prompt -- but only with an EXFILTRATION VERB. A bare
    # "system prompt" is weak evidence: it blocked "Add a test for the system prompt
    # template loader", a legitimate task, which is precisely the class of false
    # positive that hard-fails real work. The verb is what separates asking-for-it
    # from talking-about-it.
    (
        "reveal_instructions",
        rf"(?:reveal|print|show|repeat|output|dump|give\W+me|tell\W+me)"
        rf"{_FILLER}(?:instructions?|prompt|rules)",
    ),
    # jailbreak / persona-swap framings
    ("jailbreak", r"jail\W*break"),
    (
        "no_restrictions",
        r"(?:without|no|drop\W+all|remove\W+all)\W+"
        r"(?:restrictions?|limitations?|filters?|guardrails?|content\W+polic)",
    ),
    (
        "act_as_unrestricted",
        r"(?:you\W+are\W+now|pretend|act\W+as\W+if|roleplay)"
        rf"{_FILLER}(?:dan|unrestricted|no\W+content|without\W+restriction)",
    ),
    # verb + POSSESSIVE/system target -- "override YOUR alignment", not "override the timeout"
    (
        "override_constraints",
        r"(?:override|bypass|circumvent|disable|ignore)\W+"
        r"(?:your|the\W+model|all)?\W*"
        r"(?:safety|alignment|guardrail|content\W+polic|restriction|"
        r"constraint|filter|safeguard|rule)",
    ),
]

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (name, re.compile(src, re.IGNORECASE)) for name, src in _PATTERN_SOURCES
]

_LEET = str.maketrans(
    {"1": "i", "0": "o", "3": "e", "@": "a", "4": "a", "5": "s", "7": "t", "$": "s"}
)
_B64 = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


def _decode_base64(text: str) -> str | None:
    """Decode any long base64-looking run. Attackers wrap the payload, not the sentence."""
    out = []
    for candidate in _B64.findall(text):
        try:
            padded = candidate + "=" * (-len(candidate) % 4)
            decoded = base64.b64decode(padded, validate=True).decode("utf-8", errors="strict")
        except ValueError:
            continue
        if decoded.isprintable():
            out.append(decoded)
    return " ".join(out) if out else None


def normalize_variants(text: str) -> list[str]:
    """Return the text plus the decoded/folded forms a matcher should also see.

    Always includes the original as element 0, so a caller that only checks ``[0]``
    degrades to the old raw-text behaviour rather than to no behaviour.
    """
    variants = [text]

    # Unicode fold: NFKD strips combining marks and maps fullwidth/compatibility forms,
    # which defeats homoglyph substitution without a per-character lookup table.
    folded = unicodedata.normalize("NFKD", text)
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    if folded != text:
        variants.append(folded)

    lowered = folded.lower()
    deleet = lowered.translate(_LEET)
    if deleet != lowered:
        variants.append(deleet)

    # Character-stream ("i g n o r e"): collapse runs of single chars separated by spaces.
    destreamed = re.sub(r"\b(?:(\w) )+(\w)\b", lambda m: m.group(0).replace(" ", ""), lowered)
    if destreamed != lowered:
        variants.append(destreamed)

    rot13 = codecs.decode(text, "rot13")
    variants.append(rot13)

    decoded = _decode_base64(text)
    if decoded:
        variants.append(decoded)

    return variants


def find_injection(text: str) -> str | None:
    """Return the name of the first matching injection signal, or None.

    Returns a NAME rather than a bool so the blocking reason is specific enough to
    debug, and so a regression names the rule that was lost.
    """
    if not text:
        return None
    for variant in normalize_variants(text):
        for name, pattern in INJECTION_PATTERNS:
            if pattern.search(variant):
                return name
    return None
