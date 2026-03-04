from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.reminder import trigger_manual

router = APIRouter(prefix="/reminders", tags=["EMI Reminders"])

@router.post("/reminders/manual")
def manual(application_id: int, db: Session = Depends(get_db)):
    return trigger_manual(application_id, db)