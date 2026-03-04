import uuid
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.db import Base
import enum


class Payment_Transaction(Base):
    __tablename__ = "payments"

    payment_id = Column(Integer, primary_key=True)
    transaction_id = Column(String(12), unique=True, nullable=True)
    application_id = Column(Integer, ForeignKey("loan_application.id"))
    emi_number     = Column(String, nullable=True)
    amount_paid = Column(Numeric(12, 2))
    payment_mode = Column(String(30))           
    payment_option = Column(String(20))  
    created_at = Column(DateTime, server_default=func.now())
    
class PaymentModeEnum(str, enum.Enum):
    upi = "upi"
    bank_transfer = "bank_transfer"
    credit_card = "credit_card"
