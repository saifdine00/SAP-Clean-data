from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import pandas as pd
import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.database import get_db
from app.models.session import UploadSession, Anomaly, CorrectionStatus
from app.core.corrector import apply_corrections

router = APIRouter(prefix="/export", tags=["export"])


def _build_clean_df(session: UploadSession, anomalies: list[Anomaly]) -> pd.DataFrame:
    """Reconstruct the DataFrame and apply accepted corrections."""
    records = session.clean_data.get("records", [])
    df = pd.DataFrame(records)
    accepted = [
        {
            "row_index": a.row_index,
            "column_name": a.column_name,
            "corrected_value": a.corrected_value,
        }
        for a in anomalies
        if a.status in (CorrectionStatus.ACCEPTED, CorrectionStatus.MANUAL)
        and a.corrected_value is not None
        and a.column_name in df.columns
    ]
    # Remove rows flagged as exact duplicates and accepted
    dup_rows = {
        a.row_index
        for a in anomalies
        if a.anomaly_type == "duplicate_exact"
        and a.status == CorrectionStatus.ACCEPTED
    }
    df = apply_corrections(df, accepted)
    if dup_rows:
        df = df.drop(index=list(dup_rows), errors="ignore").reset_index(drop=True)
    return df


@router.get("/{session_id}/csv")
async def export_csv(session_id: str, db: AsyncSession = Depends(get_db)):
    """Export the corrected data as CSV."""
    session, anomalies = await _load(session_id, db)
    df = _build_clean_df(session, anomalies)
    buf = io.StringIO()
    df.to_csv(buf, index=False, encoding="utf-8-sig")
    buf.seek(0)
    filename = f"clean_{session.filename.rsplit('.', 1)[0]}.csv"
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{session_id}/xlsx")
async def export_xlsx(session_id: str, db: AsyncSession = Depends(get_db)):
    """Export the corrected data as Excel (.xlsx)."""
    session, anomalies = await _load(session_id, db)
    df = _build_clean_df(session, anomalies)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Clean Data")
    buf.seek(0)
    filename = f"clean_{session.filename.rsplit('.', 1)[0]}.xlsx"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{session_id}/report/pdf")
async def export_report_pdf(session_id: str, db: AsyncSession = Depends(get_db)):
    """Generate and export the validation report as PDF."""
    session, anomalies = await _load(session_id, db)
    buf = io.BytesIO()
    _build_pdf(buf, session, anomalies)
    buf.seek(0)
    filename = f"validation_report_{session_id[:8]}.pdf"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{session_id}/report/json")
async def export_report_json(session_id: str, db: AsyncSession = Depends(get_db)):
    """Return validation report as JSON."""
    session, anomalies = await _load(session_id, db)
    return _build_report_data(session, anomalies)


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _load(session_id: str, db: AsyncSession):
    stmt = select(UploadSession).where(UploadSession.id == session_id)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, f"Session '{session_id}' not found.")
    a_stmt = select(Anomaly).where(Anomaly.session_id == session_id)
    a_result = await db.execute(a_stmt)
    anomalies = a_result.scalars().all()
    return session, list(anomalies)


def _build_report_data(session: UploadSession, anomalies: list[Anomaly]) -> dict:
    total = session.total_rows
    accepted = sum(1 for a in anomalies if a.status == CorrectionStatus.ACCEPTED)
    rejected = sum(1 for a in anomalies if a.status == CorrectionStatus.REJECTED)
    manual = sum(1 for a in anomalies if a.status == CorrectionStatus.MANUAL)
    pending = sum(1 for a in anomalies if a.status == CorrectionStatus.PENDING)

    rows_with_issues = len({a.row_index for a in anomalies})
    rows_ready = total - rows_with_issues

    by_type: dict[str, int] = {}
    for a in anomalies:
        by_type[a.anomaly_type] = by_type.get(a.anomaly_type, 0) + 1

    return {
        "session_id": session.id,
        "filename": session.filename,
        "generated_at": datetime.utcnow().isoformat(),
        "total_rows": total,
        "rows_with_issues": rows_with_issues,
        "rows_ready_for_import": rows_ready,
        "total_anomalies": len(anomalies),
        "corrections": {
            "accepted": accepted,
            "rejected": rejected,
            "manual": manual,
            "pending": pending,
        },
        "anomalies_by_type": by_type,
    }


def _build_pdf(buf: io.BytesIO, session: UploadSession, anomalies: list[Anomaly]):
    data = _build_report_data(session, anomalies)
    doc = SimpleDocTemplate(buf, pagesize=A4,
                             rightMargin=2*cm, leftMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("title", parent=styles["Title"],
                                  fontSize=20, textColor=colors.HexColor("#1e293b"),
                                  spaceAfter=0.3*cm)
    sub_style = ParagraphStyle("sub", parent=styles["Normal"],
                                fontSize=10, textColor=colors.HexColor("#64748b"),
                                spaceAfter=0.5*cm)
    h2_style = ParagraphStyle("h2", parent=styles["Heading2"],
                               fontSize=13, textColor=colors.HexColor("#0f172a"),
                               spaceBefore=0.5*cm, spaceAfter=0.3*cm)
    body_style = ParagraphStyle("body", parent=styles["Normal"], fontSize=9)

    elements = []

    # Header
    elements.append(Paragraph("SAP Data Migration — Validation Report", title_style))
    elements.append(Paragraph(
        f"Session: {session.id} | File: {session.filename} | "
        f"Generated: {data['generated_at'][:19].replace('T', ' ')} UTC",
        sub_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
    elements.append(Spacer(1, 0.4*cm))

    # Summary table
    elements.append(Paragraph("Summary", h2_style))
    summary_data = [
        ["Metric", "Value"],
        ["Total rows", str(data["total_rows"])],
        ["Rows with issues", str(data["rows_with_issues"])],
        ["Rows ready for import", str(data["rows_ready_for_import"])],
        ["Total anomalies detected", str(data["total_anomalies"])],
        ["Corrections accepted", str(data["corrections"]["accepted"])],
        ["Corrections rejected", str(data["corrections"]["rejected"])],
        ["Manual corrections", str(data["corrections"]["manual"])],
        ["Pending corrections", str(data["corrections"]["pending"])],
    ]
    t = Table(summary_data, colWidths=[9*cm, 7*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 0.4*cm))

    # Anomalies by type
    if data["anomalies_by_type"]:
        elements.append(Paragraph("Anomalies by Type", h2_style))
        type_data = [["Anomaly Type", "Count"]] + [
            [k.replace("_", " ").title(), str(v)]
            for k, v in sorted(data["anomalies_by_type"].items(), key=lambda x: -x[1])
        ]
        t2 = Table(type_data, colWidths=[12*cm, 4*cm])
        t2.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#6366f1")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(t2)

    doc.build(elements)
