"""
Encoding detection utility — thin wrapper around chardet.
Kept here for convenience and future extension.
"""
import chardet


def detect_encoding(raw_bytes: bytes) -> str:
    """Return the most likely encoding of the raw bytes."""
    result = chardet.detect(raw_bytes)
    encoding = result.get("encoding") or "utf-8"
    if encoding.lower() in ("ascii",):
        return "utf-8"
    return encoding
