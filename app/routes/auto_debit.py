import uuid
from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.db import get_db
from app.models.payments import Payment_Transaction
from app.models.reminder_log import Reminder_Log

router = APIRouter(prefix="/auto-debit", tags=["Payment"])

ALLOWED_PAYMENT_OPTIONS = ["bank_transfer", "upi", "credit_card"]

class AutoDebitRequest(BaseModel):
    application_id: str
    emi_number: int
    emi_amount: float

@router.post("/pay/{payment_option}")
def auto_debit_payment(
    request: AutoDebitRequest,
    payment_option: str = Path(..., description="upi / bank_transfer / credit_card"),
    db: Session = Depends(get_db)
):
    if payment_option not in ALLOWED_PAYMENT_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid payment_option. Choose one of {ALLOWED_PAYMENT_OPTIONS}")

    try:
        app_id = uuid.UUID(request.application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application_id")

    reminder = (
        db.query(Reminder_Log)
        .filter(Reminder_Log.application_id == app_id, Reminder_Log.emi_number == request.emi_number)
        .order_by(desc(Reminder_Log.sent_at))
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found for this EMI")

    payment = Payment_Transaction(
        application_id=app_id,
        emi_number=request.emi_number,
        amount_paid=request.emi_amount,
        payment_mode="auto_debit",        # 🔹 auto_debit
        payment_option=payment_option,     # 🔹 upi / bank_transfer / credit_card
        created_at=reminder.sent_at
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "message": f"EMI {request.emi_number} auto debited successfully via {payment_option}",
        "payment_id": str(payment.payment_id),
        "created_at": payment.created_at,
        "status": "completed"
    }