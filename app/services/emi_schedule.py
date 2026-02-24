import math, os
from datetime import timedelta
from sqlalchemy.orm import Session
from app.models.users import EMI_Schedule, Loan

GST = float(os.getenv("GST_RATE")) / 100

def generate_emi_schedule(db: Session, loan: Loan):
    if loan.status != "ACTIVE":
        return

    principal_per_month = loan.principal_amount / loan.tenure_months
    interest_per_month = (loan.principal_amount * loan.interest_rate / 100) / loan.tenure_months

    for i in range(1, loan.tenure_months + 1):
        interest = round(interest_per_month, 2)
        gst = round(interest * GST, 2)

        emi_amount = math.ceil(principal_per_month + interest + gst)

        db.add(EMI_Schedule(
            loan_id=loan.loan_id,
            emi_number=i,
            due_date=loan.created_at.date() + timedelta(days=30*i),
            principal_component=round(principal_per_month,2),
            interest_component=interest,
            gst_amount=gst,
            emi_amount=emi_amount
        ))

    db.commit()
