from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from decimal import Decimal
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import inch, cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle,
    Paragraph, Spacer, HRFlowable, KeepTogether
)

from app.core.db import get_db
from app.models.payments import Payment_Transaction
from app.models.emi_scheduled import EMISchedule

router = APIRouter(prefix="/payments", tags=["Payment-History"])

GST_RATE          = Decimal('0.18')
PREPAY_RATE       = Decimal('0.02')
FORECLOSURE_RATE  = Decimal('0.04')
PRIMARY    = colors.HexColor('#1A3C5E')   
ACCENT     = colors.HexColor('#2E7DAF')   
LIGHT_BG   = colors.HexColor('#F0F4F8')   
ALT_ROW    = colors.HexColor('#FAFBFC')   
BORDER     = colors.HexColor('#D0D9E3')   
SUCCESS    = colors.HexColor('#1E7E4A')   
WARNING    = colors.HexColor('#B45309')   
WHITE      = colors.white

def _fmt(val) -> str:
    try:
        return f"{float(val):,.2f}"
    except Exception:
        return str(val)


def _parse_emi_numbers(emi_number) -> list[int]:
    if emi_number is None:
        return []
    if isinstance(emi_number, int):
        return [emi_number]
    if isinstance(emi_number, list):
        return emi_number
    if isinstance(emi_number, str):
        return [int(e.strip()) for e in emi_number.split(",") if e.strip().isdigit()]
    return []
@router.get("/history/receipt/pdf")
def download_payment_history_pdf(
    application_id: str,
    db: Session = Depends(get_db)
):
    payments = db.query(Payment_Transaction).filter(
        Payment_Transaction.application_id == application_id
    ).order_by(Payment_Transaction.created_at).all()

    if not payments:
        raise HTTPException(status_code=404, detail="No payment records found.")

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin   = 1.8 * cm,
        rightMargin  = 1.8 * cm,
        topMargin    = 1.5 * cm,
        bottomMargin = 1.5 * cm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title',
        fontName  = 'Helvetica-Bold',
        fontSize  = 18,
        textColor = PRIMARY,
        spaceAfter= 2,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle',
        fontName  = 'Helvetica',
        fontSize  = 10,
        textColor = ACCENT,
        spaceAfter= 4,
    )
    section_style = ParagraphStyle(
        'Section',
        fontName  = 'Helvetica-Bold',
        fontSize  = 10,
        textColor = PRIMARY,
        spaceBefore = 6,
        spaceAfter  = 4,
    )
    col_header_style = ParagraphStyle(
        'ColHeader',
        fontName  = 'Helvetica-Bold',
        fontSize  = 8,
        textColor = WHITE,
        alignment = TA_CENTER,
        leading   = 11,
    )
    cell_style = ParagraphStyle(
        'Cell',
        fontName  = 'Helvetica',
        fontSize  = 8,
        textColor = colors.HexColor('#2D3748'),
        alignment = TA_CENTER,
        leading   = 11,
    )
    cell_right = ParagraphStyle(
        'CellRight',
        fontName  = 'Helvetica',
        fontSize  = 8,
        textColor = colors.HexColor('#2D3748'),
        alignment = TA_RIGHT,
        leading   = 11,
    )
    amount_style = ParagraphStyle(
        'Amount',
        fontName  = 'Helvetica-Bold',
        fontSize  = 8,
        textColor = SUCCESS,
        alignment = TA_RIGHT,
        leading   = 11,
    )
    charge_style = ParagraphStyle(
        'Charge',
        fontName  = 'Helvetica',
        fontSize  = 8,
        textColor = WARNING,
        alignment = TA_RIGHT,
        leading   = 11,
    )
    footer_style = ParagraphStyle(
        'Footer',
        fontName  = 'Helvetica',
        fontSize  = 8,
        textColor = colors.HexColor('#718096'),
        alignment = TA_CENTER,
    )

    elements = []
    elements.append(Spacer(1, 0.1 * cm))
    elements.append(Paragraph("Payment History Receipt", title_style))
    elements.append(Paragraph(f"Loan Application ID: {application_id}", subtitle_style))
    elements.append(HRFlowable(
        width="100%", thickness=2, color=ACCENT,
        spaceAfter=12, spaceBefore=4
    ))
    total_paid_all = sum(Decimal(str(p.amount_paid or 0)) for p in payments)

    summary_data = [[
        Paragraph("Total Transactions", col_header_style),
        Paragraph("Total Amount Paid", col_header_style),
        Paragraph("Generated On", col_header_style),
    ],[
        Paragraph(str(len(payments)), ParagraphStyle('sv', fontName='Helvetica-Bold', fontSize=13, textColor=ACCENT, alignment=TA_CENTER)),
        Paragraph(f"Rs. {_fmt(total_paid_all)}", ParagraphStyle('sv', fontName='Helvetica-Bold', fontSize=13, textColor=SUCCESS, alignment=TA_CENTER)),
        Paragraph(datetime.now().strftime("%d %b %Y, %I:%M %p"), ParagraphStyle('sv', fontName='Helvetica', fontSize=10, textColor=PRIMARY, alignment=TA_CENTER)),
    ]]

    page_w = landscape(A4)[0] - 3.6 * cm
    summary_table = Table(summary_data, colWidths=[page_w/3]*3)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0), PRIMARY),
        ('BACKGROUND',    (0, 1), (-1, 1), LIGHT_BG),
        ('TOPPADDING',    (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING',   (0, 0), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 0), (-1, -1), 8),
        ('BOX',           (0, 0), (-1, -1), 1, BORDER),
        ('LINEAFTER',     (0, 0), (-2, -1), 0.5, BORDER),
        ('ROUNDEDCORNERS', [4]),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph("Transaction Details", section_style))

    col_headers = [
        Paragraph("Txn ID",                col_header_style),
        Paragraph("EMI No.",               col_header_style),
        Paragraph("Principal\n(Rs.)",      col_header_style),
        Paragraph("Interest\n(Rs.)",       col_header_style),
        Paragraph("GST on\nInterest",      col_header_style),
        Paragraph("EMI Total\n(Rs.)",      col_header_style),
        Paragraph("Foreclosure\nCharge",   col_header_style),
        Paragraph("Prepay\nCharge",        col_header_style),
        Paragraph("GST on\nCharges",       col_header_style),
        Paragraph("Total Paid\n(Rs.)",     col_header_style),
        Paragraph("Mode",                  col_header_style),
        Paragraph("Option",                col_header_style),
        Paragraph("Date",                  col_header_style),
    ]
    table_data = [col_headers]

    for p in payments:
        emi_numbers = _parse_emi_numbers(p.emi_number)

        principal_total = Decimal('0')
        interest_total  = Decimal('0')

        for emi_num in emi_numbers:
            emi_obj = db.query(EMISchedule).filter(
                EMISchedule.application_id == application_id,
                EMISchedule.emi_number     == emi_num
            ).first()
            if emi_obj:
                principal_total += Decimal(str(getattr(emi_obj, "principal_component", 0) or 0))
                interest_total  += Decimal(str(getattr(emi_obj, "interest_component",  0) or 0))

        total_emi      = principal_total + interest_total
        gst_on_interest = interest_total * GST_RATE

        foreclosure_charges = Decimal('0')
        prepay_charges      = Decimal('0')
        gst_on_charges      = Decimal('0')

        opt = (p.payment_option or "").lower()
        if opt == "foreclosure":
            foreclosure_charges = total_emi * FORECLOSURE_RATE
            gst_on_charges      = foreclosure_charges * GST_RATE
        elif opt == "prepay":
            prepay_charges = total_emi * PREPAY_RATE
            gst_on_charges = prepay_charges * GST_RATE

        import random
        raw_txn = str(p.transaction_id or "")
        if "." in raw_txn:
            raw_txn = raw_txn.split(".")[0]
        if not raw_txn.isdigit() or len(raw_txn) != 12:
            raw_txn = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        txn_id = raw_txn

        emi_display = p.emi_number if p.emi_number else "-"
        date_str    = p.created_at.strftime("%d %b %Y\n%I:%M %p") if p.created_at else "-"
        opt_label = (p.payment_option or "-").replace("_", " ").title()

        table_data.append([
            Paragraph(str(txn_id),                   cell_style),
            Paragraph(str(emi_display),              cell_style),
            Paragraph(_fmt(principal_total),         cell_right),
            Paragraph(_fmt(interest_total),          cell_right),
            Paragraph(_fmt(gst_on_interest),         cell_right),
            Paragraph(_fmt(total_emi),               amount_style),
            Paragraph(_fmt(foreclosure_charges),     charge_style if foreclosure_charges > 0 else cell_right),
            Paragraph(_fmt(prepay_charges),          charge_style if prepay_charges > 0 else cell_right),
            Paragraph(_fmt(gst_on_charges),          charge_style if gst_on_charges > 0 else cell_right),
            Paragraph(_fmt(p.amount_paid or 0),      amount_style),
            Paragraph((p.payment_mode or "-").replace("_", " ").title(), cell_style),
            Paragraph(opt_label,                     cell_style),
            Paragraph(date_str,                      cell_style),
        ])

    # Column widths
    col_widths = [
        1.5 * cm,  
        1.5 * cm,  
        2.2 * cm,  
        2.0 * cm,  
        2.0 * cm,  
        2.2 * cm,  
        2.4 * cm,  
        2.2 * cm,  
        2.0 * cm,  
        2.2 * cm, 
        2.2 * cm,  
        2.0 * cm,  
        2.5 * cm,  
    ]

    payment_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    payment_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND',    (0, 0),  (-1, 0),  PRIMARY),
        ('TOPPADDING',    (0, 0),  (-1, 0),  10),
        ('BOTTOMPADDING', (0, 0),  (-1, 0),  10),
        # Data rows
        ('ROWBACKGROUNDS',(0, 1),  (-1, -1), [WHITE, ALT_ROW]),
        ('TOPPADDING',    (0, 1),  (-1, -1), 9),
        ('BOTTOMPADDING', (0, 1),  (-1, -1), 9),
        ('LEFTPADDING',   (0, 0),  (-1, -1), 6),
        ('RIGHTPADDING',  (0, 0),  (-1, -1), 6),
        # Borders
        ('GRID',          (0, 0),  (-1, -1), 0.4, BORDER),
        ('LINEBELOW',     (0, 0),  (-1, 0),  1.5, ACCENT),
        # Align
        ('VALIGN',        (0, 0),  (-1, -1), 'MIDDLE'),
    ]))

    elements.append(payment_table)
    elements.append(Spacer(1, 0.8 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceAfter=6))
    elements.append(Paragraph(
        f"This is a system-generated receipt. Generated on {datetime.now().strftime('%d %b %Y at %I:%M %p')}. "
        f"For queries, contact support@loanapp.com",
        footer_style
    ))

    doc.build(elements)
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=payment_history_{application_id}.pdf"}
    )