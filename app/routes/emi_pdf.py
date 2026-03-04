from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from app.core.db import get_db
from app.models.emi_scheduled import EMISchedule

router = APIRouter(prefix="/emi-pdf",tags=["EMI Schedule"])

@router.get("/{loan_id}/pdf")
def download_emi_pdf(loan_id: str, db: Session = Depends(get_db)):

    emis = (
        db.query(EMISchedule)
        .filter(EMISchedule.application_id == loan_id)
        .order_by(EMISchedule.emi_number.asc())
        .all()
    )

    if not emis:
        raise HTTPException(status_code=404, detail="No EMI schedule found")
    file_path = f"EMISchedule_{loan_id}.pdf"
    doc = SimpleDocTemplate(
        file_path,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=25,
        bottomMargin=25
    )

    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        name="TitleStyle",
        fontSize=22,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=8,
        spaceBefore=4,
        alignment=1,
        fontName="Helvetica-Bold"
    )

    subtitle_style = ParagraphStyle(
        name="SubtitleStyle",
        fontSize=12,
        textColor=colors.HexColor("#444444"),
        spaceAfter=14,
        alignment=1
    )

    label_style = ParagraphStyle(
        name="LabelStyle",
        fontSize=11,
        textColor=colors.black,
        spaceAfter=6,
        leading=18
    )
    elements.append(Paragraph("EMI Repayment Schedule", title_style))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"Loan ID: <b>{loan_id}</b>", subtitle_style))
    elements.append(Spacer(1, 8))
    table_data = [[
        "EMI No.",
        "Due Date",
        "Opening\nPrincipal",
        "Principal",
        "Interest",
        "GST",
        "Total EMI",
        "Closing\nPrincipal"
    ]]

    total_emi = 0.0
    total_principal = 0.0
    total_interest = 0.0
    total_gst = 0.0

    for emi in emis:
        table_data.append([
            str(emi.emi_number),
            emi.due_date.strftime("%d-%m-%Y"),
            f"{float(emi.opening_principal):,.2f}",
            f"{float(emi.principal_component):,.2f}",
            f"{float(emi.interest_component):,.2f}",
            f"{float(emi.gst_amount):,.2f}",
            f"{float(emi.emi_amount):,.2f}",
            f"{float(emi.closing_principal):,.2f}"
        ])
        total_emi       += float(emi.emi_amount)
        total_principal += float(emi.principal_component)
        total_interest  += float(emi.interest_component)
        total_gst       += float(emi.gst_amount)
    table_data.append([
        "Total", "",
        "",
        f"{total_principal:,.2f}",
        f"{total_interest:,.2f}",
        f"{total_gst:,.2f}",
        f"{total_emi:,.2f}",
        ""
    ])

    col_widths = [
        0.70 * inch,
        1.10 * inch,
        1.50 * inch,
        1.30 * inch,
        1.30 * inch,
        1.10 * inch,
        1.40 * inch,
        1.50 * inch,
    ]

    num_rows = len(table_data)

    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    row_bg_colors = []
    for i in range(1, num_rows - 1):
        bg = colors.HexColor("#f0f4ff") if i % 2 == 0 else colors.white
        row_bg_colors.append(("BACKGROUND", (0, i), (-1, i), bg))

    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  colors.white),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  11),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, 0),  "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),

        ("FONTNAME",      (0, 1), (-1, -2), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -2), 10),
        ("ALIGN",         (0, 1), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 1), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, -2), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -2), 7),

        ("BACKGROUND",    (0, -1), (-1, -1), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR",     (0, -1), (-1, -1), colors.white),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, -1), (-1, -1), 10),
        ("TOPPADDING",    (0, -1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
        ("SPAN",          (0, -1), (1, -1)),
        ("SPAN",          (2, -1), (2, -1)),
        ("GRID",          (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
        ("LINEBELOW",     (0, 0), (-1, 0),  1.5, colors.HexColor("#ffffff")),
        *row_bg_colors,
    ]))

    elements.append(table)
    elements.append(Spacer(1, 16))
    summary_style = ParagraphStyle(
        name="SummaryStyle",
        fontSize=11,
        textColor=colors.black,
        alignment=1,  # center
        spaceBefore=12,
        spaceAfter=6,
        leading=14
    )

    summary_text = (
        f"Total EMI Amount: {total_emi:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Total Principal: {total_principal:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Total Interest: {total_interest:,.2f} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"Total GST: {total_gst:,.2f}"
    )

    elements.append(Paragraph(summary_text, summary_style))

    doc.build(elements)

    return FileResponse(
        path=file_path,
        filename=f"EMI_Schedule_{loan_id}.pdf",
        media_type="application/pdf"
    )
