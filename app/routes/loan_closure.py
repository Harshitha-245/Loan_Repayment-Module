from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from app.core.db import get_db
from app.models.loans import Loan
from app.models.payments import Payment_Transaction
from app.models.emi_scheduled import EMI_Schedule

router = APIRouter(prefix="/loan-closure", tags=["Loan Closure and NDC certificate"])

# ── NBFC Config ───────────────────────────────────────────────────────────────

NBFC_NAME    = "ABC Finance Private Limited"
NBFC_ADDRESS = "123, Financial District, Hyderabad - 500032, Telangana"
NBFC_CONTACT = "Phone: 040-12345678 | Email: support@abcfinance.in"
NBFC_REG     = "NBFC Reg No: N-07.00000.00.000 | RBI Reg No: B-01.00000"

# ── Dummy Bank Details ────────────────────────────────────────────────────────

DUMMY_BANK = {
    "bank_name":      "State Bank of India",
    "branch_name":    "Hyderabad Main Branch",
    "account_number": "456789123456",
    "ifsc_code":      "SBIN0002456",
}

# ── Color Palette ─────────────────────────────────────────────────────────────

PRIMARY   = colors.HexColor('#1B3A6B')
GREEN     = colors.HexColor('#1B7B34')
LIGHT_BG  = colors.HexColor('#EEF2F8')
ROW_ALT   = colors.HexColor('#F7F9FC')
GREY      = colors.HexColor('#CCCCCC')
TEXT_DARK = colors.HexColor('#222222')
TEXT_MID  = colors.HexColor('#444444')
TEXT_LITE = colors.HexColor('#888888')

# ── Styles ────────────────────────────────────────────────────────────────────

def get_styles():
    styles = getSampleStyleSheet()

    defs = [
        ('nbfc_name',     'Helvetica-Bold',    18, PRIMARY,   TA_CENTER, 4,  0),
        ('nbfc_address',  'Helvetica',          9, TEXT_MID,  TA_CENTER, 2,  0),
        ('nbfc_reg',      'Helvetica-Oblique',  8, TEXT_LITE, TA_CENTER, 2,  0),
        ('doc_title',     'Helvetica-Bold',    14, PRIMARY,   TA_CENTER, 6, 10),
        ('ref_line',      'Helvetica',          9, colors.HexColor('#333333'), TA_LEFT, 2, 0),
        ('body_text',     'Helvetica',         10, TEXT_DARK, TA_JUSTIFY, 8,  0),
        ('section_header','Helvetica-Bold',    11, PRIMARY,   TA_LEFT,   4, 10),
        ('footer_text',   'Helvetica-Oblique',  8, TEXT_LITE, TA_CENTER, 0,  0),
        ('sign_label',    'Helvetica',          9, colors.HexColor('#333333'), TA_LEFT, 0, 0),
        ('sign_name',     'Helvetica-Bold',    10, PRIMARY,   TA_LEFT,   0,  0),
    ]

    for name, font, size, color, align, after, before in defs:
        styles.add(ParagraphStyle(
            name, fontName=font, fontSize=size, textColor=color,
            alignment=align, spaceAfter=after, spaceBefore=before,
            **({"leading": 16} if name == "body_text" else {})
        ))

    return styles


# ── Helpers ───────────────────────────────────────────────────────────────────

def format_date(dt=None):
    return (dt or datetime.utcnow()).strftime("%d %B %Y")

def ref_no(prefix, application_id, dt=None):
    return f"REF/{prefix}/{(dt or datetime.utcnow()).strftime('%Y%m%d')}/{str(application_id)[:8].upper()}"

def loan_info(loan):
    """Extract loan fields with safe fallbacks."""
    def get(attr, fallback):
        return getattr(loan, attr, None) or fallback

    bank = DUMMY_BANK
    return {
        "borrower_name":  get("borrower_name",       "Valued Customer"),
        "loan_amount":    get("loan_amount",          "N/A"),
        "bank_name":      get("bank_name",            bank["bank_name"]),
        "account_number": get("bank_account_number",  bank["account_number"]),
        "ifsc_code":      get("ifsc_code",            bank["ifsc_code"]),
        "branch_name":    get("branch_name",          bank["branch_name"]),
    }

def base_table_style(header_row=False):
    style = [
        ('FONTNAME',  (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME',  (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE',  (0, 0), (-1, -1), 10),
        ('GRID',      (0, 0), (-1, -1), 0.5, GREY),
        ('PADDING',   (0, 0), (-1, -1), 7),
        ('VALIGN',    (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, ROW_ALT]),
    ]
    if header_row:
        style += [
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.white),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('ALIGN',      (0, 0), (-1, 0), 'CENTER'),
        ]
    else:
        style.append(('BACKGROUND', (0, 0), (0, -1), LIGHT_BG))
    return TableStyle(style)


# ── Letterhead ────────────────────────────────────────────────────────────────

def build_letterhead(styles):
    return [
        HRFlowable(width="100%", thickness=6, color=PRIMARY, spaceAfter=8),
        Paragraph(NBFC_NAME,    styles['nbfc_name']),
        Paragraph(NBFC_ADDRESS, styles['nbfc_address']),
        Paragraph(NBFC_CONTACT, styles['nbfc_address']),
        Paragraph(NBFC_REG,     styles['nbfc_reg']),
        HRFlowable(width="100%", thickness=1, color=GREY, spaceBefore=6, spaceAfter=10),
    ]


def build_signature(left_label, right_label, styles):
    return Table([
        [Paragraph(left_label,  styles['sign_label']), Paragraph("", styles['sign_label']), Paragraph(right_label, styles['sign_label'])],
        [Paragraph(NBFC_NAME,   styles['sign_name']),  Paragraph("", styles['sign_label']), Paragraph(NBFC_NAME,   styles['sign_name'])],
    ], colWidths=[3 * inch, 1 * inch, 3 * inch])

def build_footer(styles):
    return [
        Spacer(1, 0.3 * inch),
        HRFlowable(width="100%", thickness=1, color=GREY, spaceAfter=4),
        Paragraph(f"This is a system-generated document. | {NBFC_NAME} | {NBFC_ADDRESS}", styles['footer_text']),
    ]


# ── Page 1: Loan Closure Certificate ─────────────────────────────────────────

def build_closure_letter(loan, application_id, total_paid, styles, closure_date, issued_date, closed_at):
    info = loan_info(loan)
    elements = build_letterhead(styles)

    ref = Table([
        [Paragraph(f"Ref No: {ref_no('LC', application_id, closed_at + timedelta(days=2))}", styles['ref_line']),
         Paragraph(f"Date: {issued_date}", styles['ref_line'])]
    ], colWidths=[3.5 * inch, 3.5 * inch])
    ref.setStyle(TableStyle([('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements += [ref, Spacer(1, 0.15 * inch)]

    elements += [
        Paragraph("LOAN CLOSURE CERTIFICATE", styles['doc_title']),
        HRFlowable(width="60%", thickness=2, color=PRIMARY, spaceAfter=10, hAlign='CENTER'),
        Paragraph("To,", styles['body_text']),
        Paragraph(f"<b>{info['borrower_name']}</b>", styles['body_text']),
        Spacer(1, 0.05 * inch),
        Paragraph(f"<b>Subject: Closure of Loan Account No. {application_id}</b>", styles['body_text']),
        Spacer(1, 0.05 * inch),
        Paragraph("Dear Sir/Madam,", styles['body_text']),
        Paragraph(
            f"We are pleased to inform you that your loan account bearing Loan ID "
            f"<b>{application_id}</b> has been <b>fully repaid and officially closed</b> "
            f"as on <b>{closure_date}</b>. We thank you for your timely repayments and for "
            f"choosing {NBFC_NAME} for your financial needs.",
            styles['body_text']
        ),
    ]

    elements.append(Paragraph("Loan Account Summary", styles['section_header']))
    summary_table = Table([
        ["Loan Account Number", str(application_id)],
        ["Borrower Name",       info['borrower_name']],
        ["Loan Amount",         f"Rs. {info['loan_amount']}"],
        ["Total Amount Repaid", f"Rs. {total_paid:.2f}"],
        ["Closure Date",        closure_date],
        ["Account Status",      "CLOSED"],
    ], colWidths=[2.5 * inch, 4.5 * inch])
    st = base_table_style()
    st.add('TEXTCOLOR', (1, 5), (1, 5), GREEN)
    st.add('FONTNAME',  (1, 5), (1, 5), 'Helvetica-Bold')
    summary_table.setStyle(st)
    elements += [summary_table, Spacer(1, 0.15 * inch)]

    elements.append(Paragraph("Bank Account Details", styles['section_header']))
    bank_table = Table([
        ["Bank Name",      info['bank_name']],
        ["Account Number", info['account_number']],
        ["IFSC Code",      info['ifsc_code']],
        ["Branch",         info['branch_name']],
    ], colWidths=[2.5 * inch, 4.5 * inch])
    bank_table.setStyle(base_table_style())
    elements += [bank_table, Spacer(1, 0.15 * inch)]

    elements += [
        Paragraph(
            "You are requested to collect your original documents (if any) from our nearest branch. "
            "No further dues are outstanding against this loan account.",
            styles['body_text']
        ),
        Spacer(1, 0.2 * inch),
        build_signature("Authorized Signatory", "Branch Manager", styles),
        *build_footer(styles),
    ]
    return elements


# ── Page 2: Credit Bureau Update Notice ──────────────────────────────────────

def build_credit_bureau_letter(loan, application_id, styles, closure_date, issued_date, closed_at):
    info = loan_info(loan)
    elements = build_letterhead(styles)

    ref = Table([
        [Paragraph(f"Ref No: {ref_no('CB', application_id, closed_at + timedelta(days=2))}", styles['ref_line']),
         Paragraph(f"Date: {issued_date}", styles['ref_line'])]
    ], colWidths=[3.5 * inch, 3.5 * inch])
    ref.setStyle(TableStyle([('ALIGN', (1, 0), (1, 0), 'RIGHT')]))
    elements += [ref, Spacer(1, 0.15 * inch)]

    elements += [
        Paragraph("CREDIT BUREAU UPDATE NOTICE", styles['doc_title']),
        HRFlowable(width="60%", thickness=2, color=PRIMARY, spaceAfter=10, hAlign='CENTER'),
        Paragraph("To,", styles['body_text']),
        Paragraph(f"<b>{info['borrower_name']}</b>", styles['body_text']),
        Spacer(1, 0.05 * inch),
        Paragraph(f"<b>Subject: Credit Bureau Update — Loan Account No. {application_id}</b>", styles['body_text']),
        Spacer(1, 0.05 * inch),
        Paragraph("Dear Sir/Madam,", styles['body_text']),
        Paragraph(
            f"This is to formally notify you that {NBFC_NAME} has submitted an update to "
            f"<b>CIBIL (TransUnion)</b>, <b>Experian</b>, <b>Equifax</b>, and "
            f"<b>CRIF High Mark</b> reflecting the closure of Loan ID <b>{application_id}</b> "
            f"as on <b>{closure_date}</b>.",
            styles['body_text']
        ),
    ]

    elements.append(Paragraph("Credit Bureau Update Details", styles['section_header']))
    bureau_table = Table([
        ["Bureau Name",        "Update Status", "Remarks"],
        ["CIBIL (TransUnion)", "Submitted",     "Loan marked as CLOSED"],
        ["Experian",           "Submitted",     "Loan marked as CLOSED"],
        ["Equifax",            "Submitted",     "Loan marked as CLOSED"],
        ["CRIF High Mark",     "Submitted",     "Loan marked as CLOSED"],
    ], colWidths=[2.3 * inch, 2 * inch, 2.7 * inch])
    bt = base_table_style(header_row=True)
    bt.add('TEXTCOLOR', (1, 1), (1, -1), GREEN)
    bt.add('FONTNAME',  (1, 1), (1, -1), 'Helvetica-Bold')
    bureau_table.setStyle(bt)
    elements += [bureau_table, Spacer(1, 0.15 * inch)]

    elements += [
        Paragraph(
            "Credit bureau records are typically updated within <b>30-45 working days</b>. "
            "For discrepancies, contact us at <b>support@abcfinance.in</b>.",
            styles['body_text']
        ),
        Spacer(1, 0.2 * inch),
        build_signature("Authorized Signatory", "Credit Bureau Officer", styles),
        *build_footer(styles),
    ]
    return elements


# ── Main Route ────────────────────────────────────────────────────────────────

@router.post("/close/{application_id}")
def close_loan(application_id: str, db: Session = Depends(get_db)):

    loan = db.query(Loan).filter(Loan.loan_id == application_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.status != "closed":
        emi_schedule = db.query(EMI_Schedule).filter(
            EMI_Schedule.application_id == application_id
        ).all()
        if not emi_schedule:
            raise HTTPException(status_code=400, detail="No EMI schedule found")

        scheduled_emi_numbers = {e.emi_number for e in emi_schedule}

        payments = db.query(Payment_Transaction).filter(
            Payment_Transaction.application_id == application_id
        ).all()

        paid_emi_numbers = set()
        total_paid = 0.0

        for p in payments:
            total_paid += float(p.amount_paid or 0)
            if p.emi_number is None:
                continue
            elif isinstance(p.emi_number, int):
                paid_emi_numbers.add(p.emi_number)
            elif isinstance(p.emi_number, list):
                paid_emi_numbers.update(p.emi_number)
            elif isinstance(p.emi_number, str):
                paid_emi_numbers.update(
                    int(e.strip()) for e in p.emi_number.split(",") if e.strip().isdigit()
                )

        if scheduled_emi_numbers != paid_emi_numbers:
            raise HTTPException(status_code=400, detail="Loan is not fully paid yet")

        loan.status    = "closed"
        loan.closed_at = datetime(2026, 9, 26)
        db.commit()
    else:
        # Already closed — just recalculate total_paid for PDF
        payments = db.query(Payment_Transaction).filter(
            Payment_Transaction.application_id == application_id
        ).all()
        total_paid = sum(float(p.amount_paid or 0) for p in payments)

    # ── Build PDF ─────────────────────────────────────────────────────────────
    styles       = get_styles()
    closed_at    = datetime(2026, 9, 26)
    closure_date = format_date(closed_at)                     # 26 September 2026
    issued_date  = format_date(closed_at + timedelta(days=2)) # 28 September 2026

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        leftMargin=0.75 * inch, rightMargin=0.75 * inch,
        topMargin=0.5 * inch,   bottomMargin=0.5 * inch,
    )
    doc.build([
        *build_closure_letter(loan, application_id, total_paid, styles, closure_date, issued_date, closed_at),
        PageBreak(),
        *build_credit_bureau_letter(loan, application_id, styles, closure_date, issued_date, closed_at),
    ])
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=loan_closure_{application_id}.pdf"},
    )