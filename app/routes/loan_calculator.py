from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime
from app.core.db import get_db
from app.models.loans import Loan

router = APIRouter(prefix="/loans", tags=["Loan Calculator and Bank Deatils"])

# SYSTEM RULE – MONTHLY INTEREST
def get_monthly_interest_rate(loan_amount: float) -> float:
    if loan_amount <= 10000:
        return 0.02      # 2% monthly
    return 0.018         # 1.8% monthly

@router.post("/calculate")
def loan_calculate(user_id: UUID, loan_amount: float, tenure_months: int, db: Session = Depends(get_db)):

    # Validate loan amount limits
    if loan_amount < 5000 or loan_amount > 20000:
        raise HTTPException(status_code=400, detail="Loan amount must be between 5,000 and 20,000")

    # Check if user already has a loan
    existing_loan = db.query(Loan).filter(Loan.user_id == user_id).first()
    if existing_loan:
        raise HTTPException(status_code=400, detail="User already has a loan")

    P = loan_amount
    N = tenure_months
    R = get_monthly_interest_rate(P)

    # EMI formula
    emi_amount = round(P * R * (1 + R)**N / ((1 + R)**N - 1), 2)

    # Automatically calculate monthly interest, principal component, and GST
    monthly_interest = round(P * R, 2)
    gst_on_interest = round(monthly_interest * 0.18, 2)
    monthly_principal_component = round(emi_amount - monthly_interest, 2)

    # Save loan in DB including calculated fields
    loan = Loan(
        user_id=user_id,
        principal_amount=P,
        tenure_months=N,
        interest_rate=R,
        monthly_emi=emi_amount,
        monthly_interest=monthly_interest,    # ✅ save calculated value
        gst_on_interest=gst_on_interest,      # ✅ save calculated value
        outstanding_amount=P,
        status="CALCULATED",
        created_at=datetime.utcnow()
    )

    db.add(loan)
    db.commit()
    db.refresh(loan)

    # Return response
    return {
        "message": "Loan calculated successfully",
        "loan_id": loan.loan_id,
        "user_id": str(user_id),
        "loan_amount": P,
        "tenure_months": N,
        "monthly_interest_rate": R,
        "monthly_emi": emi_amount,
        "monthly_principal_component": monthly_principal_component,
        "monthly_interest_component": monthly_interest,
        "gst_on_interest": gst_on_interest,
        "outstanding_amount": loan.outstanding_amount,
        "created_at": loan.created_at
    }
