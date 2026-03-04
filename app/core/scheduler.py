from apscheduler.schedulers.background import BackgroundScheduler
from app.core.db import SessionLocal
from app.services.reminder import process_automatic_reminders

scheduler = BackgroundScheduler()

def start_scheduler():

    def job():
        db = SessionLocal()
        process_automatic_reminders(db)
        db.close()

    scheduler.add_job(job, "cron", hour=9, minute=0)
    scheduler.start()