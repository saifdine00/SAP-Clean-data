from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import json

from app.database import get_db, AsyncSessionLocal
from app.models.session import UploadSession, SessionStatus, Anomaly
from app.utils.file_parser import parse_file, parse_pasted_text, dataframe_to_records
from app.core.detector import detect_anomalies
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["upload"])

MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


async def _run_analysis(session_id: str, df, original_format: str):
    """Background task: run detection and persist anomalies."""
    async with AsyncSessionLocal() as db:
        try:
            # Update status
            stmt = select(UploadSession).where(UploadSession.id == session_id)
            result = await db.execute(stmt)
            session = result.scalar_one()
            session.status = SessionStatus.ANALYZING
            await db.commit()

            # Detect anomalies
            anomaly_dicts = detect_anomalies(session_id, df)

            # Persist anomalies
            for a in anomaly_dicts:
                db.add(Anomaly(**a))

            # Build summary
            type_counts: dict[str, int] = {}
            for a in anomaly_dicts:
                t = a["anomaly_type"]
                type_counts[t] = type_counts.get(t, 0) + 1

            session.status = SessionStatus.READY
            session.summary = {
                "total_anomalies": len(anomaly_dicts),
                "anomalies_by_type": type_counts,
                "total_rows": len(df),
                "rows_with_issues": len({a["row_index"] for a in anomaly_dicts}),
            }
            await db.commit()
            logger.info("Analysis complete for session %s: %d anomalies", session_id, len(anomaly_dicts))
        except Exception as exc:
            logger.error("Analysis failed for session %s: %s", session_id, exc, exc_info=True)
            await db.rollback()


@router.post("/file")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file (.xlsx, .xls, .csv, .json) and start async analysis."""
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, f"File exceeds maximum size of {settings.MAX_FILE_SIZE_MB} MB")

    try:
        df, fmt = parse_file(file.filename, content)
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    if len(df) > settings.MAX_ROWS:
        raise HTTPException(400, f"File contains too many rows (max {settings.MAX_ROWS})")

    # Store raw data as JSON-serialisable records
    records = dataframe_to_records(df)

    session = UploadSession(
        filename=file.filename,
        original_format=fmt,
        total_rows=len(df),
        status=SessionStatus.ANALYZING,
        column_mapping={col: col for col in df.columns},
        raw_data={"records": records},
        clean_data={"records": records},
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    # Run analysis in background
    background_tasks.add_task(_run_analysis, session.id, df, fmt)

    return {
        "session_id": session.id,
        "filename": file.filename,
        "total_rows": len(df),
        "columns": list(df.columns),
        "status": "analyzing",
        "message": "File uploaded. Analysis is running in the background.",
    }


@router.post("/paste")
async def upload_paste(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Accept pasted tabular text (TSV / CSV) and start async analysis."""
    if not text.strip():
        raise HTTPException(400, "No text provided.")

    try:
        df, fmt = parse_pasted_text(text)
    except Exception as exc:
        raise HTTPException(400, f"Could not parse pasted text: {exc}")

    records = dataframe_to_records(df)
    session = UploadSession(
        filename="pasted_data",
        original_format="paste",
        total_rows=len(df),
        status=SessionStatus.ANALYZING,
        column_mapping={col: col for col in df.columns},
        raw_data={"records": records},
        clean_data={"records": records},
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    background_tasks.add_task(_run_analysis, session.id, df, fmt)

    return {
        "session_id": session.id,
        "filename": "pasted_data",
        "total_rows": len(df),
        "columns": list(df.columns),
        "status": "analyzing",
    }
