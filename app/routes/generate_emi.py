from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.services.emi_schedule import generate_emi_schedule_service

router = APIRouter(
    prefix="/emis",
    tags=["EMI Schedule"]
)

@router.post("/generate/{loan_id}")
def generate_emi_schedule(loan_id: str, db: Session = Depends(get_db)):
    return generate_emi_schedule_service(loan_id, db)