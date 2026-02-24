import uuid
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.db import Base
import enum


class Payment_Transaction(Base):
    __tablename__ = "payments"

    payment_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True), ForeignKey("loans.loan_id"))
    # emi_id = Column(UUID(as_uuid=True))  # optional
    emi_number = Column(Integer, nullable=True)# optional
    # emi_amount = Column(Numeric(12, 2), nullable=True)  # optional, can be derived from EMI schedule
    amount_paid = Column(Numeric(12, 2))
    payment_mode = Column(String(30))            # bank_transfer / upi / credit_card
    payment_option = Column(String(20))  # manual / auto_debit
    created_at = Column(DateTime, server_default=func.now())
    
class PaymentModeEnum(str, enum.Enum):
    upi = "upi"
    bank_transfer = "bank_transfer"
    credit_card = "credit_card"
