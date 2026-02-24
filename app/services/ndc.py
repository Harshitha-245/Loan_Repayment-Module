from sqlalchemy.orm import Session
from app.models.users import Loan, EMI_Schedule, NoDueCertificate


def generate_ndc(db: Session, loan_id):
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()

    if not loan:
        raise Exception("Loan not found")

    if loan.status != "CLOSED":
        raise Exception("Loan is not closed. NDC cannot be generated")

    unpaid_emi = db.query(EMI_Schedule).filter(
        EMI_Schedule.loan_id == loan_id,
        EMI_Schedule.status != "PAID"
    ).first()

    if unpaid_emi:
        raise Exception("All EMIs are not paid. NDC cannot be generated")

    existing_ndc = db.query(NoDueCertificate).filter(
        NoDueCertificate.loan_id == loan_id
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
