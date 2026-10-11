import chardet
import io
import json
import pandas as pd
from typing import Tuple
import logging

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".xlsx", ".xls", ".csv", ".json"}


def detect_encoding(raw_bytes: bytes) -> str:
    """Detect file encoding using chardet."""
    result = chardet.detect(raw_bytes)
    encoding = result.get("encoding") or "utf-8"
    # Normalize common aliases
    if encoding.lower() in ("ascii",):
        encoding = "utf-8"
    return encoding


def parse_file(filename: str, raw_bytes: bytes) -> Tuple[pd.DataFrame, str]:
    """
    Parse an uploaded file into a DataFrame.
    Returns (dataframe, detected_format).
    Supports: .xlsx, .xls, .csv, .json
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext in (".xlsx", ".xls"):
        return _parse_excel(raw_bytes, ext), ext.lstrip(".")
    elif ext == ".csv":
        return _parse_csv(raw_bytes), "csv"
    elif ext == ".json":
        return _parse_json(raw_bytes), "json"
    else:
        raise ValueError(f"Unsupported file format: '{ext}'. Accepted: .xlsx, .xls, .csv, .json")


def _parse_excel(raw_bytes: bytes, ext: str) -> pd.DataFrame:
    buf = io.BytesIO(raw_bytes)
    engine = "openpyxl" if ext == ".xlsx" else "xlrd"
    df = pd.read_excel(buf, engine=engine, dtype=str)
    df = _clean_dataframe(df)
    return df


def _parse_csv(raw_bytes: bytes) -> pd.DataFrame:
    encoding = detect_encoding(raw_bytes)
    text = raw_bytes.decode(encoding, errors="replace")
    buf = io.StringIO(text)

    # Try to detect separator: comma, semicolon, tab, pipe
    sample = text[:4096]
    sep = _detect_separator(sample)

    df = pd.read_csv(buf, sep=sep, dtype=str, encoding=None)
    df = _clean_dataframe(df)
    return df


def _detect_separator(sample: str) -> str:
    counts = {
        ",": sample.count(","),
        ";": sample.count(";"),
        "\t": sample.count("\t"),
        "|": sample.count("|"),
    }
    return max(counts, key=counts.get)


def _parse_json(raw_bytes: bytes) -> pd.DataFrame:
    encoding = detect_encoding(raw_bytes)
    text = raw_bytes.decode(encoding, errors="replace")
    data = json.loads(text)
    if isinstance(data, list):
        df = pd.DataFrame(data)
    elif isinstance(data, dict):
        # Try records, data, or root keys
        for key in ("records", "data", "rows", "items"):
            if key in data and isinstance(data[key], list):
                df = pd.DataFrame(data[key])
                break
        else:
            df = pd.DataFrame([data])
    else:
        raise ValueError("JSON must contain an array or object with a records key")
    df = df.astype(str)
    df = _clean_dataframe(df)
    return df


def _clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace, drop fully-empty rows/cols, normalize column names."""
    # Drop fully empty rows
    df = df.dropna(how="all").reset_index(drop=True)
    # Drop empty columns
    valid_cols = [c for c in df.columns if str(c).strip() != ""]
    df = df[valid_cols]

    # Strip whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # Strip whitespace from string cells
    for col in df.columns:
        df[col] = df[col].apply(lambda v: v.strip() if isinstance(v, str) else v)

    # Replace pandas NA/NaN string representations with empty string
    df = df.replace({"nan": "", "NaN": "", "None": "", "NaT": ""})
    return df


def parse_pasted_text(text: str) -> Tuple[pd.DataFrame, str]:
    """
    Parse raw pasted text (JSON, TSV, or CSV).
    Returns (dataframe, "paste").
    """
    stripped = text.strip()
    if stripped.startswith(("[", "{")):
        try:
            return _parse_json(stripped.encode("utf-8")), "paste"
        except Exception:
            pass

    buf = io.StringIO(text)
    sep = _detect_separator(text[:4096])
    df = pd.read_csv(buf, sep=sep, dtype=str)
    df = _clean_dataframe(df)
    return df, "paste"


def dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert DataFrame to list of dicts, replacing NaN with None."""
    return df.where(pd.notna(df), None).to_dict(orient="records")
