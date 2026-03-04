from sqlalchemy import Column, Integer, String, ForeignKey, DateTime,Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.db import Base
 
class Lender(Base):
    __tablename__ = "lenders"
 
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    company_name = Column(String, nullable=False)
    gst_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    lender_account_number = Column(String(20), nullable=False)
    lender_account_holder_name = Column(String(150), nullable=False)
    lender_bank_name = Column(String(100), nullable=False)
    ifsc = Column(String(11), nullable=False)
    lender_upi = Column(String(100), nullable=True)
    lender_card_type = Column(String(20), nullable=True)        
    lender_card_number = Column(String(20), nullable=True)
    lender_expiry = Column(String(7), nullable=True)            
    lender_cvv = Column(String(4), nullable=True)
    
   
    user = relationship("User", back_populates="lenders")