from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from app.models.payments import Payment_Transaction
from app.models.emi_scheduled import EMISchedule
from app.models.lender_table import Lender
from app.models.loans import LoanApplication
from app.models.prepay_table import Prepayment_Request
from app.schemas.prepayment_schema import (
    PaymentModeEnum,
    PrepayResponse,
    PrepayEMIItem,
    LenderUPIDetails,
    LenderBankTransferDetails,
    LenderCreditCardDetails,
)

PREPAY_PENALTY_RATE = Decimal("0.02")
PENALTY_GST_RATE    = Decimal("0.18")


def _get_due_emis(db: Session, application_id: int, count: int) -> list[EMISchedule]:
    emis = (
        db.query(EMISchedule)
        .filter(
            and_(
                EMISchedule.application_id == application_id,
                EMISchedule.status == "DUE",
            )
        )
        .order_by(EMISchedule.emi_number)
        .limit(count)
        .all()
    )
    if not emis:
        raise HTTPException(
            status_code=404,
            detail=f"No pending EMIs found for application_id {application_id}."
        )
    if len(emis) < count:
        raise HTTPException(
            status_code=400,
            detail=f"Only {len(emis)} pending EMI(s) available. You cannot prepay {count} EMIs."
        )
    return emis


def _get_lender_payment_details(
    db:             Session,
    application_id: int,
    payment_mode:   PaymentModeEnum,
) -> LenderUPIDetails | LenderBankTransferDetails | LenderCreditCardDetails:

    loan = db.query(LoanApplication).filter(LoanApplication.id == application_id).first()
    if not loan:
        raise HTTPException(status_code=404, detail="Loan application not found.")

    lender = db.query(Lender).filter(Lender.user_id == loan.user_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="No lender found for this loan application.")

    if payment_mode == PaymentModeEnum.upi:
        if not lender.lender_upi:
            raise HTTPException(status_code=400, detail="No UPI ID linked for this lender.")
        return LenderUPIDetails(
            lender_upi                 = lender.lender_upi,
            lender_account_holder_name = lender.lender_account_holder_name,
        )

    elif payment_mode == PaymentModeEnum.bank_transfer:
        return LenderBankTransferDetails(
            lender_account_holder_name = lender.lender_account_holder_name,
            lender_account_number      = lender.lender_account_number,
            ifsc                       = lender.ifsc,
            lender_bank_name           = lender.lender_bank_name,
        )

    elif payment_mode == PaymentModeEnum.credit_card:
        if not lender.lender_card_number:
            raise HTTPException(status_code=400, detail="No credit card linked for this lender.")
        return LenderCreditCardDetails(
            lender_account_holder_name = lender.lender_account_holder_name,
            lender_card_number         = f"**** **** **** {lender.lender_card_number[-4:]}",
            lender_card_type           = lender.lender_card_type or "N/A",
            lender_expiry              = lender.lender_expiry or "N/A",
        )

def process_prepay(
    db:             Session,
    application_id: int,
    emi_count:      int,
    payment_mode:   PaymentModeEnum,
) -> PrepayResponse:

    emis            = _get_due_emis(db, application_id, emi_count)
    payment_details = _get_lender_payment_details(db, application_id, payment_mode)

    total_emi_amount = sum(Decimal(str(e.emi_amount))          for e in emis)
    total_principal  = sum(Decimal(str(e.principal_component)) for e in emis)
    total_interest   = sum(Decimal(str(e.interest_component))  for e in emis)
    total_gst        = sum(Decimal(str(e.gst_amount))          for e in emis)

    prepay_penalty   = (total_principal * PREPAY_PENALTY_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    penalty_gst      = (prepay_penalty  * PENALTY_GST_RATE).quantize(Decimal("0.01"),   rounding=ROUND_HALF_UP)
    total_payable    = (total_emi_amount + prepay_penalty + penalty_gst).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    emi_numbers_str = ",".join(str(e.emi_number) for e in emis)
    txn = Payment_Transaction(
        application_id = application_id,
        emi_number     = emi_numbers_str,
        amount_paid    = total_payable,
        payment_mode   = payment_mode,
        payment_option = "prepay",
    )
    db.add(txn)
    prepay_record = Prepayment_Request(
        application_id = application_id,
        emi_numbers    = emi_numbers_str,
        amount         = total_emi_amount,
        charge         = prepay_penalty,
        gst            = penalty_gst,
        status         = "PAID",
    )
    db.add(prepay_record)
    for e in emis:
        e.status = "PAID"

    db.commit()
    db.refresh(txn)

    return PrepayResponse(
        application_id      = application_id,
        total_emis_selected = len(emis),
        emis                = [
            PrepayEMIItem(
                emi_number          = e.emi_number,
                due_date            = e.due_date,
                emi_amount          = e.emi_amount,
                principal_component = e.principal_component,
                interest_component  = e.interest_component,
                gst_amount          = e.gst_amount,
            )
            for e in emis
        ],
        total_emi_amount    = total_emi_amount,
        total_principal     = total_principal,
        total_interest      = total_interest,
        total_gst           = total_gst,
        prepay_penalty      = prepay_penalty,
        penalty_gst         = penalty_gst,
        total_payable       = total_payable,
        payment_mode        = payment_mode,
        lender_details      = payment_details,
    )