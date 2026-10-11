from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import pandas as pd
import logging

from app.database import get_db
from app.models.session import UploadSession, Anomaly, CorrectionStatus
from app.models.anomaly import CorrectionRequest, BulkCorrectionRequest
from app.core.llm_service import get_llm_service
from app.core.corrector import rule_based_suggestion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/corrections", tags=["corrections"])


@router.patch("/{anomaly_id}")
async def apply_correction(
    anomaly_id: str,
    body: CorrectionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept, reject, or manually correct a single anomaly."""
    stmt = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(stmt)
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(404, f"Anomaly '{anomaly_id}' not found.")

    action = body.action.lower()
    if action == "accept":
        anomaly.status = CorrectionStatus.ACCEPTED
        anomaly.corrected_value = anomaly.suggested_value
    elif action == "reject":
        anomaly.status = CorrectionStatus.REJECTED
        anomaly.corrected_value = anomaly.original_value
    elif action == "manual":
        if body.manual_value is None:
            raise HTTPException(400, "manual_value is required for action='manual'")
        anomaly.status = CorrectionStatus.MANUAL
        anomaly.corrected_value = body.manual_value
    else:
        raise HTTPException(400, f"Invalid action '{action}'. Use: accept, reject, manual")

    await db.commit()
    return {"anomaly_id": anomaly_id, "status": anomaly.status.value}


@router.post("/bulk")
async def bulk_correct(body: BulkCorrectionRequest, db: AsyncSession = Depends(get_db)):
    """Apply multiple corrections at once."""
    results = []
    for req in body.corrections:
        stmt = select(Anomaly).where(Anomaly.id == req.anomaly_id)
        result = await db.execute(stmt)
        anomaly = result.scalar_one_or_none()
        if not anomaly:
            results.append({"anomaly_id": req.anomaly_id, "error": "not found"})
            continue

        action = req.action.lower()
        if action == "accept":
            anomaly.status = CorrectionStatus.ACCEPTED
            anomaly.corrected_value = anomaly.suggested_value
        elif action == "reject":
            anomaly.status = CorrectionStatus.REJECTED
            anomaly.corrected_value = anomaly.original_value
        elif action == "manual" and req.manual_value is not None:
            anomaly.status = CorrectionStatus.MANUAL
            anomaly.corrected_value = req.manual_value
        results.append({"anomaly_id": req.anomaly_id, "status": anomaly.status.value})

    await db.commit()
    return {"updated": len(results), "results": results}


@router.post("/bulk-accept-high-confidence")
async def bulk_accept_high_confidence(
    session_id: str,
    threshold: float = 0.8,
    db: AsyncSession = Depends(get_db),
):
    """Accept all pending corrections with confidence ≥ threshold."""
    stmt = (
        select(Anomaly)
        .where(Anomaly.session_id == session_id)
        .where(Anomaly.status == CorrectionStatus.PENDING)
        .where(Anomaly.confidence >= threshold)
        .where(Anomaly.suggested_value.isnot(None))
    )
    result = await db.execute(stmt)
    anomalies = result.scalars().all()

    for a in anomalies:
        a.status = CorrectionStatus.ACCEPTED
        a.corrected_value = a.suggested_value

    await db.commit()
    return {"accepted": len(anomalies)}


@router.post("/{anomaly_id}/llm-suggest")
async def llm_suggest(anomaly_id: str, db: AsyncSession = Depends(get_db)):
    """
    Request an LLM-powered correction suggestion for a specific anomaly.
    Calls llm_service.suggest_correction — never calls Gemini directly.
    """
    stmt = select(Anomaly).where(Anomaly.id == anomaly_id)
    result = await db.execute(stmt)
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(404, f"Anomaly '{anomaly_id}' not found.")

    # First try rule-based suggestion (fast, no API cost)
    rule_result = rule_based_suggestion(
        anomaly.original_value or "",
        anomaly.anomaly_type,
    )
    if rule_result.get("confidence", 0) >= 0.9:
        return {"source": "rules", **rule_result}

    # Fetch column sample values for context
    session_stmt = select(UploadSession).where(UploadSession.id == anomaly.session_id)
    s_result = await db.execute(session_stmt)
    session = s_result.scalar_one_or_none()
    column_values: list = []
    if session and session.raw_data:
        records = session.raw_data.get("records", [])
        column_values = [
            str(r.get(anomaly.column_name, ""))
            for r in records[:50]
            if r.get(anomaly.column_name)
        ]

    context = {
        "anomaly_type": anomaly.anomaly_type,
        "column_name": anomaly.column_name,
        "message": anomaly.message,
        "column_values": column_values,
    }

    llm = get_llm_service()
    suggestion = await llm.suggest_correction(anomaly.original_value or "", context)

    # Persist the suggestion
    if suggestion.get("suggested_value"):
        anomaly.suggested_value = suggestion["suggested_value"]
        anomaly.confidence = suggestion.get("confidence", 0.5)
        await db.commit()

    return {"source": "llm", **suggestion}
