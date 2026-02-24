import uuid
from fastapi import APIRouter, HTTPException, Depends, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.db import get_db
from app.models.payments import Payment_Transaction
from app.models.reminder_log import Reminder_Log

router = APIRouter(prefix="/manual-payment", tags=["Payment"])

ALLOWED_PAYMENT_OPTIONS = ["bank_transfer", "upi", "credit_card"]

class ManualPaymentRequest(BaseModel):
    application_id: str
    emi_number: int
    emi_amount: float
    account_number: str | None = None
    ifsc_code: str | None = None
    upi_id: str | None = None
    card_number: str | None = None
    cvv: str | None = None

@router.post("/pay/{payment_option}")
def manual_payment(
    request: ManualPaymentRequest,
    payment_option: str = Path(..., description="upi / bank_transfer / credit_card"),
    db: Session = Depends(get_db)
):
    if payment_option not in ALLOWED_PAYMENT_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid payment_option. Choose one of {ALLOWED_PAYMENT_OPTIONS}")

    # Validate required details based on payment_option
    if payment_option == "bank_transfer" and (not request.account_number or not request.ifsc_code):
        raise HTTPException(status_code=400, detail="Bank account_number and ifsc_code required")
    if payment_option == "upi" and not request.upi_id:
        raise HTTPException(status_code=400, detail="UPI ID required")
    if payment_option == "credit_card" and (not request.card_number or not request.cvv):
        raise HTTPException(status_code=400, detail="Card number and CVV required")

    try:
        app_id = uuid.UUID(request.application_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid application_id")

    # Get last reminder sent_at
    reminder = (
        db.query(Reminder_Log)
        .filter(Reminder_Log.application_id == app_id, Reminder_Log.emi_number == request.emi_number)
        .order_by(desc(Reminder_Log.sent_at))
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found for this EMI")

    # Create payment
    payment = Payment_Transaction(
        application_id=app_id,
        emi_number=request.emi_number,
        amount_paid=request.emi_amount,
        payment_mode="manual",       # 🔹 manual
        payment_option=payment_option,  # 🔹 upi / bank_transfer / credit_card
        created_at=reminder.sent_at
    )

    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "message": f"EMI {request.emi_number} paid successfully via {payment_option}",
        "payment_id": str(payment.payment_id),
        "created_at": payment.created_at,
        "status": "success"
    }