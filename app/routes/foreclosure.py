from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.schemas.foreclosure_schema import PaymentModeEnum
from app.services.foreclosure import process_foreclosure

router = APIRouter(prefix="/foreclosure", tags=["Payments"])

@router.post("/pay")
def foreclosure_payment(
    application_id: int             = Query(..., description="Enter your Loan Application ID"),
    payment_mode:   PaymentModeEnum = Query(..., description="Select payment mode"),
    db:             Session         = Depends(get_db),
):
    return process_foreclosure(
        db             = db,
        application_id = application_id,
        payment_mode   = payment_mode,
    )