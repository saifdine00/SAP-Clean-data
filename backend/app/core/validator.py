"""
SAP-specific validation rules.

This module defines:
  - Configurable required fields per SAP object type
  - Configurable SAP payment terms and account group codes
  - Field length limits per SAP field
  - Special-character blacklist for SAP input
"""

from __future__ import annotations
from typing import Set

# ── SAP configurable constants ─────────────────────────────────────────────────

# Fields that MUST be non-empty for a vendor master record
SAP_REQUIRED_FIELDS: list[str] = [
    "vendor_name",
    "siret",
    "payment_terms",
    "account_group",
]

# Valid SAP payment term codes (extend as needed)
SAP_PAYMENT_TERMS: Set[str] = {
    "0001", "0002", "0003", "0004", "0005",
    "NT30", "NT60", "NT90", "NT45",
    "NET30", "NET60", "NET90", "NET45",
    "IM", "CASH", "COD", "IMMED",
    "Z001", "Z002", "Z003", "Z004", "Z005",
    "Z010", "Z015", "Z030", "Z045", "Z060",
    "Z090", "Z120",
}

# Valid SAP vendor account group codes
SAP_ACCOUNT_GROUPS: Set[str] = {
    "KRED",   # Standard vendor
    "LIEF",   # Supplier
    "FREI",   # Free vendor (one-time)
    "INTE",   # Intercompany
    "EXTE",   # External
    "Z001", "Z002", "Z003", "Z004",
}

# SAP field length constraints (field_name → max_length)
SAP_FIELD_MAX_LENGTHS: dict[str, int] = {
    "vendor_name":    35,
    "street":         35,
    "city":           35,
    "postal_code":    10,
    "country":         3,
    "phone":          30,
    "email":         241,
    "payment_terms":   4,
    "account_group":   4,
    "siret":          20,
    "siren":          15,
    "iban":           34,
    "swift":          11,
    "currency":        5,
    "tax_number":     18,
}

# Characters rejected by SAP in most text fields
SAP_FORBIDDEN_CHARS: set[str] = set('&<>"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f')

# ── Utility helpers ────────────────────────────────────────────────────────────

def get_required_fields() -> list[str]:
    return list(SAP_REQUIRED_FIELDS)


def is_valid_payment_terms(code: str) -> bool:
    return code.strip().upper() in {v.upper() for v in SAP_PAYMENT_TERMS}


def is_valid_account_group(code: str) -> bool:
    return code.strip().upper() in {v.upper() for v in SAP_ACCOUNT_GROUPS}


def get_max_length(field_name: str) -> int | None:
    """Return max SAP field length or None if not constrained."""
    key = field_name.strip().lower().replace(" ", "_")
    return SAP_FIELD_MAX_LENGTHS.get(key)


def has_forbidden_chars(value: str) -> tuple[bool, list[str]]:
    """Return (has_issues, list_of_bad_chars)."""
    found = [ch for ch in SAP_FORBIDDEN_CHARS if ch in value]
    return bool(found), found
