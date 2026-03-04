from fastapi import APIRouter, Depends
from uuid import UUID
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.reminder_log import Reminder_Log

router = APIRouter(prefix="/reminders", tags=["EMI Reminders"])
@router.get("/overdue-summary/{loan_id}")
def overdue_summary(id: int, db: Session = Depends(get_db)):

    latest = db.query(Reminder_Log).filter(
        Reminder_Log.application_id == id,
        Reminder_Log.overdue_day_count > 0
    ).order_by(Reminder_Log.overdue_day_count.desc()).first()

    if not latest:
        return {"message": "No overdue found for this loan"}

    return {
        "loan_id": id,
        "emi_number_overdue": latest.emi_number,
        "overdue_days": latest.overdue_day_count,
        "base_penalty_paid": float(latest.penalty_amount or 0),
        "gst_18_percent_paid": float(latest.penalty_gst or 0),
        "total_penalty_paid": float(latest.total_penalty_with_gst or 0),
        "current_stage": latest.reminder_stage
    }
