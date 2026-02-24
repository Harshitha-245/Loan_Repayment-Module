from sqlalchemy import Column, Integer, Date, Numeric, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
import uuid
from sqlalchemy.orm import relationship
from app.core.db import Base

class EMI_Schedule(Base):
    __tablename__ = "emi_schedules"
    emi_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id = Column(UUID(as_uuid=True),ForeignKey("loans.loan_id"),nullable=False)
    emi_number = Column(Integer, nullable=False)
    due_date = Column(Date, nullable=False)
    opening_principal = Column(Numeric(12, 2), nullable=False)
    principal_component = Column(Numeric(12, 2), nullable=False)
    interest_component = Column(Numeric(12, 2), nullable=False)
    gst_amount = Column(Numeric(12, 2), nullable=False)
    emi_amount = Column(Numeric(12, 2), nullable=False)
    closing_principal = Column(Numeric(12, 2), nullable=False)
    status = Column(String(20), default="DUE")

    loan = relationship("Loan", back_populates="emi_schedules")
