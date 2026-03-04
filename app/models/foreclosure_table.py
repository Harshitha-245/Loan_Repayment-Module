from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.core.db import Base

class Foreclosure_Request(Base):
    __tablename__ = "foreclosures"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("loan_application.id"))
    outstanding    = Column(Numeric(12, 2))
    charge         = Column(Numeric(12, 2))
    gst            = Column(Numeric(12, 2))
    status         = Column(String(20), default="PENDING")
    created_at     = Column(DateTime, server_default=func.now())