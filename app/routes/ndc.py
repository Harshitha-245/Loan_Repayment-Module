from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from app.core.db import get_db
from app.models.loans import Loan
from app.models.payments import Payment_Transaction

router = APIRouter(prefix="/ndc", tags=["Loan Closure and NDC certificate"])

# ── Constants ─────────────────────────────────────────────────────────────────
NBFC_NAME       = "ABC Finance Private Limited"
NBFC_ADDRESS    = "123, Financial District, Hyderabad - 500032, Telangana"
NBFC_CONTACT    = "Phone: 040-12345678  |  Email: support@abcfinance.in"
NBFC_REG        = "NBFC Reg No: N-07.00000.00.000  |  RBI Reg No: B-01.00000"
USER_NAME       = "Harshitha"
BANK_NAME       = "State Bank of India"
BRANCH_NAME     = "Hyderabad Main Branch"
ACCOUNT_HOLDER  = "Harshitha"
ACCOUNT_NUMBER  = "456789123456"
IFSC_CODE       = "SBIN0002456"
LOAN_AMOUNT     = "15,000.00"
LOAN_START_DATE = "26 April 2026"
LOAN_CLOSE_DATE = "30 September 2026"

# ── Style helpers ─────────────────────────────────────────────────────────────
def s(name, **kw): return ParagraphStyle(name, **kw)
def p(text, style): return Paragraph(text, style)

CENTER = s("c",  fontName="Helvetica",         fontSize=8,   alignment=TA_CENTER,  textColor=colors.HexColor("#555"), leading=12)
TITLE  = s("t",  fontName="Helvetica-Bold",    fontSize=12,  alignment=TA_CENTER,  textColor=colors.HexColor("#1B3A6B"), spaceBefore=5, spaceAfter=4)
BODY   = s("b",  fontName="Helvetica",         fontSize=9.5, alignment=TA_JUSTIFY, textColor=colors.HexColor("#222"), leading=14, spaceAfter=5)
REF    = s("r",  fontName="Helvetica",         fontSize=8.5, alignment=TA_LEFT,    textColor=colors.HexColor("#333"))
REF_R  = s("rr", fontName="Helvetica",         fontSize=8.5, alignment=2,          textColor=colors.HexColor("#333"))
HDR    = s("h",  fontName="Helvetica-Bold",    fontSize=9.5, alignment=TA_LEFT,    textColor=colors.white)
SIGN   = s("sg", fontName="Helvetica",         fontSize=8.5, alignment=TA_CENTER,  textColor=colors.HexColor("#555"))
SIGN_B = s("sb", fontName="Helvetica-Bold",    fontSize=8.5, alignment=TA_CENTER,  textColor=colors.HexColor("#1B3A6B"))
FOOT   = s("f",  fontName="Helvetica-Oblique", fontSize=7,   alignment=TA_CENTER,  textColor=colors.HexColor("#888"))
GREEN  = s("g",  fontName="Helvetica-Bold",    fontSize=10,  alignment=TA_CENTER,  textColor=colors.HexColor("#1B7B34"))
NBFC_S = s("ns", fontName="Helvetica-Bold",    fontSize=15,  alignment=TA_CENTER,  textColor=colors.HexColor("#1B3A6B"), spaceAfter=2)

# ── Reusable table style ──────────────────────────────────────────────────────
def key_val_table(rows, col_w, green_rows=[]):
    t = Table(rows, colWidths=col_w)
    style = [
        ("BACKGROUND",     (0, 0), (-1, 0),  colors.HexColor("#1B3A6B")),
        ("SPAN",           (0, 0), (-1, 0)),
        ("TEXTCOLOR",      (0, 0), (-1, 0),  colors.white),
        ("BACKGROUND",     (0, 1), (0, -1),  colors.HexColor("#EEF2F8")),
        ("FONTNAME",       (0, 1), (0, -1),  "Helvetica-Bold"),
        ("FONTNAME",       (1, 1), (1, -1),  "Helvetica"),
        ("FONTSIZE",       (0, 0), (-1, -1), 9),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("GRID",           (0, 0), (-1, -1), 0.4, colors.HexColor("#CCC")),
        ("PADDING",        (0, 0), (-1, -1), 6),
        ("VALIGN",         (0, 0), (-1, -1), "MIDDLE"),
    ]
    for row_idx in green_rows:
        style.append(("TEXTCOLOR", (1, row_idx), (1, row_idx), colors.HexColor("#1B7B34")))
        style.append(("FONTNAME",  (1, row_idx), (1, row_idx), "Helvetica-Bold"))
    t.setStyle(TableStyle(style))
    return t


# ── Route ─────────────────────────────────────────────────────────────────────
@router.get("/no-due-certificate/{application_id}")
def no_due_certificate(application_id: str, db: Session = Depends(get_db)):
    try:
        loan = db.query(Loan).filter(Loan.loan_id == application_id).first()
        if not loan:
            raise HTTPException(404, "Loan not found")
        if getattr(loan, "status", "") != "closed":
            raise HTTPException(400, "Loan is not closed yet")

        total_paid = sum(
            float(x.amount_paid or 0)
            for x in db.query(Payment_Transaction)
            .filter(Payment_Transaction.application_id == application_id).all()
        )

        ref_no = f"REF/NDC/20260930/{str(application_id)[:8].upper()}"
        buf    = BytesIO()
        doc    = SimpleDocTemplate(buf, pagesize=A4,
                    leftMargin=1.8*cm, rightMargin=1.8*cm,
                    topMargin=1.2*cm, bottomMargin=1.2*cm)
        E = []

        # ── Letterhead
        E.append(HRFlowable(width="100%", thickness=6,
            color=colors.HexColor("#1B3A6B"), spaceAfter=5))
        E.append(p(NBFC_NAME, NBFC_S))
        for line in [NBFC_ADDRESS, NBFC_CONTACT, NBFC_REG]:
            E.append(p(line, CENTER))
        E.append(HRFlowable(width="100%", thickness=0.6,
            color=colors.HexColor("#CCC"), spaceBefore=4, spaceAfter=6))

        # ── Ref & Date
        E.append(Table([
            [p(f"Ref No: <b>{ref_no}</b>", REF),
             p(f"Date: <b>{LOAN_CLOSE_DATE}</b>", REF_R)]
        ], colWidths=[9*cm, 9*cm]))
        E.append(Spacer(1, 0.2*cm))

        # ── Title
        E.append(p("NO DUE CERTIFICATE", TITLE))

        # ── Green certified box
        cert = Table([[p("<b>✓  CERTIFIED — NO OUTSTANDING DUES</b>", GREEN)]],
                     colWidths=[16.4*cm])
        cert.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F0FFF4")),
            ("BOX",        (0, 0), (-1, -1), 1.2, colors.HexColor("#1B7B34")),
            ("PADDING",    (0, 0), (-1, -1), 7),
        ]))
        E.append(cert)
        E.append(Spacer(1, 0.25*cm))

        # ── Body
        E.append(p("To,", BODY))
        E.append(p(f"<b>{USER_NAME}</b><br/>Hyderabad, Telangana", BODY))
        E.append(Spacer(1, 0.1*cm))
        E.append(p(f"<b>Subject: No Due Certificate — Loan Account No. {application_id}</b>", BODY))
        E.append(p("Dear Harshitha,", BODY))
        E.append(p(
            f"This is to certify that <b>{USER_NAME}</b> availed a loan of <b>Rs. {LOAN_AMOUNT}</b> "
            f"from <b>{NBFC_NAME}</b> on <b>{LOAN_START_DATE}</b>. All EMI instalments have been duly "
            f"paid and the loan account has been <b>fully closed on {LOAN_CLOSE_DATE}</b>. "
            f"There are <b>NO OUTSTANDING DUES</b> against this account and all obligations stand fully discharged.",
            BODY))
        E.append(Spacer(1, 0.2*cm))

        # ── Loan Details Table
        loan_rows = [
            [p("<b>  Loan Account Details</b>", HDR), ""],
            ["Loan Account No.",    str(application_id)],
            ["Borrower Name",       USER_NAME],
            ["Sanctioned Amount",   f"Rs. {LOAN_AMOUNT}"],
            ["Disbursement Date",   LOAN_START_DATE],
            ["Total Amount Repaid", f"Rs. {total_paid:.2f}"],
            ["Loan Closure Date",   LOAN_CLOSE_DATE],
            ["Outstanding Dues",    "NIL"],
            ["Loan Status",         "CLOSED"],
        ]
        E.append(key_val_table(loan_rows, [5.5*cm, 10.9*cm], green_rows=[7, 8]))
        E.append(Spacer(1, 0.25*cm))

        # ── Bank Details Table ✅ clean single column
        bank_rows = [
            [p("<b>  Bank Account Details</b>", HDR), ""],
            ["Bank Name",      BANK_NAME],
            ["Branch",         BRANCH_NAME],
            ["Account Holder", ACCOUNT_HOLDER],
            ["Account Number", ACCOUNT_NUMBER],
            ["IFSC Code",      IFSC_CODE],
        ]
        E.append(key_val_table(bank_rows, [5.5*cm, 10.9*cm]))
        E.append(Spacer(1, 0.25*cm))

        # ── Note
        E.append(p(
            "This certificate is issued upon the request of the borrower for official and "
            "personal record purposes. This is a system-generated document.", BODY))
        E.append(Spacer(1, 0.3*cm))

        # ── Signature
        E.append(Table([
            [p("________________________", SIGN),  p("________________________", SIGN)],
            [p("Authorized Signatory",    SIGN),  p("Branch Manager",          SIGN)],
            [p(NBFC_NAME,               SIGN_B), p(NBFC_NAME,               SIGN_B)],
        ], colWidths=[8.2*cm, 8.2*cm]))

        # ── Footer
        E.append(Spacer(1, 0.3*cm))
        E.append(HRFlowable(width="100%", thickness=0.6,
            color=colors.HexColor("#CCC"), spaceAfter=3))
        E.append(p(f"System Generated Document  |  {NBFC_NAME}  |  {NBFC_ADDRESS}", FOOT))

        doc.build(E)
        buf.seek(0)
        return StreamingResponse(buf, media_type="application/pdf",
            headers={"Content-Disposition":
                f"attachment; filename=no_due_certificate_{application_id}.pdf"})

    except HTTPException:
        raise
    except Exception as e:
        import traceback; traceback.print_exc()
        raise HTTPException(500, str(e))