from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.manual_schema import PaymentModeEnum, PaymentOptionEnum
from app.services.manual_payment import process_manual_payment

router = APIRouter(prefix="/manual-payment", tags=["Payments"])


@router.post("/pay")
def manual_payment(
    application_id: int               = Query(..., description="Enter your Loan Application ID"),
    payment_mode:   PaymentModeEnum   = Query(..., description="Select payment mode"),
    payment_option: PaymentOptionEnum = Query(..., description="Select payment option"),
    db:             Session           = Depends(get_db),
):
    return process_manual_payment(
        db             = db,
        application_id = application_id,
        payment_mode   = payment_mode,
        payment_option = payment_option,
    )