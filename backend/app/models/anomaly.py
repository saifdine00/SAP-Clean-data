from pydantic import BaseModel, Field
from typing import Optional, Any, List, Dict
from datetime import datetime
from enum import Enum


class AnomalyType(str, Enum):
    DUPLICATE_EXACT = "duplicate_exact"
    DUPLICATE_NEAR = "duplicate_near"
    DUPLICATE_SIRET = "duplicate_siret"
    INVALID_SIRET = "invalid_siret"
    INVALID_SIREN = "invalid_siren"
    INVALID_IBAN = "invalid_iban"
    INVALID_EMAIL = "invalid_email"
    INVALID_PHONE = "invalid_phone"
    INVALID_DATE = "invalid_date"
    INVALID_AMOUNT = "invalid_amount"
    MISSING_REQUIRED = "missing_required"
    INVALID_PAYMENT_TERMS = "invalid_payment_terms"
    INVALID_ACCOUNT_GROUP = "invalid_account_group"
    FIELD_TOO_LONG = "field_too_long"
    SPECIAL_CHARACTERS = "special_characters"
    MIXED_CURRENCY = "mixed_currency"


class AnomalySchema(BaseModel):
    id: str
    session_id: str
    row_index: int
    column_name: str
    anomaly_type: str
    original_value: Optional[str]
    suggested_value: Optional[str]
    confidence: float
    message: str
    status: str
    corrected_value: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class CorrectionRequest(BaseModel):
    anomaly_id: str
    action: str  # "accept", "reject", "manual"
    manual_value: Optional[str] = None


class BulkCorrectionRequest(BaseModel):
    corrections: List[CorrectionRequest]


class SessionSummary(BaseModel):
    id: str
    filename: str
    total_rows: int
    status: str
    created_at: datetime
    anomaly_count: int = 0
    anomalies_by_type: Dict[str, int] = Field(default_factory=dict)


class SessionDetailSchema(BaseModel):
    id: str
    filename: str
    original_format: str
    total_rows: int
    status: str
    created_at: datetime
    updated_at: datetime
    column_mapping: Dict[str, Any]
    summary: Dict[str, Any]
    anomalies: List[AnomalySchema] = []

    class Config:
        from_attributes = True
