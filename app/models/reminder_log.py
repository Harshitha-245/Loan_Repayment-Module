import uuid
from sqlalchemy import (Column,Integer,String,Float,DateTime,ForeignKey)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.db import Base


class Reminder_Log(Base):
    __tablename__ = "reminder_log"

    log_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    application_id = Column(UUID(as_uuid=True), ForeignKey("loans.loan_id"), nullable=False)
    emi_number = Column(Integer, nullable=False)
    reminder_day = Column(Integer, nullable=True)  # 7 / 3 / 1 / 0
    reminder_stage = Column(String(20), nullable=False)  
    channel = Column(String(10), nullable=True)  # EMAIL / SMS / PUSH
    penalty_amount = Column(Float, nullable=True)  
    overdue_day_count = Column(Integer, nullable=True)
    penalty_gst = Column(Float, nullable=True)  
    total_penalty_with_gst = Column(Float, nullable=True)
    penalty_paid_at = Column(DateTime, nullable=True)
    message = Column(String, nullable=False)
    sent_at = Column(DateTime, nullable=True)
    
    
    
   
    # reminder_day = Column(Integer, nullable=True)  
    # channel = Column(String(10), nullable=True)
