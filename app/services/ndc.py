from sqlalchemy.orm import Session
from app.models.emi_scheduled import EMI_Schedule
from app.models.loans import LoanApplication
from app.models.ndc_generation import NoDueCertificate

def generate_ndc(db: Session, loan_id):
    loan = db.query(LoanApplication).filter(LoanApplication.loan_id == loan_id).first()

    if not loan:
        raise Exception("Loan not found")

    if loan.application_status != "CLOSED":
        raise Exception("Loan is not closed. NDC cannot be generated")

    unpaid_emi = db.query(EMI_Schedule).filter(
        EMI_Schedule.application_id == loan.id,
        EMI_Schedule.status != "PAID"
    ).first()

    if unpaid_emi:
        raise Exception("All EMIs are not paid. NDC cannot be generated")

    existing_ndc = db.query(NoDueCertificate).filter(
        NoDueCertificate.application_id == loan.id
    ).first()

    if existing_ndc:
        return existing_ndc

    ndc = NoDueCertificate(
        loan_id=loan_id,
        pdf_url=f"/pdfs/ndc_{loan_id}.pdf"
    )

    db.add(ndc)
    db.commit()
    return ndc
