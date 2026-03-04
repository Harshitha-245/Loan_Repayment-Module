from datetime import datetime
from sqlalchemy import Column, String, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.core.db import Base


class Bank_Details(Base):
    __tablename__ = "User_Bank_Details"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)
    account_number = Column(String(20), nullable=False)
    account_holder_name = Column(String(150), nullable=False)
    bank_name = Column(String(100), nullable=False)
    ifsc = Column(String(11), nullable=False)
    upi_id = Column(String(100), nullable=True)
    card_type = Column(String(20), nullable=True)        
    card_number = Column(String(20), nullable=True)
    expiry = Column(String(7), nullable=True)            
    cvv = Column(String(4), nullable=True)

    # Relationship
    user = relationship("User", back_populates="bank_details")