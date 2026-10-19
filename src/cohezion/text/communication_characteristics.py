"""AA-PersonalityBench 21 Communication Characteristics Analyzer.

Grounding:
Artificial Analysis AA-PersonalityBench:
https://artificialanalysis.ai/articles/aa-personalitybench
https://artificialanalysis.ai/methodology/aa-personalitybench
https://artificialanalysis.ai/evaluations/aa-personalitybench

Measures 21 deterministic communication characteristics directly from prose:
1. Length (5): characters, words, sentences, paragraphs, avg_sentence_length
2. Structure (3): lists, headings, tables
3. Punctuation (8): em_dashes, contractions, exclamations, questions, parentheses, quotes, colons, ellipses
4. Emphasis & Surface (5): bold, italics, emojis, acronyms, ends_with_question
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any


# Abbreviations for sentence splitting
_ABBREVIATIONS = (
    "dr",
    "mr",
    "mrs",
    "ms",
    "prof",
    "vs",
    "e.g",
    "i.e",
    "u.s",
    "etc",
    "inc",
    "ltd",
    "jr",
    "sr",
    "fig",
    "al",
    "ref",
)

# Known contractions pattern (excluding possessives)
_CONTRACTIONS_RE = re.compile(
    r"\b(?:can't|won't|shan't|don't|doesn't|didn't|isn't|aren't|wasn't|weren't|haven't|hasn't|hadn't|"
    r"couldn't|shouldn't|wouldn't|mustn't|it's|that's|what's|there's|who's|where's|when's|why's|how's|"
    r"i'm|you're|we're|they're|i've|you've|we've|they've|i'll|you'll|he'll|she'll|we'll|they'll|"
    r"i'd|you'd|he'd|she'd|we'd|they'd|ain't|let's)\b",
    re.IGNORECASE,
)

# Acronym pattern: 2 or more uppercase letters or dotted uppercase
_ACRONYM_RE = re.compile(r"\b[A-Z]{2,}\b|\b(?:[A-Z]\.){2,}")

# Code block and URL removal patterns
_CODE_BLOCK_RE = re.compile(r"```[\s\S]*?```|`[^`\n]+`")
_URL_RE = re.compile(r"https?://\S+|www\.\S+")

# Markdown formatting
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*|__(.+?)__")
_ITALIC_RE = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d+\.)\s+", re.MULTILINE)
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$", re.MULTILINE)

# Punctuation patterns
_EM_DASH_RE = re.compile(r"—")
_ELLIPSIS_RE = re.compile(r"\.\.\.|…")
_PAREN_PAIR_RE = re.compile(r"\([^\(\)]*\)")
_QUOTE_PAIR_RE = re.compile(r'\"[^\"]*\"|\'[^\']*\'|«[^»]*»|“[^”]*”|‘[^’]*’')


def _is_emoji(char: str) -> bool:
    """Check if character belongs to an Emoji category."""
    category = unicodedata.category(char)
    # Symbols: Other (So) often contains emojis
    if category == "So":
        return True
    code = ord(char)
    # Common Unicode emoji blocks
    return (
        0x1F300 <= code <= 0x1F5FF  # Misc Symbols and Pictographs
        or 0x1F600 <= code <= 0x1F64F  # Emoticons
        or 0x1F680 <= code <= 0x1F6FF  # Transport and Map
        or 0x2600 <= code <= 0x26FF  # Misc symbols
        or 0x2700 <= code <= 0x27BF  # Dingbats
        or 0x1F900 <= code <= 0x1F9FF  # Supplemental Symbols and Pictographs
        or 0x1FA70 <= code <= 0x1FAFF  # Symbols and Pictographs Extended-A
    )


def count_emojis(text: str) -> int:
    """Count visible emoji characters in text."""
    return sum(1 for char in text if _is_emoji(char))


def split_sentences(prose: str) -> list[str]:
    """Rule-based sentence splitter that handles common abbreviations."""
    raw_sentences = re.split(r"(?<=[.!?])\s+", prose.strip())
    sentences: list[str] = []
    buf = ""
    for s in raw_sentences:
        if not s:
            continue
        if buf:
            buf += " " + s
        else:
            buf = s

        # Check if ending with a known abbreviation
        words = buf.rstrip(".!?").split()
        if words and words[-1].lower() in _ABBREVIATIONS:
            continue
        sentences.append(buf)
        buf = ""

    if buf:
        sentences.append(buf)
    return sentences


@dataclass(frozen=True, slots=True)
class CommunicationCharacteristics:
    """The 21 Communication Characteristics of AA-PersonalityBench.

    All metrics are programmatically measured directly from response prose.
    """

    # 1. Length
    characters: int
    words: int
    sentences: int
    paragraphs: int
    avg_sentence_length: float

    # 2. Structure
    lists: int
    headings: int
    tables: int

    # 3. Punctuation
    em_dashes: int
    contractions: int
    exclamations: int
    questions: int
    parentheses: int
    quotes: int
    colons: int
    ellipses: int

    # 4. Emphasis & Surface
    bold: int
    italics: int
    emojis: int
    acronyms: int
    ends_with_question: bool

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return asdict(self)


def analyze_communication_characteristics(text: str) -> CommunicationCharacteristics:
    """Programmatically measure the 21 communication characteristics from response text.

    Parameters
    ----------
    text : str
        The raw markdown or plaintext model response.

    Returns
    -------
    CommunicationCharacteristics
        Complete 21-metric dataclass matching AA-PersonalityBench specifications.
    """
    if not text or not text.strip():
        return CommunicationCharacteristics(
            characters=0,
            words=0,
            sentences=0,
            paragraphs=0,
            avg_sentence_length=0.0,
            lists=0,
            headings=0,
            tables=0,
            em_dashes=0,
            contractions=0,
            exclamations=0,
            questions=0,
            parentheses=0,
            quotes=0,
            colons=0,
            ellipses=0,
            bold=0,
            italics=0,
            emojis=0,
            acronyms=0,
            ends_with_question=False,
        )

    # 1. Structural elements from raw text
    list_count = len(_LIST_ITEM_RE.findall(text))
    heading_count = len(_HEADING_RE.findall(text))
    table_count = len(_TABLE_ROW_RE.findall(text))
    bold_count = len(_BOLD_RE.findall(text))
    italic_count = len(_ITALIC_RE.findall(text))

    # Clean prose by stripping code blocks and URLs
    clean_prose = _CODE_BLOCK_RE.sub(" ", text)
    clean_prose = _URL_RE.sub(" ", clean_prose)

    # Characters (spaces included after code and URLs removed)
    char_count = len(clean_prose)

    # Words (tokens with letter or digit; CJK count individually)
    words = re.findall(r"\b[\w\d'-]+\b|[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]", clean_prose)
    word_count = len(words)

    # Paragraphs (prose blocks separated by double newlines, excluding code and list items)
    raw_paras = [p.strip() for p in clean_prose.split("\n\n") if p.strip()]
    prose_paras = [
        p
        for p in raw_paras
        if not (p.startswith("#") or p.startswith("-") or p.startswith("*") or p.startswith("|"))
    ]
    para_count = max(1, len(prose_paras)) if word_count > 0 else 0

    # Sentences and average sentence length
    sentences = split_sentences(clean_prose)
    sentence_count = max(1, len(sentences)) if word_count > 0 else 0
    avg_sentence_len = round(word_count / sentence_count, 2) if sentence_count > 0 else 0.0

    # Punctuation counts
    em_dashes = len(_EM_DASH_RE.findall(clean_prose))
    contractions = len(_CONTRACTIONS_RE.findall(clean_prose))
    exclamations = clean_prose.count("!")
    questions = clean_prose.count("?")
    parentheses = len(_PAREN_PAIR_RE.findall(clean_prose))
    quotes = len(_QUOTE_PAIR_RE.findall(clean_prose))
    colons = clean_prose.count(":")
    ellipses = len(_ELLIPSIS_RE.findall(clean_prose))

    # Emphasis & Surface
    emojis = count_emojis(clean_prose)
    acronyms = len(_ACRONYM_RE.findall(clean_prose))

    stripped = text.strip()
    ends_with_q = stripped.endswith("?")

    return CommunicationCharacteristics(
        characters=char_count,
        words=word_count,
        sentences=sentence_count,
        paragraphs=para_count,
        avg_sentence_length=avg_sentence_len,
        lists=list_count,
        headings=heading_count,
        tables=table_count,
        em_dashes=em_dashes,
        contractions=contractions,
        exclamations=exclamations,
        questions=questions,
        parentheses=parentheses,
        quotes=quotes,
        colons=colons,
        ellipses=ellipses,
        bold=bold_count,
        italics=italic_count,
        emojis=emojis,
        acronyms=acronyms,
        ends_with_question=ends_with_q,
    )
