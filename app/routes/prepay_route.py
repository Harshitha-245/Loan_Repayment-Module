from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.prepayment_schema import PaymentModeEnum
from app.services.prepay import process_prepay

router = APIRouter(prefix="/prepay", tags=["Payments"])


@router.post("/pay")
def prepay_payment(
    application_id: int             = Query(..., description="Enter your Loan Application ID"),
    emi_count:      int             = Query(..., description="How many EMIs do you want to prepay?"),
    payment_mode:   PaymentModeEnum = Query(..., description="Select payment mode"),
    db:             Session         = Depends(get_db),
):
    return process_prepay(
        db             = db,
        application_id = application_id,
        emi_count      = emi_count,
        payment_mode   = payment_mode,
    )