from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd

from app.database import get_db
from app.models.session import UploadSession, SessionStatus, Anomaly
from app.models.anomaly import SessionDetailSchema, AnomalySchema

router = APIRouter(prefix="/analyze", tags=["analyze"])


@router.get("/session/{session_id}")
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get full session details including anomalies."""
    stmt = select(UploadSession).where(UploadSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, f"Session '{session_id}' not found.")

    # Load anomalies
    a_stmt = select(Anomaly).where(Anomaly.session_id == session_id).order_by(Anomaly.row_index)
    a_result = await db.execute(a_stmt)
    anomalies = a_result.scalars().all()

    return {
        "id": session.id,
        "filename": session.filename,
        "original_format": session.original_format,
        "total_rows": session.total_rows,
        "status": session.status.value,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "column_mapping": session.column_mapping,
        "summary": session.summary,
        "anomalies": [
            {
                "id": a.id,
                "session_id": a.session_id,
                "row_index": a.row_index,
                "column_name": a.column_name,
                "anomaly_type": a.anomaly_type,
                "original_value": a.original_value,
                "suggested_value": a.suggested_value,
                "confidence": a.confidence,
                "message": a.message,
                "status": a.status.value,
                "corrected_value": a.corrected_value,
                "created_at": a.created_at.isoformat(),
            }
            for a in anomalies
        ],
    }


@router.get("/sessions")
async def list_sessions(db: AsyncSession = Depends(get_db)):
    """List all upload sessions ordered by creation date descending."""
    stmt = select(UploadSession).order_by(UploadSession.created_at.desc()).limit(50)
    result = await db.execute(stmt)
    sessions = result.scalars().all()
    return [
        {
            "id": s.id,
            "filename": s.filename,
            "total_rows": s.total_rows,
            "status": s.status.value,
            "created_at": s.created_at.isoformat(),
            "summary": s.summary,
        }
        for s in sessions
    ]


@router.get("/session/{session_id}/status")
async def get_session_status(session_id: str, db: AsyncSession = Depends(get_db)):
    """Lightweight status poll endpoint."""
    stmt = select(UploadSession).where(UploadSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    return {
        "status": session.status.value,
        "summary": session.summary,
    }
