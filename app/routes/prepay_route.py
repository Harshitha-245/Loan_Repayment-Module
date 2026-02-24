from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID, uuid4

from app.core.db import get_db
from app.models.payments import Payment_Transaction
from app.models.reminder_log import Reminder_Log
from app.models.prepay_request import Prepayment_Request

router = APIRouter(prefix="/prepayment", tags=["Payment"])


class PrepayRequest(BaseModel):
    application_id: str
    emi_ids: list[int]
    payment_mode: str          # manual / auto_debit
    payment_option: str        # upi / bank_transfer / credit_card


@router.post("/pay")
def prepayment(request: PrepayRequest, db: Session = Depends(get_db)):

    if not request.emi_ids:
        raise HTTPException(status_code=400, detail="No EMIs selected")

    try:
        app_id = UUID(request.application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application_id")

    if min(request.emi_ids) <= 3:
        raise HTTPException(status_code=400, detail="Prepayment not allowed for first 3 EMIs")

    total_emi_amount = 0
    reminder_date = None

    for emi_num in request.emi_ids:

        reminder = (
            db.query(Reminder_Log)
            .filter(
                Reminder_Log.application_id == app_id,
                Reminder_Log.emi_number == emi_num
            )
            .order_by(desc(Reminder_Log.sent_at))
            .first()
        )

        if not reminder:
            raise HTTPException(status_code=404, detail=f"Reminder not found for EMI {emi_num}")

        emi_amount = 1863.18   # 🔥 Replace with actual EMI fetch logic
        total_emi_amount += emi_amount

        reminder.reminder_stage = "PAID(PREPAY)"

        if reminder_date is None:
            reminder_date = reminder.sent_at

    # ✅ 2% penalty
    charge = total_emi_amount * 0.02

    # ✅ 18% GST on penalty
    gst = charge * 0.18

    # ✅ Final payable
    final_amount = total_emi_amount + charge + gst

    # ✅ Insert into Prepayment table
    prepay_entry = Prepayment_Request(
        application_id=app_id,
        amount=final_amount,
        charge=charge,
        gst=gst,
        status="COMPLETED"
    )

    db.add(prepay_entry)

    # ✅ Insert single Payment row
    payment_record = Payment_Transaction(
        payment_id=uuid4(),
        application_id=app_id,
        emi_number=",".join(map(str, request.emi_ids)),   # "4,5"
        amount_paid=final_amount,
        payment_mode=f"{request.payment_mode}(prepay)",   # manual(prepay)
        payment_option=request.payment_option,            # upi / bank_transfer / credit_card
        created_at=reminder_date
    )

    db.add(payment_record)
    db.commit()

    return {
        "message": "Prepayment successful",
        "emi_numbers": request.emi_ids,
        "emi_total": total_emi_amount,
        "penalty_2_percent": charge,
        "gst_18_percent": gst,
        "final_amount_paid": final_amount
    }