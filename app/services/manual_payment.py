from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date

from app.models.emi_scheduled import EMISchedule
from app.models.lender_table import Lender
from app.models.loans import LoanApplication
from app.models.payments import Payment_Transaction
from app.schemas.manual_schema import (
    PaymentModeEnum,
    PaymentOptionEnum,
    PaymentResponse,
    DuesResponse,
    DueEMIItem,
    OverdueResponse,
    OverdueEMIItem,
    NoOverdueResponse,
    LenderUPIDetails,
    LenderBankTransferDetails,
    LenderCreditCardDetails,
)

OVERDUE_PENALTY_RATE = Decimal("0.02")
PENALTY_GST_RATE     = Decimal("0.18")


def _get_next_due_emi(db: Session, application_id: int) -> EMISchedule:
    emi = (
        db.query(EMISchedule)
        .filter(
            and_(
                EMISchedule.application_id == application_id,
                EMISchedule.status == "DUE",
            )
        )
        .order_by(EMISchedule.emi_number)
        .first()
    )
    if not emi:
        raise HTTPException(
            status_code=404,
            detail=f"No pending EMIs found for application_id {application_id}."
        )
    return emi


def _get_all_due_emis(db: Session, application_id: int) -> list[EMISchedule]:
    return (
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


def _get_overdue_emis(db: Session, application_id: int) -> list[EMISchedule]:
    today = date.today()
    return (
        db.query(EMISchedule)
        .filter(
            and_(
                EMISchedule.application_id == application_id,
                EMISchedule.status == "DUE",
                EMISchedule.due_date < today,
            )
        )
        .order_by(EMISchedule.emi_number)
        .all()
    )


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


def _save_transaction(
    db:             Session,
    application_id: int,
    emi_number:     str,
    amount_paid:    Decimal,
    payment_mode:   str,
    payment_option: str,
) -> Payment_Transaction:
    txn = Payment_Transaction(
        application_id = application_id,
        emi_number     = emi_number,
        amount_paid    = amount_paid,
        payment_mode   = payment_mode,
        payment_option = payment_option,
    )
    db.add(txn)
    return txn


def process_manual_payment(
    db:             Session,
    application_id: int,
    payment_mode:   PaymentModeEnum,
    payment_option: PaymentOptionEnum,
):
    today = date.today()

    if payment_option == PaymentOptionEnum.overdue:
        overdue_emis = _get_overdue_emis(db, application_id)

        if not overdue_emis:
            return NoOverdueResponse(
                application_id = application_id,
                message        = "No overdue EMIs! All payments are up to date.",
                overdue_count  = 0,
                penalty        = Decimal("0.00"),
                penalty_gst    = Decimal("0.00"),
                total_payable  = Decimal("0.00"),
            )

        total_emi_amount = sum(Decimal(str(e.emi_amount))         for e in overdue_emis)
        total_interest   = sum(Decimal(str(e.interest_component)) for e in overdue_emis)
        penalty          = (total_emi_amount * OVERDUE_PENALTY_RATE).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        penalty_gst      = (penalty * PENALTY_GST_RATE).quantize(Decimal("0.01"),             rounding=ROUND_HALF_UP)
        total_payable    = (total_emi_amount + penalty + penalty_gst).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return OverdueResponse(
            application_id   = application_id,
            overdue_count    = len(overdue_emis),
            total_emi_amount = total_emi_amount,
            total_interest   = total_interest,
            penalty          = penalty,
            penalty_gst      = penalty_gst,
            total_payable    = total_payable,
            overdue_emis     = [
                OverdueEMIItem(
                    emi_number   = e.emi_number,
                    emi_amount   = e.emi_amount,
                    due_date     = e.due_date,
                    overdue_days = (today - e.due_date).days,
                    status       = e.status,
                )
                for e in overdue_emis
            ],
        )

    if payment_option == PaymentOptionEnum.dues:
        due_emis = _get_all_due_emis(db, application_id)
        if not due_emis:
            return {"message": "No dues! All EMIs are cleared.", "application_id": application_id}

        return DuesResponse(
            application_id   = application_id,
            total_due_emis   = len(due_emis),
            total_due_amount = sum(e.emi_amount for e in due_emis),
            due_emis         = [
                DueEMIItem(
                    emi_number = e.emi_number,
                    emi_amount = e.emi_amount,
                    due_date   = e.due_date,
                    status     = e.status,
                )
                for e in due_emis
            ],
        )

    payment_details = _get_lender_payment_details(db, application_id, payment_mode)

    if payment_option == PaymentOptionEnum.regular_emi:
        emi = _get_next_due_emi(db, application_id)
        txn = _save_transaction(
            db             = db,
            application_id = application_id,
            emi_number     = str(emi.emi_number),
            amount_paid    = Decimal(str(emi.emi_amount)),
            payment_mode   = payment_mode,
            payment_option = payment_option,
        )
        emi.status = "PAID"
        db.commit()
        db.refresh(txn)
        return PaymentResponse(
            transaction_id  = txn.payment_id,
            application_id  = application_id,
            emi_number      = emi.emi_number,
            emi_amount      = emi.emi_amount,
            amount_paid     = txn.amount_paid,
            payment_mode    = payment_mode,
            payment_option  = payment_option,
            date            = txn.created_at,
            payment_details = payment_details,
        )

    elif payment_option == PaymentOptionEnum.prepay:
        emi = _get_next_due_emi(db, application_id)
        txn = _save_transaction(
            db             = db,
            application_id = application_id,
            emi_number     = str(emi.emi_number),
            amount_paid    = Decimal(str(emi.emi_amount)),
            payment_mode   = payment_mode,
            payment_option = payment_option,
        )
        emi.status = "PARTIAL"
        db.commit()
        db.refresh(txn)
        return PaymentResponse(
            transaction_id  = txn.payment_id,
            application_id  = application_id,
            emi_number      = emi.emi_number,
            emi_amount      = emi.emi_amount,
            amount_paid     = txn.amount_paid,
            payment_mode    = payment_mode,
            payment_option  = payment_option,
            date            = txn.created_at,
            payment_details = payment_details,
        )

    elif payment_option == PaymentOptionEnum.foreclosure:
        pending = _get_all_due_emis(db, application_id)
        if not pending:
            raise HTTPException(status_code=400, detail="No pending EMIs. Loan may already be closed.")

        total            = sum(Decimal(str(e.emi_amount)) for e in pending)
        emi_numbers_str  = ",".join(str(e.emi_number) for e in pending)

        txn = _save_transaction(
            db             = db,
            application_id = application_id,
            emi_number     = emi_numbers_str,
            amount_paid    = total,
            payment_mode   = payment_mode,
            payment_option = payment_option,
        )
        for e in pending:
            e.status = "PAID"
        db.commit()
        db.refresh(txn)

        return PaymentResponse(
            transaction_id  = txn.payment_id,
            application_id  = application_id,
            emi_number      = None,
            emi_amount      = total,
            amount_paid     = txn.amount_paid,
            payment_mode    = payment_mode,
            payment_option  = payment_option,
            date            = txn.created_at,
            payment_details = payment_details,
        )