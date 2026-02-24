# foreclosure_modified_v2.py
import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.core.db import get_db
from app.models.loans import Loan
from app.models.emi_scheduled import EMI_Schedule
from app.models.payments import Payment_Transaction
from app.models.reminder_log import Reminder_Log
from app.models.foreclosure_request import Foreclosure_Request

router = APIRouter(prefix="/foreclosure", tags=["Payment"])

@router.post("/pay/{loan_id}")
def foreclosure_payment(loan_id: UUID, payment_mode: str = "auto_debit", payment_option: str = "upi", db: Session = Depends(get_db)):

    # 🔹 Fetch loan
    loan = db.query(Loan).filter(Loan.loan_id == loan_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    # 🔹 Prevent double foreclosure
    if loan.status == "Closed":
        raise HTTPException(status_code=400, detail="Loan already closed")

    # 🔹 Get pending EMIs 6,7,8,9 only
    pending_emis = db.query(EMI_Schedule).filter(
        EMI_Schedule.application_id == loan_id,
        EMI_Schedule.status != "PAID",
        EMI_Schedule.emi_number >= 6
    ).order_by(EMI_Schedule.emi_number).all()

    if not pending_emis:
        raise HTTPException(status_code=400, detail="No pending EMIs 6-9")

    # 🔹 Total outstanding
    total_outstanding = sum(float(emi.emi_amount) for emi in pending_emis)

    # 🔹 Foreclosure charge 4% + GST 18%
    foreclosure_charge = total_outstanding * 0.04
    gst = foreclosure_charge * 0.18
    total_payable = total_outstanding + foreclosure_charge + gst

    # 🔹 Mark EMIs as PAID
    for emi in pending_emis:
        emi.status = "PAID"

    # 🔹 Close loan
    loan.status = "Closed"
    loan.outstanding_amount = 0
    loan.closed_at = datetime.utcnow() if hasattr(loan, "closed_at") else None

    # 🔹 Get first unpaid EMI's last reminder.sent_at for created_at
    first_emi_num = pending_emis[0].emi_number  # should be 6
    first_reminder = db.query(Reminder_Log).filter(
        Reminder_Log.application_id == loan_id,
        Reminder_Log.emi_number == first_emi_num
    ).order_by(Reminder_Log.sent_at.desc()).first()
    created_at_for_payment = first_reminder.sent_at if first_reminder else datetime.utcnow()

    # 🔹 Comma-separated EMI numbers
    emi_numbers_str = ",".join(str(emi.emi_number) for emi in pending_emis)

    try:
        # 🔹 Insert single payment row
        payment_entry = Payment_Transaction(
            payment_id=uuid.uuid4(),
            application_id=loan.loan_id,
            emi_number=emi_numbers_str,
            amount_paid=total_payable,
            payment_mode=f"{payment_mode}(FORECLOSURE)",   # e.g., auto_debit(FORECLOSURE)
            payment_option=payment_option,
            created_at=created_at_for_payment            # last reminder.sent_at of EMI 6
        )
        db.add(payment_entry)

        # 🔹 Insert into foreclosure table
        foreclosure_entry = Foreclosure_Request(
            id=uuid.uuid4(),
            application_id=loan.loan_id,
            outstanding=total_outstanding,
            charge=foreclosure_charge,
            gst=gst,
            status="COMPLETED"
        )
        db.add(foreclosure_entry)

        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Foreclosure failed: {str(e)}")

    return {
        "message": "Loan foreclosed successfully for EMIs 6-9",
        "total_outstanding": total_outstanding,
        "foreclosure_charge": foreclosure_charge,
        "gst": gst,
        "total_paid": total_payable,
        "emi_numbers": emi_numbers_str,
        "payment_mode": f"{payment_mode}(FORECLOSURE)",
        "payment_option": payment_option,
        "created_at": created_at_for_payment
    }