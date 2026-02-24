from datetime import datetime, time
from sqlalchemy.orm import Session
from app.models.reminder_log import Reminder_Log
from app.core.email import send_mail
from app.core.notifier import push, sms

def send_reminders(db: Session):

    now = datetime.now()

    # Allow only between 9AM–6PM
    if not (time(9, 0) <= now.time() <= time(18, 0)):
        return

    reminders = db.query(Reminder_Log).filter(
        Reminder_Log.sent_at <= now
    ).all()

    for reminder in reminders:

        message = reminder.message

        if reminder.channel == "EMAIL":
            send_mail("user@email.com", "EMI Reminder", message)

        elif reminder.channel == "SMS":
            sms(message)

        elif reminder.channel == "PUSH":
            push(message)

    db.commit()
