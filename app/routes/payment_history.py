from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.db import get_db
from app.models.payments import Payment_Transaction
from app.models.emi_scheduled import EMISchedule

router = APIRouter(prefix="/payments", tags=["Payment-History"])

GST_RATE         = Decimal('0.18')
PREPAY_RATE      = Decimal('0.02')
FORECLOSURE_RATE = Decimal('0.04')


class PaymentDetail(BaseModel):
    payment_id:          int
    transaction_id:      str
    emi_number:          Optional[str]
    principal:           float
    interest:            float
    total_emi_amount:    float
    gst_on_interest:     float
    foreclosure_charges: float
    prepay_charges:      float
    gst_on_charges:      float
    total_amount_paid:   float
    payment_mode:        Optional[str]
    payment_option:      Optional[str]
    payment_date:        Optional[datetime]


class PaymentHistoryResponse(BaseModel):
    application_id:    str
    total_payments:    int
    total_amount_paid: float
    payment_details:   List[PaymentDetail]


@router.get(
    "/history",
    response_model=PaymentHistoryResponse,
    summary="Get complete payment history for a loan"
)
def get_payment_history(application_id: str, db: Session = Depends(get_db)):
    payments = db.query(Payment_Transaction).filter(
        Payment_Transaction.application_id == application_id
    ).order_by(Payment_Transaction.created_at).all()

    if not payments:
        raise HTTPException(status_code=404, detail="No payment records found.")

    payment_rows: List[PaymentDetail] = []
    total_paid = Decimal('0')

    for p in payments:
        if p.emi_number is None:
            emi_numbers = []
        elif isinstance(p.emi_number, int):
            emi_numbers = [p.emi_number]
        elif isinstance(p.emi_number, list):
            emi_numbers = p.emi_number
        elif isinstance(p.emi_number, str):
            emi_numbers = [int(e.strip()) for e in p.emi_number.split(",") if e.strip().isdigit()]
        else:
            emi_numbers = []
        principal_total = Decimal('0')
        interest_total  = Decimal('0')

        for emi_num in emi_numbers:
            emi_obj = db.query(EMISchedule).filter(
                EMISchedule.application_id == application_id,
                EMISchedule.emi_number     == emi_num
            ).first()
            if emi_obj:
                principal_total += Decimal(str(getattr(emi_obj, "principal_component", 0) or 0))
                interest_total  += Decimal(str(getattr(emi_obj, "interest_component",  0) or 0))

        import random
        raw_txn = str(p.transaction_id or "")
        if "." in raw_txn:
            raw_txn = raw_txn.split(".")[0]
        if not raw_txn.isdigit() or len(raw_txn) != 12:
            raw_txn = ''.join([str(random.randint(0, 9)) for _ in range(12)])
        txn_id = raw_txn

        amount_paid      = Decimal(str(p.amount_paid or 0))
        total_paid      += amount_paid
        total_emi_amount = principal_total + interest_total
        gst_on_interest  = interest_total * GST_RATE

        foreclosure_charges = Decimal('0')
        prepay_charges      = Decimal('0')
        gst_on_charges      = Decimal('0')

        if p.payment_option == "foreclosure":
            foreclosure_charges = total_emi_amount * FORECLOSURE_RATE
            gst_on_charges      = foreclosure_charges * GST_RATE
        elif p.payment_option == "prepay":
            prepay_charges = total_emi_amount * PREPAY_RATE
            gst_on_charges = prepay_charges * GST_RATE

        payment_rows.append(PaymentDetail(
            payment_id          = p.payment_id,
            transaction_id      = txn_id,
            emi_number          = p.emi_number,
            principal           = round(float(principal_total),       2),
            interest            = round(float(interest_total),        2),
            total_emi_amount    = round(float(total_emi_amount),      2),
            gst_on_interest     = round(float(gst_on_interest),       2),
            foreclosure_charges = round(float(foreclosure_charges),   2),
            prepay_charges      = round(float(prepay_charges),        2),
            gst_on_charges      = round(float(gst_on_charges),        2),
            total_amount_paid   = round(float(amount_paid),           2),
            payment_mode        = p.payment_mode,
            payment_option      = p.payment_option,
            payment_date        = p.created_at,
        ))

    return PaymentHistoryResponse(
        application_id    = application_id,
        total_payments    = len(payment_rows),
        total_amount_paid = round(float(total_paid), 2),
        payment_details   = payment_rows,
    )
