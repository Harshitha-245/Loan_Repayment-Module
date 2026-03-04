from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.auto_debit_schema import PaymentModeEnum, PaymentOptionEnum
from app.services.auto_debit_payment import process_auto_debit

router = APIRouter(prefix="/auto-debit", tags=["Payments"])


@router.post("/pay")
def auto_debit_payment(
    application_id: int               = Query(..., description="Enter your Loan Application ID"),
    payment_mode:   PaymentModeEnum   = Query(..., description="Select payment mode"),
    payment_option: PaymentOptionEnum = Query(..., description="Select payment option"),
    db:             Session           = Depends(get_db),
):
    return process_auto_debit(
        db             = db,
        application_id = application_id,
        payment_mode   = payment_mode,
        payment_option = payment_option,
    )