from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta
from dateutil.relativedelta import relativedelta
from app.core.db import get_db
from app.models.loans import Loan
from app.models.emi_scheduled import EMI_Schedule

router = APIRouter(prefix="/emis",tags=["EMI Schedule"])

@router.post("/generate/{loan_id}")

def generate_emi_schedule(loan_id: str, db: Session = Depends(get_db)):

    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()

    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    # ✅ Only ACTIVE loans allowed
    if loan.status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=f"Loan not ACTIVE. Current status: {loan.status}"
        )

    # 🔥 Activation date = created_at + 32 days (30 approval + 2 activation)
    activation_date = loan.created_at + timedelta(days=32)

    # 🔥 First EMI = Activation + 30 days
    first_emi_date = (activation_date + timedelta(days=30)).date()

    # Delete old EMI schedule if exists
    db.query(EMI_Schedule).filter(EMI_Schedule.application_id == loan.loan_id).delete()
    db.commit()

    principal = float(loan.principal_amount)
    emi_amount = float(loan.monthly_emi)

    # If annual interest → convert to monthly
    monthly_rate = float(loan.interest_rate) / 12

    tenure = loan.tenure_months
    gst_rate = 0.18

    remaining = principal
    generated_emis = []

    for emi_number in range(1, tenure + 1):

        opening = round(remaining, 2)

        interest_component = round(opening * monthly_rate, 2)

        principal_component = round(emi_amount - interest_component, 2)

        # 🔥 Last EMI Adjustment
        if emi_number == tenure:
            principal_component = round(opening, 2)
            interest_component = round(emi_amount - principal_component, 2)

        closing = round(opening - principal_component, 2)

        if closing < 0:
            closing = 0.00

        gst_on_interest = round(interest_component * gst_rate, 2)

        emi = EMI_Schedule(
            application_id=loan.loan_id,
            emi_number=emi_number,
            due_date=first_emi_date + relativedelta(months=emi_number - 1),
            opening_principal=opening,
            principal_component=principal_component,
            interest_component=interest_component,
            gst_amount=gst_on_interest,
            emi_amount=emi_amount,
            closing_principal=closing,
            status="DUE"
        )

        db.add(emi)
        generated_emis.append(emi)

        remaining = closing

    db.commit()

    response = [
        {
            "emi_number": e.emi_number,
            "due_date": str(e.due_date),
            "opening_principal": float(e.opening_principal),
            "principal_component": float(e.principal_component),
            "interest_component": float(e.interest_component),
            "gst_amount": float(e.gst_amount),
            "emi_amount": float(e.emi_amount),
            "closing_principal": float(e.closing_principal),
            "status": e.status
        }
        for e in generated_emis
    ]

    return {
        "message": f"{tenure} EMI's generated successfully",
        "first_emi_date": first_emi_date,
        "emis": response
    }
