from pydantic import BaseModel
from enum import Enum
from typing import Optional, List
from datetime import date
from decimal import Decimal


class PaymentModeEnum(str, Enum):
    upi           = "upi"
    bank_transfer = "bank_transfer"
    credit_card   = "credit_card"


class LenderUPIDetails(BaseModel):
    lender_upi:                 str
    lender_account_holder_name: str


class LenderBankTransferDetails(BaseModel):
    lender_account_holder_name: str
    lender_account_number:      str
    ifsc:                       str
    lender_bank_name:           str


class LenderCreditCardDetails(BaseModel):
    lender_account_holder_name: str
    lender_card_number:         str
    lender_card_type:           str
    lender_expiry:              str


class PrepayEMIItem(BaseModel):
    emi_number:          int
    due_date:            date
    emi_amount:          Decimal
    principal_component: Decimal
    interest_component:  Decimal
    gst_amount:          Decimal


class PrepayResponse(BaseModel):
    application_id:      int
    total_emis_selected: int
    emis:                List[PrepayEMIItem]
    total_emi_amount:    Decimal
    total_principal:     Decimal
    total_interest:      Decimal
    total_gst:           Decimal
    prepay_penalty:      Decimal   
    penalty_gst:         Decimal   
    total_payable:       Decimal   
    payment_mode:        str
    lender_details:      LenderUPIDetails | LenderBankTransferDetails | LenderCreditCardDetails

    class Config:
        from_attributes = True