from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from app.core.db import get_db
from app.models.loans import LoanApplication
from app.models.payments import Payment_Transaction
from app.models.users import User
from app.models.bank_details import Bank_Details
from app.models.ndc_generation import NoDueCertificate

router = APIRouter(prefix="/ndc", tags=["NDC certificate"])
def s(name, **kw): return ParagraphStyle(name, **kw)
def p(text, style): return Paragraph(text, style)

CENTER = s("c", fontName="Helvetica", fontSize=8, alignment=TA_CENTER, textColor=colors.HexColor("#555"), leading=12)
TITLE  = s("t", fontName="Helvetica-Bold", fontSize=12, alignment=TA_CENTER, textColor=colors.HexColor("#1B3A6B"), spaceBefore=5, spaceAfter=4)
BODY   = s("b", fontName="Helvetica", fontSize=9.5, alignment=TA_JUSTIFY, textColor=colors.HexColor("#222"), leading=14, spaceAfter=5)
REF    = s("r", fontName="Helvetica", fontSize=8.5, alignment=TA_LEFT, textColor=colors.HexColor("#333"))
REF_R  = s("rr", fontName="Helvetica", fontSize=8.5, alignment=2, textColor=colors.HexColor("#333"))
HDR    = s("h", fontName="Helvetica-Bold", fontSize=9.5, alignment=TA_LEFT, textColor=colors.white)
GREEN  = s("g", fontName="Helvetica-Bold", fontSize=10, alignment=TA_CENTER, textColor=colors.HexColor("#1B7B34"))
NBFC_S = s("ns", fontName="Helvetica-Bold", fontSize=15, alignment=TA_CENTER, textColor=colors.HexColor("#1B3A6B"), spaceAfter=2)
FOOT   = s("f", fontName="Helvetica-Oblique", fontSize=7, alignment=TA_CENTER, textColor=colors.HexColor("#888"))

def key_val_table(rows, col_w, green_rows=[]):
    t = Table(rows, colWidths=col_w)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1B3A6B")),
        ("SPAN", (0, 0), (-1, 0)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#EEF2F8")),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 1), (1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCC")),
        ("PADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for row_idx in green_rows:
        style.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), colors.HexColor("#1B7B34")))
        style.append(("FONTNAME",  (1, row_idx), (1, row_idx), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return t

@router.get("/generate/{application_id}")
def dowmload_ndc(application_id: int, db: Session = Depends(get_db)):
    loan = db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
    if not loan:
        raise HTTPException(404, "Loan not found")
    if loan.application_status != "CLOSED":
        raise HTTPException(400, "Loan is not closed yet")

    user = db.query(User).filter(User.user_id == loan.user_id).first()
    if not user:
        raise HTTPException(404, "User not found")

    bank = db.query(Bank_Details).filter(Bank_Details.user_id == user.user_id).first()

    payments = db.query(Payment_Transaction).filter(Payment_Transaction.application_id == application_id).all()
    total_paid = sum(float(p.amount_paid or 0) for p in payments)

    disbursed_date = loan.disbursed_at
    closure_date = max([p.created_at for p in payments]) if payments else datetime.now()
    
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=1.8*cm, rightMargin=1.8*cm, topMargin=1.2*cm, bottomMargin=1.2*cm)
    E = []

    NBFC_NAME = "ABC Finance Private Limited"
    E.append(p(NBFC_NAME, NBFC_S))
    for line in ["123, Financial District, Hyderabad - 500032, Telangana", 
                 "Phone: 040-12345678 | Email: support@abcfinance.in", 
                 "NBFC Reg No: N-07.00000.00.000 | RBI Reg No: B-01.00000"]:
        E.append(p(line, CENTER))
    E.append(Spacer(1, 0.3*cm))
    E.append(p("To,", BODY))
    E.append(p(f"<b>{user.name}</b>", BODY))
    E.append(p("Hyderabad, Telangana", BODY))
    E.append(Spacer(1, 0.1*cm))
    E.append(p(f"<b>Subject: No Due Certificate — Loan Account No. {application_id}</b>", BODY))
    E.append(p(f"Dear {user.name},", BODY))
    E.append(p(
        f"This is to certify that <b>{user.name}</b> availed a loan of <b>Rs. {loan.approved_amount:,.2f}</b> "
        f"from <b>{NBFC_NAME}</b> on <b>{disbursed_date.strftime('%d %B %Y') if disbursed_date else 'N/A'}</b>. "
        f"All EMI instalments have been duly paid and the loan account has been "
        f"<b>fully closed on {closure_date.strftime('%d %B %Y')}</b>. "
        f"There are <b>NO OUTSTANDING DUES</b> against this account and all obligations stand fully discharged.",
        BODY))
    E.append(Spacer(1, 0.2*cm))

    loan_rows = [
        [p("<b>Loan Account Details</b>", HDR), ""],
        ["Loan Account No.", str(application_id)],
        ["Borrower Name", user.name],
        ["Sanctioned Amount", f"Rs. {loan.approved_amount:,.2f}"],
        ["Disbursement Date", disbursed_date.strftime('%d %B %Y') if disbursed_date else 'N/A'],
        ["Total Amount Repaid", f"Rs. {total_paid:,.2f}"],
        ["Loan Closure Date", closure_date.strftime('%d %B %Y')],
        ["Outstanding Dues", "NIL"],
        ["Loan Status", "CLOSED"],
    ]
    E.append(key_val_table(loan_rows, [6*cm, 10*cm], green_rows=[7, 8]))
    E.append(Spacer(1, 0.25*cm))
    bank_rows = [
        [p("<b>Bank Account Details</b>", HDR), ""],
        ["Bank Name", bank.bank_name if bank else "-"],
        ["Branch", bank.bank_name if bank else "-"],
        ["Account Holder", bank.account_holder_name if bank else "-"],
        ["Account Number", bank.account_number if bank else "-"],
        ["IFSC Code", bank.ifsc if bank else "-"],
    ]
    E.append(key_val_table(bank_rows, [6*cm, 10*cm]))
    E.append(Spacer(1, 0.25*cm))

    E.append(p("This certificate is issued upon the request of the borrower for official and personal record purposes. This is a system-generated document.", BODY))
    doc.build(E)
    buf.seek(0)
    existing_ndc = db.query(NoDueCertificate).filter(NoDueCertificate.application_id == application_id).first()
    if not existing_ndc:
        ndc = NoDueCertificate(application_id=application_id, pdf_url=f"/ndc/download/{application_id}")
        db.add(ndc)
        db.commit()

    return StreamingResponse(buf, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=no_due_certificate_{application_id}.pdf"})