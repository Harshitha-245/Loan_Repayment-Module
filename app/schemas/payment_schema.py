from pydantic import BaseModel, Field
from typing import List, Union, Literal, Annotated, Optional
from enum import Enum
from datetime import datetime


# ---------- ENUMS (Dropdown in Swagger) ----------

class PaymentMode(str, Enum):
    auto_debit = "auto_debit"
    manual = "manual"


class PaymentOption(str, Enum):
    upi = "upi"
    bank_transfer = "bank_transfer"
    credit_card = "credit_card"


# ---------- MANUAL PAYMENT SCHEMAS ----------

class UPIDetails(BaseModel):
    payment_option: Literal["upi"]
    upi_id: str = Field(..., min_length=3)


class BankTransferDetails(BaseModel):
    payment_option: Literal["bank_transfer"]
    account_number: str = Field(..., min_length=6)
    ifsc_code: str = Field(..., min_length=5)
    account_holder_name: str


class CreditCardDetails(BaseModel):
    payment_option: Literal["credit_card"]
    card_number: str = Field(..., min_length=12, max_length=19)
    expiry_month: str
    expiry_year: str
    cvv: str = Field(..., min_length=3, max_length=4)
    card_holder_name: str


ManualPaymentDetails = Annotated[
    Union[
        UPIDetails,
        BankTransferDetails,
        CreditCardDetails
    ],
    Field(discriminator="payment_option")
]


# ---------- ROUTE 1 REQUEST ----------

class PaymentModeRequest(BaseModel):
    payment_mode: PaymentMode
    payment_option: PaymentOption


# ---------- ROUTE 2 REQUEST ----------

class PaymentTransactionRequest(BaseModel):
    details: Optional[ManualPaymentDetails] = None
    
    
class PaymentHistoryItem(BaseModel):
    emi_number: Optional[List[int]]  # can be single or multiple EMIs (prepay/foreclosure)
    principal_component: float
    interest_component: float
    emi_amount: float
    overdue_count: Optional[int] = 0
    overdue_charges: Optional[float] = 0
    prepay_charge: Optional[float] = 0
    foreclosure_charge: Optional[float] = 0
    gst: float
    payment_date: datetime
    payment_mode: str
    transaction_id: str

class PaymentHistoryResponse(BaseModel):
    total_paid: float
    payment_history: List[PaymentHistoryItem]
