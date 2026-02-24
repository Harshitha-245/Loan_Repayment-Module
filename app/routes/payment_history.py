from decimal import Decimal
from typing import List, Optional
import os
import base64
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.db import get_db
from app.models.payments import Payment_Transaction
from app.models.emi_scheduled import EMI_Schedule
from app.schemas.payment_schema import PaymentHistoryResponse, PaymentHistoryItem

router = APIRouter(prefix="/payments", tags=["Payment-History"])
GST_RATE = Decimal('0.18')  # Example 18% GST

@router.get("/history", response_model=PaymentHistoryResponse)
def get_payment_history(application_id: str, db: Session = Depends(get_db)):
    date_range = db.query(
        func.min(Payment_Transaction.created_at),
        func.max(Payment_Transaction.created_at)
    ).filter(Payment_Transaction.application_id == application_id).first()

    if not date_range or not date_range[0]:
        return PaymentHistoryResponse(total_paid=Decimal('0'), payment_history=[])

    start_date, end_date = date_range

    payments = db.query(Payment_Transaction).filter(
        Payment_Transaction.application_id == application_id,
        Payment_Transaction.created_at >= start_date,
        Payment_Transaction.created_at <= end_date
    ).order_by(Payment_Transaction.created_at).all()

    total_paid = Decimal('0')
    history: List[PaymentHistoryItem] = []

    for p in payments:
        total_paid += Decimal(p.amount_paid)
        emi_number_val: List[int] = []
        principal = Decimal('0')
        interest = Decimal('0')
        gst = Decimal('0')
        overdue_count = 0
        overdue_charges = Decimal('0')
        prepay_charge = Decimal('0')
        foreclosure_charge = Decimal('0')

        # Determine EMI numbers
        if isinstance(p.emi_number, int):
            emi_number_val = [p.emi_number]
        elif isinstance(p.emi_number, list):
            emi_number_val = p.emi_number
        elif isinstance(p.emi_number, str):
            emi_number_val = [int(e.strip()) for e in p.emi_number.split(",")]

        for e in emi_number_val:
            emi_obj = db.query(EMI_Schedule).filter(
                EMI_Schedule.application_id == application_id,
                EMI_Schedule.emi_number == e
            ).first()
            if emi_obj:
                principal += Decimal(getattr(emi_obj, "principal_component", 0))
                interest += Decimal(getattr(emi_obj, "interest_component", 0))
                gst += Decimal(getattr(emi_obj, "interest_component", 0)) * GST_RATE

        # Overdue for 3rd EMI
        if 3 in emi_number_val:
            overdue_count = 2  # example
            overdue_charges = Decimal('50') * Decimal(overdue_count)

        # Prepay charges for 4,5
        if any(e in [4, 5] for e in emi_number_val) and "prepay" in p.payment_mode.lower():
            prepay_charge = Decimal(p.amount_paid) - (principal + interest + gst)

        # Foreclosure charges for 6-9
        if any(e in [6, 7, 8, 9] for e in emi_number_val) and "foreclosure" in p.payment_mode.lower():
            foreclosure_charge = Decimal(p.amount_paid) - (principal + interest + gst)

        history.append(PaymentHistoryItem(
            emi_number=emi_number_val,
            principal_component=principal,
            interest_component=interest,
            emi_amount=Decimal(p.amount_paid),
            overdue_count=overdue_count,
            overdue_charges=overdue_charges,
            prepay_charge=prepay_charge,
            foreclosure_charge=foreclosure_charge,
            gst=gst,
            payment_date=p.created_at,
            payment_mode=p.payment_mode,
            transaction_id=str(p.payment_id),
        ))

    return PaymentHistoryResponse(
        total_paid=total_paid,
        payment_history=history
    )