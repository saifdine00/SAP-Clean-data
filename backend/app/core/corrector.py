"""
Corrector — applies accepted/manual corrections to a DataFrame.
Also provides a rule-based correction helper that runs before the LLM call.
"""

from __future__ import annotations
import re
import pandas as pd
from typing import Any


def apply_corrections(df: pd.DataFrame, corrections: list[dict]) -> pd.DataFrame:
    """
    Apply a list of accepted corrections to a copy of the DataFrame.

    Each correction dict: {row_index, column_name, corrected_value}
    Returns a new DataFrame with all corrections applied.
    """
    result = df.copy()
    for c in corrections:
        row = c.get("row_index")
        col = c.get("column_name")
        val = c.get("corrected_value")
        if row is None or col is None or col not in result.columns:
            continue
        if 0 <= int(row) < len(result):
            result.at[int(row), col] = val
    return result


def rule_based_suggestion(value: str, anomaly_type: str) -> dict:
    """
    Fast rule-based correction for well-defined anomaly types.
    Returns a suggestion dict or empty dict if no rule applies.
    """
    v = str(value).strip()

    if anomaly_type == "invalid_phone":
        normalized = re.sub(r"[\s.\-()+]", "", v)
        if normalized.startswith("33") and len(normalized) == 11:
            normalized = "0" + normalized[2:]
        if len(normalized) == 10 and normalized.startswith("0"):
            formatted = " ".join([normalized[i:i+2] for i in range(0, 10, 2)])
            return {"suggested_value": formatted, "confidence": 0.85,
                    "explanation": "Reformatted to standard French phone format."}

    if anomaly_type == "invalid_siret":
        digits_only = re.sub(r"\D", "", v)
        if len(digits_only) == 14:
            return {"suggested_value": digits_only, "confidence": 0.9,
                    "explanation": "Removed non-digit characters from SIRET."}

    if anomaly_type == "invalid_siren":
        digits_only = re.sub(r"\D", "", v)
        if len(digits_only) == 9:
            return {"suggested_value": digits_only, "confidence": 0.9,
                    "explanation": "Removed non-digit characters from SIREN."}

    if anomaly_type == "invalid_iban":
        iban = re.sub(r"[\s]", "", v).upper()
        return {"suggested_value": iban, "confidence": 0.7,
                "explanation": "Removed whitespace and uppercased IBAN."}

    if anomaly_type == "invalid_email":
        normalized = v.lower().strip()
        return {"suggested_value": normalized, "confidence": 0.6,
                "explanation": "Lowercased and stripped email."}

    if anomaly_type == "special_characters":
        cleaned = re.sub(r'[&<>"\x00-\x08\x0b\x0c\x0e\x0f]', "", v)
        return {"suggested_value": cleaned, "confidence": 0.95,
                "explanation": "Removed SAP-incompatible special characters."}

    if anomaly_type == "field_too_long":
        # Truncation suggestion handled by detector; pass through
        pass

    return {}
