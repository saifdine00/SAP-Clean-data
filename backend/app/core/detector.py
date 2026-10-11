"""
Anomaly Detection Engine.

Scans a pandas DataFrame and returns a list of anomaly dicts ready to be
persisted as Anomaly ORM objects.

Detection categories:
  1. Exact duplicates
  2. Near-duplicates (fuzzy match on name columns)
  3. Duplicate SIRET with different names
  4. Format validation  (SIRET, SIREN, IBAN, email, phone, date, amount)
  5. Missing required fields
  6. SAP-specific rules (payment terms, account groups, field lengths, chars)
"""

from __future__ import annotations

import re
import uuid
import logging
from typing import Any
import pandas as pd
from fuzzywuzzy import fuzz

from app.core.validator import (
    get_required_fields,
    is_valid_payment_terms,
    is_valid_account_group,
    get_max_length,
    has_forbidden_chars,
    SAP_FIELD_MAX_LENGTHS,
)

logger = logging.getLogger(__name__)

# ── Column-name heuristics ─────────────────────────────────────────────────────

_SIRET_COLS    = {"siret", "siret_number", "num_siret", "numéro_siret"}
_SIREN_COLS    = {"siren", "siren_number", "num_siren"}
_IBAN_COLS     = {"iban", "bank_iban", "rib_iban"}
_EMAIL_COLS    = {"email", "e_mail", "mail", "courriel", "email_address"}
_PHONE_COLS    = {"phone", "telephone", "tel", "téléphone", "mobile", "fax"}
_DATE_COLS     = {"date", "birth_date", "invoice_date", "start_date", "end_date", "creation_date"}
_AMOUNT_COLS   = {"amount", "montant", "price", "prix", "total", "balance", "solde"}
_NAME_COLS     = {"vendor_name", "supplier_name", "name", "nom", "company", "raison_sociale"}
_PAYMENT_COLS  = {"payment_terms", "paymentterms", "cond_paiement", "terms"}
_ACCOUNT_COLS  = {"account_group", "accountgroup", "groupe_compte", "acct_grp"}
_CURRENCY_COLS = {"currency", "devise", "cur", "currency_code"}

FUZZY_THRESHOLD = 85  # 0-100; pairs above this are near-dupes


# ── Regex patterns ─────────────────────────────────────────────────────────────

_RE_SIRET  = re.compile(r"^\d{14}$")
_RE_SIREN  = re.compile(r"^\d{9}$")
_RE_EMAIL  = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_PHONE_FR = re.compile(r"^(?:\+33|0033|0)[1-9](?:[\s.\-]?\d{2}){4}$")
_RE_IBAN   = re.compile(r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$")
_RE_DATE_DMY = re.compile(r"^\d{1,2}/\d{1,2}/\d{2,4}$")
_RE_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_DATE_MDY = re.compile(r"^\d{1,2}-\d{1,2}-\d{2,4}$")


# ── Public entry-point ─────────────────────────────────────────────────────────

def detect_anomalies(session_id: str, df: pd.DataFrame) -> list[dict]:
    """
    Run all detection rules on the DataFrame.
    Returns a list of anomaly dicts (one per issue).
    """
    anomalies: list[dict] = []
    cols_lower = {c.lower().replace(" ", "_").replace("-", "_"): c for c in df.columns}

    # -- 1. Exact duplicates ---------------------------------------------------
    _detect_exact_duplicates(session_id, df, anomalies)

    # -- 2. Near-duplicates on name columns ------------------------------------
    name_col = _find_col(cols_lower, _NAME_COLS)
    if name_col:
        _detect_near_duplicates(session_id, df, name_col, anomalies)

    # -- 3. Duplicate SIRET with different names --------------------------------
    siret_col = _find_col(cols_lower, _SIRET_COLS)
    if siret_col and name_col:
        _detect_siret_name_mismatch(session_id, df, siret_col, name_col, anomalies)

    # -- 4. Format validations -------------------------------------------------
    if siret_col:
        _validate_siret(session_id, df, siret_col, anomalies)
    siren_col = _find_col(cols_lower, _SIREN_COLS)
    if siren_col:
        _validate_siren(session_id, df, siren_col, anomalies)
    iban_col = _find_col(cols_lower, _IBAN_COLS)
    if iban_col:
        _validate_iban(session_id, df, iban_col, anomalies)
    email_col = _find_col(cols_lower, _EMAIL_COLS)
    if email_col:
        _validate_email(session_id, df, email_col, anomalies)
    phone_col = _find_col(cols_lower, _PHONE_COLS)
    if phone_col:
        _validate_phone(session_id, df, phone_col, anomalies)
    for col_key in _DATE_COLS:
        real_col = _find_col(cols_lower, {col_key})
        if real_col:
            _validate_dates(session_id, df, real_col, anomalies)
    for col_key in _AMOUNT_COLS:
        real_col = _find_col(cols_lower, {col_key})
        if real_col:
            _validate_amounts(session_id, df, real_col, anomalies)

    # -- 5. Missing required fields --------------------------------------------
    _detect_missing_required(session_id, df, cols_lower, anomalies)

    # -- 6. SAP-specific validation --------------------------------------------
    pay_col = _find_col(cols_lower, _PAYMENT_COLS)
    if pay_col:
        _validate_payment_terms(session_id, df, pay_col, anomalies)
    acct_col = _find_col(cols_lower, _ACCOUNT_COLS)
    if acct_col:
        _validate_account_group(session_id, df, acct_col, anomalies)
    _validate_field_lengths(session_id, df, cols_lower, anomalies)
    _validate_special_chars(session_id, df, cols_lower, anomalies)

    logger.info("Detection complete: %d anomalies found for session %s", len(anomalies), session_id)
    return anomalies


# ── Helper: map column ─────────────────────────────────────────────────────────

def _find_col(cols_lower: dict[str, str], targets: set[str]) -> str | None:
    for t in targets:
        if t in cols_lower:
            return cols_lower[t]
    return None


def _mk(session_id: str, row_index: int, column_name: str, anomaly_type: str,
         original_value: Any, suggested_value: Any, confidence: float, message: str) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "row_index": row_index,
        "column_name": column_name,
        "anomaly_type": anomaly_type,
        "original_value": str(original_value) if original_value is not None else "",
        "suggested_value": str(suggested_value) if suggested_value is not None else None,
        "confidence": confidence,
        "message": message,
        "status": "pending",
        "corrected_value": None,
    }


# ── Detection functions ────────────────────────────────────────────────────────

def _detect_exact_duplicates(session_id: str, df: pd.DataFrame, out: list):
    dup_mask = df.duplicated(keep="first")
    dup_indices = df.index[dup_mask].tolist()
    for idx in dup_indices:
        out.append(_mk(
            session_id, int(idx), "_all_",
            "duplicate_exact",
            f"Row {idx}",
            None, 1.0,
            "This row is an exact duplicate of a previous row and can be safely removed.",
        ))


def _detect_near_duplicates(session_id: str, df: pd.DataFrame, col: str, out: list):
    values = df[col].fillna("").tolist()
    reported: set[tuple] = set()
    for i in range(len(values)):
        for j in range(i + 1, len(values)):
            v1, v2 = str(values[i]).strip(), str(values[j]).strip()
            if not v1 or not v2 or v1 == v2:
                continue
            score = fuzz.token_sort_ratio(v1.lower(), v2.lower())
            if score >= FUZZY_THRESHOLD:
                pair = (min(i, j), max(i, j))
                if pair not in reported:
                    reported.add(pair)
                    out.append(_mk(
                        session_id, j, col,
                        "duplicate_near",
                        v2, v1,
                        round(score / 100, 2),
                        f'Near-duplicate of row {i}: "{v1}" ≈ "{v2}" (similarity {score}%)',
                    ))


def _detect_siret_name_mismatch(session_id: str, df: pd.DataFrame, siret_col: str, name_col: str, out: list):
    siret_to_names: dict[str, set] = {}
    for idx, row in df.iterrows():
        siret = str(row.get(siret_col, "")).strip()
        name  = str(row.get(name_col, "")).strip()
        if siret and name:
            siret_to_names.setdefault(siret, set()).add(name)
    for siret, names in siret_to_names.items():
        if len(names) > 1:
            idx_list = df.index[df[siret_col] == siret].tolist()
            for idx in idx_list[1:]:
                out.append(_mk(
                    session_id, int(idx), siret_col,
                    "duplicate_siret",
                    siret, None, 0.9,
                    f"SIRET {siret} appears with multiple company names: {names}",
                ))


def _luhn_siret(siret: str) -> bool:
    """Validate SIRET using Luhn algorithm."""
    digits = [int(d) for d in siret]
    total = 0
    for i, d in enumerate(digits):
        if i % 2 == 0:
            doubled = d * 2
            total += doubled - 9 if doubled > 9 else doubled
        else:
            total += d
    return total % 10 == 0


def _validate_siret(session_id: str, df: pd.DataFrame, col: str, out: list):
    for idx, val in df[col].items():
        v = str(val).strip().replace(" ", "")
        if not v:
            continue
        if not _RE_SIRET.match(v):
            out.append(_mk(session_id, int(idx), col, "invalid_siret", val, None, 0.0,
                           f"SIRET must be exactly 14 digits. Got: '{v}'"))
        elif not _luhn_siret(v):
            out.append(_mk(session_id, int(idx), col, "invalid_siret", val, None, 0.3,
                           f"SIRET '{v}' fails the Luhn checksum validation."))


def _validate_siren(session_id: str, df: pd.DataFrame, col: str, out: list):
    for idx, val in df[col].items():
        v = str(val).strip().replace(" ", "")
        if not v:
            continue
        if not _RE_SIREN.match(v):
            out.append(_mk(session_id, int(idx), col, "invalid_siren", val, None, 0.0,
                           f"SIREN must be exactly 9 digits. Got: '{v}'"))


def _iban_checksum(iban: str) -> bool:
    """Validate IBAN mod-97 checksum."""
    iban = iban.upper().replace(" ", "")
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(numeric) % 97 == 1


def _validate_iban(session_id: str, df: pd.DataFrame, col: str, out: list):
    for idx, val in df[col].items():
        v = str(val).strip().upper().replace(" ", "")
        if not v:
            continue
        if not _RE_IBAN.match(v):
            out.append(_mk(session_id, int(idx), col, "invalid_iban", val, None, 0.0,
                           f"IBAN format is invalid. Got: '{val}'"))
        elif not _iban_checksum(v):
            out.append(_mk(session_id, int(idx), col, "invalid_iban", val, None, 0.2,
                           f"IBAN '{val}' fails the mod-97 checksum."))


def _validate_email(session_id: str, df: pd.DataFrame, col: str, out: list):
    for idx, val in df[col].items():
        v = str(val).strip()
        if not v:
            continue
        if not _RE_EMAIL.match(v):
            out.append(_mk(session_id, int(idx), col, "invalid_email", val, None, 0.1,
                           f"'{val}' is not a valid email address."))


def _normalize_phone_fr(v: str) -> str:
    """Attempt to normalize a French phone number to 0X XX XX XX XX format."""
    v = re.sub(r"[\s.\-()]", "", v)
    if v.startswith("+33"):
        v = "0" + v[3:]
    elif v.startswith("0033"):
        v = "0" + v[4:]
    groups = [v[i:i+2] for i in range(0, len(v), 2)]
    return " ".join(groups)


def _validate_phone(session_id: str, df: pd.DataFrame, col: str, out: list):
    for idx, val in df[col].items():
        v = str(val).strip()
        if not v:
            continue
        normalized = re.sub(r"[\s.\-()]", "", v)
        if normalized.startswith("+33"):
            normalized = "0" + normalized[3:]
        elif normalized.startswith("0033"):
            normalized = "0" + normalized[4:]
        if not re.match(r"^0[1-9]\d{8}$", normalized):
            out.append(_mk(session_id, int(idx), col, "invalid_phone", val,
                           _normalize_phone_fr(v), 0.5,
                           f"'{val}' is not a valid French phone number."))


def _detect_date_format(v: str) -> str | None:
    if _RE_DATE_ISO.match(v):
        return "ISO"
    if _RE_DATE_DMY.match(v):
        return "DMY"
    if _RE_DATE_MDY.match(v):
        return "MDY"
    return None


def _validate_dates(session_id: str, df: pd.DataFrame, col: str, out: list):
    formats_found: set[str] = set()
    format_by_row: dict[int, str] = {}
    for idx, val in df[col].items():
        v = str(val).strip()
        if not v:
            continue
        fmt = _detect_date_format(v)
        if fmt:
            formats_found.add(fmt)
            format_by_row[int(idx)] = fmt
        else:
            out.append(_mk(session_id, int(idx), col, "invalid_date", val, None, 0.0,
                           f"Unrecognised date format: '{val}'"))

    if len(formats_found) > 1:
        dominant = max(set(format_by_row.values()), key=list(format_by_row.values()).count)
        for idx, fmt in format_by_row.items():
            if fmt != dominant:
                val = df[col].iloc[idx]
                out.append(_mk(session_id, idx, col, "invalid_date", val, None, 0.6,
                               f"Inconsistent date format: '{val}' (format {fmt} vs dominant {dominant})"))


def _validate_amounts(session_id: str, df: pd.DataFrame, col: str, out: list):
    has_comma_decimal = False
    has_dot_decimal = False
    for idx, val in df[col].items():
        v = str(val).strip()
        if not v:
            continue
        if re.search(r"\d,\d{1,2}$", v) or re.search(r"\d,\d{3}", v):
            # Ambiguous: could be European decimal or thousand separator
            if re.match(r"^\d{1,3}(\.\d{3})*(,\d{1,2})?$", v):
                has_comma_decimal = True
            elif re.match(r"^\d{1,3}(,\d{3})*(\.\d{1,2})?$", v):
                has_dot_decimal = True
        if has_comma_decimal and has_dot_decimal:
            out.append(_mk(session_id, int(idx), col, "invalid_amount", val, None, 0.5,
                           f"Mixed decimal separators detected in column '{col}'."))
        # Check for multiple currency symbols
        currency_symbols = re.findall(r"[$€£¥₹]", v)
        if len(set(currency_symbols)) > 1:
            out.append(_mk(session_id, int(idx), col, "mixed_currency", val, None, 0.8,
                           f"Multiple currency symbols in '{val}'."))


def _detect_missing_required(session_id: str, df: pd.DataFrame, cols_lower: dict, out: list):
    required = get_required_fields()
    for req in required:
        real_col = _find_col(cols_lower, {req})
        if real_col is None:
            # Column doesn't exist at all — flag each row
            for idx in df.index:
                out.append(_mk(session_id, int(idx), req, "missing_required",
                               None, None, 1.0,
                               f"Required SAP field '{req}' is missing from the file."))
        else:
            for idx, val in df[real_col].items():
                v = str(val).strip() if val is not None else ""
                if not v or v in ("nan", "None", ""):
                    out.append(_mk(session_id, int(idx), real_col, "missing_required",
                                   None, None, 1.0,
                                   f"Required field '{real_col}' is empty."))


def _validate_payment_terms(session_id: str, df: pd.DataFrame, col: str, out: list):
    for idx, val in df[col].items():
        v = str(val).strip()
        if not v:
            continue
        if not is_valid_payment_terms(v):
            out.append(_mk(session_id, int(idx), col, "invalid_payment_terms", val, None, 0.0,
                           f"'{v}' is not a recognised SAP payment terms code."))


def _validate_account_group(session_id: str, df: pd.DataFrame, col: str, out: list):
    for idx, val in df[col].items():
        v = str(val).strip()
        if not v:
            continue
        if not is_valid_account_group(v):
            out.append(_mk(session_id, int(idx), col, "invalid_account_group", val, None, 0.0,
                           f"'{v}' is not a recognised SAP account group code."))


def _validate_field_lengths(session_id: str, df: pd.DataFrame, cols_lower: dict, out: list):
    for field, max_len in SAP_FIELD_MAX_LENGTHS.items():
        real_col = _find_col(cols_lower, {field})
        if real_col is None:
            continue
        for idx, val in df[real_col].items():
            v = str(val).strip() if val else ""
            if len(v) > max_len:
                truncated = v[:max_len]
                out.append(_mk(session_id, int(idx), real_col, "field_too_long",
                               val, truncated, 0.9,
                               f"Value exceeds SAP max length of {max_len} for '{real_col}' ({len(v)} chars)."))


def _validate_special_chars(session_id: str, df: pd.DataFrame, cols_lower: dict, out: list):
    for col in df.columns:
        for idx, val in df[col].items():
            v = str(val) if val else ""
            found, bad_chars = has_forbidden_chars(v)
            if found:
                cleaned = v
                for ch in bad_chars:
                    cleaned = cleaned.replace(ch, "")
                out.append(_mk(session_id, int(idx), col, "special_characters",
                               val, cleaned, 0.95,
                               f"SAP-incompatible characters found: {[repr(c) for c in bad_chars]}"))
