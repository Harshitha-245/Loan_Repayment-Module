import uuid
from sqlalchemy import (Column,String,Numeric,ForeignKey)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.db import Base

class Foreclosure_Request(Base):
    __tablename__="foreclosures"
    id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    application_id=Column(UUID(as_uuid=True),ForeignKey("loans.loan_id"))
    outstanding=Column(Numeric(12,2))
    charge=Column(Numeric(12,2))
    gst=Column(Numeric(12,2))
    status=Column(String(20),default="PENDING")