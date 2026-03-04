from datetime import timedelta
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.loans import LoanApplication
from app.models.emi_scheduled import EMISchedule
from app.services.loan_calculator import LoanCalculator


def generate_emi_schedule_service(loan_id: str, db: Session):

    loan = db.query(LoanApplication).filter(
        LoanApplication.id == loan_id
    ).first()

    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    if loan.application_status != "ACTIVE":
        raise HTTPException(
            status_code=400,
            detail=f"Loan not ACTIVE. Current status: {loan.application_status}"
        )

    activation_date = loan.created_at + timedelta(days=32)
    first_emi_date = (activation_date + timedelta(days=30)).date()

    db.query(EMISchedule).filter(
        EMISchedule.application_id == loan.id
    ).delete()
    db.commit()

    principal = Decimal(str(loan.approved_amount))
    annual_rate = Decimal(str(loan.interest_rate))
    tenure = loan.requested_tenure_months

    try:
        schedule_data = LoanCalculator.generate_schedule(
            principal=principal,
            annual_rate=annual_rate,
            tenure=tenure,
            first_emi_date=first_emi_date
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    generated_emis = []

    for item in schedule_data:

        emi = EMISchedule(
            application_id=loan.id,
            emi_number=item["emi_number"],
            due_date=item["due_date"],
            opening_principal=item["opening_principal"],
            principal_component=item["principal_component"],
            interest_component=item["interest_component"],
            gst_amount=item["gst_amount"],
            emi_amount=item["emi_amount"],
            closing_principal=item["closing_principal"],
            status="DUE"
        )

        db.add(emi)
        generated_emis.append(emi)

    db.commit()

    return {
        "message": f"{tenure} EMI's generated successfully",
        "first_emi_date": first_emi_date,
        "emi_amount": float(schedule_data[0]["emi_amount"]),
        "emis": [
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
    }