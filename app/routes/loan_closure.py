from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from io import BytesIO
from decimal import Decimal
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, HRFlowable
)

from app.core.db import get_db
from app.models.loans import LoanApplication
from app.models.emi_scheduled import EMISchedule
from app.models.payments import Payment_Transaction
from app.models.lender_table import Lender

router = APIRouter(prefix="/payments", tags=["Loan Closure & Credit Bureau Update Notice"])
GST_RATE         = Decimal('0.18')
FORECLOSURE_RATE = Decimal('0.04')
NAVY    = colors.HexColor('#1A3C5E')
BLUE    = colors.HexColor('#2E7DAF')
LIGHT   = colors.HexColor('#EEF3F8')
ALT     = colors.HexColor('#F7FAFC')
BORDER  = colors.HexColor('#CBD5E0')
GREEN   = colors.HexColor('#1E7E4A')
AMBER   = colors.HexColor('#B45309')
WHITE   = colors.white
GREY    = colors.HexColor('#718096')
DARK    = colors.HexColor('#2D3748')

def _fmt(val) -> str:
    try:
        return f"Rs. {float(val):,.2f}"
    except Exception:
        return str(val or "-")

def _fmtn(val) -> str:
    try:
        return f"{float(val):,.2f}"
    except Exception:
        return str(val or "0.00")

def _style(name, **kwargs) -> ParagraphStyle:
    base = dict(fontName='Helvetica', fontSize=9, textColor=DARK, leading=13)
    base.update(kwargs)
    return ParagraphStyle(name, **base)

def _kv_table(rows: list[tuple], col_w=(7*cm, 8*cm)) -> Table:
    data = []
    for k, v in rows:
        data.append([
            Paragraph(k, _style('k', fontName='Helvetica-Bold', fontSize=8.5, textColor=NAVY)),
            Paragraph(str(v), _style('v', fontSize=8.5, textColor=DARK)),
        ])
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('RIGHTPADDING',  (0,0), (-1,-1), 8),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [WHITE, ALT]),
        ('GRID',          (0,0), (-1,-1), 0.4, BORDER),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return t

def _section(title: str) -> list:
    return [
        Spacer(1, 0.4*cm),
        Paragraph(title, _style('sec', fontName='Helvetica-Bold',
                                fontSize=10, textColor=WHITE)),
        Spacer(1, 0.2*cm),
    ]


def _header_bar(title: str, page_w: float) -> Table:
    t = Table([[Paragraph(title, _style('hb', fontName='Helvetica-Bold',
                                        fontSize=10, textColor=WHITE,
                                        alignment=TA_LEFT))]],
              colWidths=[page_w])
    t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), NAVY),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 10),
    ]))
    return t

def _fetch_data(application_id: str, db: Session):
    loan = db.query(LoanApplication).filter(
        LoanApplication.id == application_id
    ).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan application not found.")

    emis = db.query(EMISchedule).filter(
        EMISchedule.application_id == application_id
    ).order_by(EMISchedule.emi_number).all()

    payments = db.query(Payment_Transaction).filter(
        Payment_Transaction.application_id == application_id
    ).order_by(Payment_Transaction.created_at).all()

    lender = db.query(Lender).filter(
        Lender.user_id == loan.user_id
    ).first()

    return loan, emis, payments, lender

@router.get("/loan-closure/pdf", summary="Download Loan Closure Certificate")
def loan_closure_pdf(application_id: str, db: Session = Depends(get_db)):
    loan, emis, payments, lender = _fetch_data(application_id, db)
    unpaid = [e for e in emis if e.status not in ("PAID",)]
    if unpaid:
        raise HTTPException(
            status_code=400,
            detail=f"Loan not fully closed. {len(unpaid)} EMI(s) still pending."
        )
    total_principal  = sum(Decimal(str(e.principal_component)) for e in emis)
    total_interest   = sum(Decimal(str(e.interest_component))  for e in emis)
    total_gst        = sum(Decimal(str(e.gst_amount))          for e in emis)
    total_paid       = sum(Decimal(str(p.amount_paid or 0))    for p in payments)
    last_payment     = payments[-1] if payments else None
    closure_date     = last_payment.created_at.strftime("%d %b %Y") if last_payment else datetime.now().strftime("%d %b %Y")
    disburse_date    = loan.disbursed_at.strftime("%d %b %Y") if loan.disbursed_at else "N/A"
    buffer   = BytesIO()
    PAGE_W   = A4[0] - 3.6*cm
    doc      = SimpleDocTemplate(buffer, pagesize=A4,
                                  leftMargin=1.8*cm, rightMargin=1.8*cm,
                                  topMargin=1.5*cm,  bottomMargin=1.5*cm)
    elements = []

    lender_name = lender.company_name if lender else "LoanApp Pvt. Ltd."
    lender_addr = lender.address      if lender else ""
    lender_gst  = lender.gst_number   if lender else ""

    elements.append(Paragraph(lender_name,
        _style('ln', fontName='Helvetica-Bold', fontSize=18, textColor=NAVY, alignment=TA_CENTER)))
    if lender_addr:
        elements.append(Paragraph(lender_addr,
            _style('la', fontSize=9, textColor=GREY, alignment=TA_CENTER)))
    if lender_gst:
        elements.append(Paragraph(f"GST: {lender_gst}",
            _style('lg', fontSize=8.5, textColor=GREY, alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=2, color=BLUE, spaceAfter=8))

    elements.append(Paragraph("LOAN CLOSURE CERTIFICATE",
        _style('ct', fontName='Helvetica-Bold', fontSize=16,
               textColor=NAVY, alignment=TA_CENTER)))
    elements.append(Paragraph("Loan Closure Certificate",
        _style('nd', fontSize=10, textColor=BLUE, alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.4*cm))
    ref_data = [[
        Paragraph(f"Reference No: <b>{loan.reference_number or application_id}</b>",
                  _style('ref', fontSize=9, textColor=DARK)),
        Paragraph(f"Closure Date: <b>{closure_date}</b>",
                  _style('cd', fontSize=9, textColor=DARK, alignment=TA_RIGHT)),
    ]]
    ref_t = Table(ref_data, colWidths=[PAGE_W/2, PAGE_W/2])
    ref_t.setStyle(TableStyle([
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('BACKGROUND',    (0,0), (-1,-1), LIGHT),
        ('BOX',           (0,0), (-1,-1), 0.5, BORDER),
    ]))
    elements.append(ref_t)
    elements.append(Spacer(1, 0.4*cm))
    elements.append(_header_bar("  Loan Details", PAGE_W))
    elements.append(Spacer(1, 0.1*cm))
    elements.append(_kv_table([
        ("Application ID",      application_id),
        ("Reference Number",    loan.reference_number or "N/A"),
        ("Sanctioned Amount",   _fmt(loan.approved_amount)),
        ("Interest Rate",       f"{loan.interest_rate or 'N/A'} % p.a."),
        ("Tenure",              f"{loan.requested_tenure_months or 'N/A'} Months"),
        ("Monthly EMI",         _fmt(loan.monthly_emi)),
        ("Disbursement Date",   disburse_date),
        ("Loan Status",         "CLOSED ✓"),
    ], col_w=[8*cm, PAGE_W - 8*cm]))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(_header_bar("  Payment Summary", PAGE_W))
    elements.append(Spacer(1, 0.1*cm))
    elements.append(_kv_table([
        ("Total Principal Repaid",  _fmt(total_principal)),
        ("Total Interest Paid",     _fmt(total_interest)),
        ("Total GST Paid",          _fmt(total_gst)),
        ("Total Amount Paid",       _fmt(total_paid)),
        ("Number of EMIs",          str(len(emis))),
        ("Last Payment Date",       closure_date),
    ], col_w=[8*cm, PAGE_W - 8*cm]))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(_header_bar("  EMI Payment Ledger", PAGE_W))
    elements.append(Spacer(1, 0.1*cm))
    hdr = _style('eh', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)
    cel = _style('ec', fontSize=8, textColor=DARK, alignment=TA_CENTER)
    amts= _style('ea', fontName='Helvetica-Bold', fontSize=8, textColor=GREEN, alignment=TA_RIGHT)
    emi_headers = [
        [Paragraph(h, hdr) for h in [
            "EMI #", "Due Date", "Opening\nPrincipal",
            "Principal", "Interest", "GST", "EMI Amount",
            "Closing\nPrincipal", "Status"
        ]]
    ]
    emi_rows = []
    for e in emis:
        emi_rows.append([
            Paragraph(str(e.emi_number),                        cel),
            Paragraph(e.due_date.strftime("%d %b %Y") if e.due_date else "-", cel),
            Paragraph(_fmtn(e.opening_principal),               cel),
            Paragraph(_fmtn(e.principal_component),             cel),
            Paragraph(_fmtn(e.interest_component),              cel),
            Paragraph(_fmtn(e.gst_amount),                      cel),
            Paragraph(_fmtn(e.emi_amount),                      amts),
            Paragraph(_fmtn(e.closing_principal),               cel),
            Paragraph("PAID ✓",
                _style('st', fontName='Helvetica-Bold', fontSize=8,
                       textColor=GREEN, alignment=TA_CENTER)),
        ])

    emi_table = Table(
        emi_headers + emi_rows,
        colWidths=[1.2*cm, 2.3*cm, 2.3*cm, 2.1*cm, 2.0*cm, 1.8*cm, 2.2*cm, 2.3*cm, 1.8*cm],
        repeatRows=1
    )
    emi_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  NAVY),
        ('LINEBELOW',     (0,0), (-1,0),  1.5, BLUE),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, ALT]),
        ('GRID',          (0,0), (-1,-1), 0.4, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 4),
        ('RIGHTPADDING',  (0,0), (-1,-1), 4),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(emi_table)
    elements.append(Spacer(1, 0.5*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    elements.append(Spacer(1, 0.2*cm))
    elements.append(Paragraph(
        f"This is to certify that the above-mentioned loan (Application ID: {application_id}) "
        f"has been fully repaid as on <b>{closure_date}</b>. All outstanding dues have been cleared "
        f"and the loan account is hereby marked as <b>CLOSED</b>. "
        f"No further amount is payable by the borrower against this loan.",
        _style('decl', fontSize=8.5, textColor=DARK, leading=14)
    ))
    elements.append(Spacer(1, 1.2*cm))

    sig_data = [[
        Paragraph("____________________\nAuthorized Signatory\n" + lender_name,
                  _style('sig', fontSize=8.5, textColor=DARK, alignment=TA_CENTER)),
        Paragraph(f"____________________\nDate: {closure_date}",
                  _style('sig', fontSize=8.5, textColor=DARK, alignment=TA_CENTER)),
    ]]
    sig_t = Table(sig_data, colWidths=[PAGE_W/2, PAGE_W/2])
    sig_t.setStyle(TableStyle([('TOPPADDING',(0,0),(-1,-1),4)]))
    elements.append(sig_t)

    elements.append(Spacer(1, 0.3*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    elements.append(Paragraph(
        f"System generated on {datetime.now().strftime('%d %b %Y at %I:%M %p')} · "
        f"For queries: support@loanapp.com",
        _style('ft', fontSize=7.5, textColor=GREY, alignment=TA_CENTER)
    ))

    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=loan_closure_{application_id}.pdf"})

@router.get("/credit-bureau/pdf", summary="Download Credit Bureau Update Report")
def credit_bureau_pdf(application_id: str, db: Session = Depends(get_db)):
    loan, emis, payments, lender = _fetch_data(application_id, db)

    total_emis   = len(emis)
    paid_emis    = [e for e in emis if e.status == "PAID"]
    unpaid_emis  = [e for e in emis if e.status != "PAID"]
    overdue_emis = [e for e in unpaid_emis if e.due_date and e.due_date < datetime.now().date()]

    total_paid      = sum(Decimal(str(p.amount_paid or 0)) for p in payments)
    total_emi_amt   = sum(Decimal(str(e.emi_amount))        for e in emis)
    outstanding     = loan.outstanding_amount or sum(
        Decimal(str(e.emi_amount)) for e in unpaid_emis
    )
    overdue_amount  = sum(Decimal(str(e.emi_amount)) for e in overdue_emis)

    loan_status = "CLOSED" if not unpaid_emis else ("OVERDUE" if overdue_emis else "ACTIVE")
    report_date = datetime.now().strftime("%d %b %Y")
    disburse_date = loan.disbursed_at.strftime("%d %b %Y") if loan.disbursed_at else "N/A"

    buffer  = BytesIO()
    PAGE_W  = A4[0] - 3.6*cm
    doc     = SimpleDocTemplate(buffer, pagesize=A4,
                                 leftMargin=1.8*cm, rightMargin=1.8*cm,
                                 topMargin=1.5*cm,  bottomMargin=1.5*cm)
    elements = []
    elements.append(Paragraph("CREDIT BUREAU UPDATE REPORT",
        _style('ct', fontName='Helvetica-Bold', fontSize=16,
               textColor=NAVY, alignment=TA_CENTER)))
    elements.append(Paragraph("For Official Credit Reporting Purposes",
        _style('sub', fontSize=9, textColor=GREY, alignment=TA_CENTER)))
    elements.append(Spacer(1, 0.2*cm))
    status_color = GREEN if loan_status == "CLOSED" else (AMBER if loan_status == "OVERDUE" else BLUE)
    ref_data = [[
        Paragraph(f"Report Date: <b>{report_date}</b>",
                  _style('r1', fontSize=9)),
        Paragraph(f"Application ID: <b>{application_id}</b>",
                  _style('r2', fontSize=9, alignment=TA_CENTER)),
        Paragraph(f"Loan Status: <b>{loan_status}</b>",
                  _style('r3', fontSize=9, textColor=status_color, alignment=TA_RIGHT)),
    ]]
    ref_t = Table(ref_data, colWidths=[PAGE_W/3]*3)
    ref_t.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), LIGHT),
        ('BOX',           (0,0), (-1,-1), 0.5, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
    ]))
    elements.append(ref_t)
    elements.append(Spacer(1, 0.3*cm))
    elements.append(_header_bar("  Loan Account Details", PAGE_W))
    elements.append(Spacer(1, 0.1*cm))
    elements.append(_kv_table([
        ("Account / Application ID",  application_id),
        ("Reference Number",          loan.reference_number or "N/A"),
        ("Loan Type",                 "Personal Loan"),
        ("Sanctioned Amount",         _fmt(loan.approved_amount)),
        ("Interest Rate",             f"{loan.interest_rate or 'N/A'} % p.a."),
        ("Tenure",                    f"{loan.requested_tenure_months or 'N/A'} Months"),
        ("Disbursement Date",         disburse_date),
        ("Processing Fee",            _fmt(loan.processing_fee)),
        ("Total Repayment Amount",    _fmt(loan.total_repayment)),
        ("Account Status",            loan_status),
    ], col_w=[8*cm, PAGE_W - 8*cm]))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(_header_bar("  Repayment Summary", PAGE_W))
    elements.append(Spacer(1, 0.1*cm))
    elements.append(_kv_table([
        ("Total EMIs",                str(total_emis)),
        ("EMIs Paid",                 str(len(paid_emis))),
        ("EMIs Pending",              str(len(unpaid_emis))),
        ("Overdue EMIs",              str(len(overdue_emis))),
        ("Total Amount Paid",         _fmt(total_paid)),
        ("Outstanding Amount",        _fmt(outstanding)),
        ("Overdue Amount",            _fmt(overdue_amount)),
        ("Last Payment Date",         payments[-1].created_at.strftime("%d %b %Y") if payments else "N/A"),
    ], col_w=[8*cm, PAGE_W - 8*cm]))
    if lender:
        elements.append(Spacer(1, 0.3*cm))
        elements.append(_header_bar("  Lender / Institution Details", PAGE_W))
        elements.append(Spacer(1, 0.1*cm))
        elements.append(_kv_table([
            ("Institution Name",   lender.company_name),
            ("GST Number",         lender.gst_number or "N/A"),
            ("Bank Name",          lender.lender_bank_name),
            ("Account Number",     lender.lender_account_number),
            ("IFSC Code",          lender.ifsc),
            ("Address",            lender.address or "N/A"),
        ], col_w=[8*cm, PAGE_W - 8*cm]))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(_header_bar("  Monthly Payment Track Record", PAGE_W))
    elements.append(Spacer(1, 0.1*cm))

    hdr  = _style('th', fontName='Helvetica-Bold', fontSize=8, textColor=WHITE, alignment=TA_CENTER)
    celc = _style('tc', fontSize=8, textColor=DARK, alignment=TA_CENTER)
    amts = _style('ta', fontName='Helvetica-Bold', fontSize=8, textColor=GREEN, alignment=TA_RIGHT)
    ovrd = _style('to', fontName='Helvetica-Bold', fontSize=8, textColor=AMBER, alignment=TA_CENTER)

    track_headers = [[
        Paragraph(h, hdr) for h in [
            "EMI #", "Due Date", "EMI Amount",
            "Days Overdue", "Status"
        ]
    ]]
    track_rows = []
    today = datetime.now().date()
    for e in emis:
        is_paid    = e.status == "PAID"
        is_overdue = not is_paid and e.due_date and e.due_date < today
        days_over  = (today - e.due_date).days if is_overdue else 0
        st_style   = _style('ss', fontName='Helvetica-Bold', fontSize=8,
                             textColor=GREEN if is_paid else (AMBER if is_overdue else BLUE),
                             alignment=TA_CENTER)
        track_rows.append([
            Paragraph(str(e.emi_number),                                  celc),
            Paragraph(e.due_date.strftime("%d %b %Y") if e.due_date else "-", celc),
            Paragraph(_fmtn(e.emi_amount),                                amts),
            Paragraph(str(days_over) if is_overdue else "0",              ovrd if is_overdue else celc),
            Paragraph("PAID" if is_paid else ("OVERDUE" if is_overdue else "PENDING"), st_style),
        ])

    track_table = Table(
        track_headers + track_rows,
        colWidths=[1.8*cm, 3.2*cm, 3.5*cm, 3.0*cm, 3.0*cm],
        repeatRows=1
    )
    track_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0),  NAVY),
        ('LINEBELOW',     (0,0), (-1,0),  1.5, BLUE),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [WHITE, ALT]),
        ('GRID',          (0,0), (-1,-1), 0.4, BORDER),
        ('TOPPADDING',    (0,0), (-1,-1), 7),
        ('BOTTOMPADDING', (0,0), (-1,-1), 7),
        ('LEFTPADDING',   (0,0), (-1,-1), 6),
        ('RIGHTPADDING',  (0,0), (-1,-1), 6),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(track_table)
    elements.append(Spacer(1, 0.4*cm))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    elements.append(Paragraph(
        f"This report is generated for credit bureau reporting purposes only. "
        f"Generated on {datetime.now().strftime('%d %b %Y at %I:%M %p')}. "
        f"Confidential — not for public distribution.",
        _style('ft', fontSize=7.5, textColor=GREY, alignment=TA_CENTER)
    ))

    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=credit_bureau_{application_id}.pdf"})