"""
preprocessing/cleaner.py

Cleans raw report text while preserving the original.

Checkpoint 2 (Phase 2): Python can clean reports.

We deliberately do NOT translate or strip Hinglish/multilingual text —
the multilingual sentence-transformer model handles that fine.
"""

import re


def clean_text(raw_text: str) -> str:
    """
    Turn raw, noisy report text into a cleaner version for embeddings.

    Example:
        "OMG!!! HEAVY RAIN in WHITEFIELD 😭😭 https://example.com"
        -> "omg heavy rain in whitefield"
    """
    if not raw_text:
        return ""

    text = raw_text

    # Remove URLs
    text = re.sub(r"http\S+|www\.\S+", "", text)

    # Remove emojis / non-ASCII symbols (keeps basic Latin + Devanagari-safe
    # since we don't want to destroy Hinglish/other-script text entirely —
    # this only strips emoji/pictograph ranges)
    text = re.sub(
        r"[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F1E6-\U0001F1FF]",
        "",
        text,
    )

    # Collapse excessive punctuation (e.g. "!!!" -> "!")
    text = re.sub(r"([!?.])\1+", r"\1", text)

    # Lowercase
    text = text.lower()

    # Collapse multiple spaces
    text = re.sub(r"\s+", " ", text).strip()

    return text


def clean_report(report: dict) -> dict:
    """
    Take a raw report dict (as read from MongoDB) and attach cleaned_text,
    preserving the original text.
    """
    original = report.get("text", "")
    report["original_text"] = original
    report["cleaned_text"] = clean_text(original)
    return report


if __name__ == "__main__":
    sample = "OMG!!! HEAVY RAIN in WHITEFIELD 😭😭 https://example.com"
    print("Raw:    ", sample)
    print("Cleaned:", clean_text(sample))
