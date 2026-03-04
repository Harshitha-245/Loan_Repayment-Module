from datetime import datetime, date
from sqlalchemy.orm import Session
from sqlalchemy import asc
from app.models.emi_scheduled import EMISchedule
from app.models.reminder_log import Reminder_Log
from app.notifications.reminder_service import send_email_real,send_sms,send_push

def trigger_manual(application_id: int, db: Session):
    emi = db.query(EMISchedule).filter(
        EMISchedule.application_id == application_id,
        EMISchedule.due_date >= date.today()
    ).order_by(asc(EMISchedule.due_date)).first()

    if not emi:
        return {"message": "No upcoming EMI found"}

    loan = emi.loan
    if not loan:
        return {"message": "Loan not found"}

    user = loan.user
    if not user:
        return {"message": "User not found"}

    message = f"Please pay the EMI. Your due date is {emi.due_date}."

    print(f"SMS to {user.mobile_number} -> {message}")
    print(f"Push to User {user.user_id} -> {message}")
    send_email_real(user.email, message)

    reminder_log = Reminder_Log(
        user_id=user.user_id,
        application_id=application_id,
        emi_number=emi.emi_number,
        reminder_day=0,
        reminder_stage="MANUAL",
        channel="SMS,PUSH,EMAIL",
        message=message,
        sent_at=datetime.now()
    )

    db.add(reminder_log)
    db.commit()

    return {"message": "Manual reminder sent successfully"}

def process_automatic_reminders(db: Session):

    today = date.today()
    emis = db.query(EMISchedule).all()

    for emi in emis:

        due_date = emi.due_date
        days_left = (due_date - today).days

        loan = emi.loan
        if not loan:
            continue

        user = loan.user
        if not user:
            continue

        message = None
        stage = None
        channels = []
        reminder_day = None
        overdue_count = None
        if days_left in [7, 3, 1]:
            message = f"Please pay the EMI. Your due date is {due_date}."
            stage = "BEFORE_DUE"
            channels = ["SMS", "PUSH"]
            reminder_day = days_left
        elif days_left == 0:
            message = "EMI is due today. Please pay immediately."
            stage = "DUE_DAY"
            channels = ["SMS", "PUSH", "EMAIL"]
            reminder_day = 0
        elif days_left < 0:
            overdue_count = abs(days_left)
            message = f"Your EMI is overdue by {overdue_count} days. Please pay immediately."
            stage = "OVERDUE"
            channels = ["SMS", "PUSH", "EMAIL"]
            reminder_day = 0

        if not message:
            continue
        existing_log = db.query(Reminder_Log).filter(
            Reminder_Log.application_id == emi.application_id,
            Reminder_Log.emi_number == emi.emi_number,
            Reminder_Log.reminder_stage == stage,
            Reminder_Log.sent_at >= datetime.combine(today, datetime.min.time())
        ).first()

        if existing_log:
            continue  
        if "SMS" in channels:
            print(f"SMS to {user.phone} -> {message}")

        if "PUSH" in channels:
            print(f"Push to User {user.user_id} -> {message}")

        if "EMAIL" in channels:
            send_email_real(user.email, message)
        reminder_log = Reminder_Log(
            user_id=user.user_id,
            application_id=emi.application_id,
            emi_number=emi.emi_number,
            reminder_day=reminder_day,
            reminder_stage=stage,
            channel=",".join(channels),
            overdue_day_count=overdue_count,
            message=message,
            sent_at=datetime.now()
        )

        db.add(reminder_log)

    db.commit()

    return {"message": "Automatic reminders processed"}