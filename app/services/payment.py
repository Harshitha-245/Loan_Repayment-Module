from fastapi import HTTPException


def process_payment(session, details=None):

    # AUTO DEBIT
    if session["payment_mode"] == "auto_debit":
        return {
            "status": "PAID",
            "message": "Auto debit successful"
        }

    # MANUAL
    if session["payment_mode"] == "manual":

        if not details:
            raise HTTPException(
                status_code=400,
                detail="Payment details required for manual mode"
            )

        return {
            "status": "PAID",
            "payment_method": details.payment_option,
            "message": "Manual payment successful"
        }

    raise HTTPException(status_code=400, detail="Invalid payment mode")





# populate_payments.py

import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.payments import Payment_Transaction
from app.models.emi_scheduled import EMI_Schedule

# Payment types and modes
PAYMENT_MANUAL = "manual"
PAYMENT_AUTO = "auto_debit"

MODE_BANK = "bank_transfer"
MODE_UPI = "upi"

# Define which EMIs are manual, prepay, foreclosure
MANUAL_EMIS = [1, 2]
PREPAY_EMIS = [4, 5]
FORECLOSURE_EMIS = [6, 7, 8, 9]

def populate_payments(db: Session, application_id: str):
    # Fetch all EMI schedules for this application
    emi_schedules = db.query(EMI_Schedule).filter_by(application_id=application_id).all()

    for emi in emi_schedules:
        emi_number = emi.emi_number
        amount = emi.amount
        due_date = emi.due_date

        # Skip overdue EMI (no payment yet)
        if emi_number == 3:
            continue

        # Determine payment option and mode
        if emi_number in MANUAL_EMIS:
            payment_option = PAYMENT_MANUAL
            payment_mode = MODE_BANK
        elif emi_number in PREPAY_EMIS:
            payment_option = PAYMENT_AUTO
            payment_mode = MODE_UPI
        elif emi_number in FORECLOSURE_EMIS:
            payment_option = PAYMENT_AUTO
            payment_mode = MODE_UPI
        else:
            continue  # skip any other EMI numbers

        # Create payment row
        payment = Payment_Transaction(
            payment_id=uuid.uuid4(),
            application_id=application_id,
            emi_number=emi_number,
            amount_paid=amount,
            payment_mode=payment_mode,
            payment_option=payment_option,
            created_at=due_date  # use EMI due date
        )

        db.add(payment)

    db.commit()
    print("Payments table populated successfully.")


# Example usage
if __name__ == "__main__":
    from app.core.db import SessionLocal

    db = SessionLocal()
    application_id = "YOUR-LOAN-ID-HERE"  # <-- replace with your loan/application ID
    populate_payments(db, application_id)
    db.close()
