from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from app.models.payments import Payment_Transaction
from app.models.emi_scheduled import EMISchedule
from app.models.lender_table import Lender
from app.models.loans import LoanApplication
from app.models.foreclosure_table import Foreclosure_Request
from app.schemas.foreclosure_schema import (
    PaymentModeEnum,
    ForeclosureResponse,
    ForeclosureEMIItem,
    LenderUPIDetails,
    LenderBankTransferDetails,
    LenderCreditCardDetails,
)

FORECLOSURE_PENALTY_RATE = Decimal("0.04")   
PENALTY_GST_RATE         = Decimal("0.18")   


def _get_all_due_emis(db: Session, application_id: int) -> list[EMISchedule]:
    emis = (
        db.query(EMISchedule)
        .filter(
            and_(
                EMISchedule.application_id == application_id,
                EMISchedule.status == "DUE",
            )
        )
        .order_by(EMISchedule.emi_number)
        .all()
    )
    if not emis:
        raise HTTPException(status_code=400, detail="No pending EMIs. Loan may already be closed.")
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


def process_foreclosure(
    db:             Session,
    application_id: int,
    payment_mode:   PaymentModeEnum,
) -> ForeclosureResponse:

    emis            = _get_all_due_emis(db, application_id)
    payment_details = _get_lender_payment_details(db, application_id, payment_mode)

    total_emi_amount = sum(Decimal(str(e.emi_amount))          for e in emis)
    total_principal  = sum(Decimal(str(e.principal_component)) for e in emis)
    total_interest   = sum(Decimal(str(e.interest_component))  for e in emis)
    total_gst        = sum(Decimal(str(e.gst_amount))          for e in emis)

    foreclosure_penalty = (total_principal * FORECLOSURE_PENALTY_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    penalty_gst         = (foreclosure_penalty * PENALTY_GST_RATE).quantize(Decimal("0.01"),     rounding=ROUND_HALF_UP)
    total_payable       = (total_emi_amount + foreclosure_penalty + penalty_gst).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    emi_numbers_list = [e.emi_number for e in emis]
    emi_numbers_str  = ",".join(str(n) for n in emi_numbers_list)

    # Save to payments table
    txn = Payment_Transaction(
        application_id = application_id,
        emi_number     = emi_numbers_str,
        amount_paid    = total_payable,
        payment_mode   = payment_mode,
        payment_option = "foreclosure",
    )
    db.add(txn)

    # Save to foreclosures table
    foreclosure_record = Foreclosure_Request(
        application_id = application_id,
        outstanding    = total_emi_amount,
        charge         = foreclosure_penalty,
        gst            = penalty_gst,
        status         = "PAID",
    )
    db.add(foreclosure_record)

    # Mark all EMIs as PAID
    for e in emis:
        e.status = "PAID"

    db.commit()
    db.refresh(txn)

    return ForeclosureResponse(
        transaction_id      = txn.payment_id,
        application_id      = application_id,
        emi_numbers         = emi_numbers_list,
        total_emis_cleared  = len(emis),
        emis                = [
            ForeclosureEMIItem(
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
        foreclosure_penalty = foreclosure_penalty,
        penalty_gst         = penalty_gst,
        total_payable       = total_payable,
        payment_mode        = payment_mode,
        payment_option      = "foreclosure",
        date                = txn.created_at,
        lender_details      = payment_details,
    )