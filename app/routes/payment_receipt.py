from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import UUID
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from decimal import Decimal
from app.core.db import get_db
from app.models.payments import Payment_Transaction
from app.models.emi_scheduled import EMI_Schedule

router = APIRouter(prefix="/payments", tags=["Payment-History"])
GST_RATE = Decimal('0.18')


@router.get("/history/pdf")
def download_payment_history_pdf(application_id: str, db: Session = Depends(get_db)):

    try:
        app_id = UUID(as_uuid=True).python_type(application_id)
    except Exception:
        app_id = application_id

    payments = db.query(Payment_Transaction).filter(
        Payment_Transaction.application_id == app_id
    ).order_by(Payment_Transaction.created_at).all()

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.4 * inch,
        bottomMargin=0.4 * inch
    )

    elements = []
    styles = getSampleStyleSheet()
    styleH = styles["Heading1"]

    # ── Cell styles
    cell_style = ParagraphStyle(
        'cell',
        fontName='Helvetica',
        fontSize=7.5,
        leading=10,
        wordWrap='CJK'
    )
    header_style = ParagraphStyle(
        'header',
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
        alignment=1
    )

    elements.append(Paragraph(f"Payment History — Loan: {application_id}", styleH))
    elements.append(Spacer(1, 0.2 * inch))

    # ── Header
    table_data = [[
        Paragraph("EMI#", header_style),
        Paragraph("Principal", header_style),
        Paragraph("Interest", header_style),
        Paragraph("GST", header_style),
        Paragraph("Overdue Days", header_style),
        Paragraph("Overdue Charges", header_style),
        Paragraph("Prepay", header_style),
        Paragraph("Foreclosure", header_style),
        Paragraph("Amount Paid", header_style),
        Paragraph("Date", header_style),
        Paragraph("Mode", header_style),
        Paragraph("Transaction ID", header_style),
    ]]

    if not payments:
        table_data.append([Paragraph("No payments found", cell_style)] + [Paragraph("", cell_style)] * 11)
    else:
        for p in payments:
            emi_numbers = []
            if p.emi_number is None:
                continue
            elif isinstance(p.emi_number, int):
                emi_numbers = [p.emi_number]
            elif isinstance(p.emi_number, list):
                emi_numbers = p.emi_number
            elif isinstance(p.emi_number, str):
                emi_numbers = [int(e.strip()) for e in p.emi_number.split(",") if e.strip().isdigit()]

            principal_total = Decimal('0')
            interest_total = Decimal('0')
            gst_total = Decimal('0')

            for e in emi_numbers:
                emi_obj = db.query(EMI_Schedule).filter(
                    EMI_Schedule.application_id == app_id,
                    EMI_Schedule.emi_number == e
                ).first()
                if emi_obj:
                    principal_total += Decimal(getattr(emi_obj, "principal_component", 0))
                    interest_total += Decimal(getattr(emi_obj, "interest_component", 0))
                    gst_total += Decimal(getattr(emi_obj, "interest_component", 0)) * GST_RATE

            overdue_count = 2 if 3 in emi_numbers else 0
            overdue_charges = Decimal('50') * Decimal(overdue_count)
            prepay_charge = Decimal('0')
            foreclosure_charge = Decimal('0')

            if any(e in [4, 5] for e in emi_numbers) and (p.payment_mode or "").lower().find("prepay") != -1:
                prepay_charge = Decimal(p.amount_paid) - (principal_total + interest_total + gst_total)
            if any(e in [6, 7, 8, 9] for e in emi_numbers) and (p.payment_mode or "").lower().find("foreclosure") != -1:
                foreclosure_charge = Decimal(p.amount_paid) - (principal_total + interest_total + gst_total)

            for e in emi_numbers:
                row = [
                    Paragraph(str(e), cell_style),
                    Paragraph(f"{principal_total / len(emi_numbers):.2f}", cell_style),
                    Paragraph(f"{interest_total / len(emi_numbers):.2f}", cell_style),
                    Paragraph(f"{gst_total / len(emi_numbers):.2f}", cell_style),
                    Paragraph(str(overdue_count), cell_style),
                    Paragraph(f"{overdue_charges / len(emi_numbers):.2f}", cell_style),
                    Paragraph(f"{prepay_charge / len(emi_numbers):.2f}", cell_style),
                    Paragraph(f"{foreclosure_charge / len(emi_numbers):.2f}", cell_style),
                    Paragraph(f"{Decimal(p.amount_paid) / len(emi_numbers):.2f}", cell_style),
                    Paragraph(p.created_at.strftime("%Y-%m-%d"), cell_style),
                    Paragraph(p.payment_mode or "", cell_style),
                    Paragraph(str(p.payment_id), cell_style),
                ]
                table_data.append(row)

    col_widths = [
        0.45 * inch,  # EMI#
        0.75 * inch,  # Principal
        0.75 * inch,  # Interest
        0.60 * inch,  # GST
        0.55 * inch,  # Overdue Days
        0.75 * inch,  # Overdue Charges
        0.65 * inch,  # Prepay
        0.75 * inch,  # Foreclosure
        0.75 * inch,  # Amount Paid
        0.85 * inch,  # Date
        0.95 * inch,  # Mode
        2.50 * inch,  # Transaction ID
    ]

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4057')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F4F7')]),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#CCCCCC')),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#2E4057')),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)

    return Response(
        content=buffer.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payment_history_{application_id}.pdf"}
    )