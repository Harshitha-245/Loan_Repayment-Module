from datetime import datetime
from sqlalchemy.orm import Session
from app.models.reminder_log import Reminder_Log
from app.models.loans import Loan

def execute_prepay(user_id: str, application_id: str, emi_ids: list[str], db: Session):
    """
    Execute prepayment for multiple EMIs.
    Returns total_amount for all selected EMIs.
    Updates reminder_log for these EMIs as PAID(PREPAY)
    """
    # 1️⃣ Fetch EMI amounts
    # Suppose EMI amount is stored in Loan table / other table
    loan = db.query(Loan).filter(Loan.loan_id == application_id).first()
    if not loan:
        raise ValueError("Loan not found")

    # For simplicity, assume emi_amount = loan.emi_amount
    # If emi_amount varies per EMI, you can fetch per EMI_id
    emi_amount = getattr(loan, "emi_amount", 0)
    total_amount = emi_amount * len(emi_ids)

    # 2️⃣ Update reminder_log for selected EMIs as PAID(PREPAY)
    for emi_id in emi_ids:
        db.query(Reminder_Log).filter(
            Reminder_Log.application_id == application_id,
            Reminder_Log.emi_number == int(emi_id)
        ).update({
            "reminder_stage": "PAID(PREPAY)",
            "reminder_day": 0,
            "penalty_amount": 0,
            "penalty_gst": 0,
            "total_penalty_with_gst": 0,
            "penalty_paid_at": datetime.now(),
            "overdue_day_count": 0,
            "message": f"EMI {emi_id} closed due to prepayment",
            "sent_at": datetime.now()
        }, synchronize_session=False)

    db.commit()
    return {"total_amount": total_amount}