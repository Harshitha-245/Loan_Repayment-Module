import uuid
from sqlalchemy import (Column,DateTime,Text,ForeignKey)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from app.core.db import Base

class NoDueCertificate(Base):
    __tablename__="ndc"
    id=Column(UUID(as_uuid=True),primary_key=True,default=uuid.uuid4)
    application_id=Column(UUID(as_uuid=True),ForeignKey("loans.loan_id"))
    pdf_url=Column(Text)
    issued_on=Column(DateTime,server_default=func.now())