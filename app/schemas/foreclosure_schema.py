from uuid import UUID

from .base_schema import BaseSchema
from pydantic import BaseModel


class ForeclosureSchema(BaseSchema):
    loan_id: UUID
    outstanding: float
    charge: float
    gst: float
    status: str

class ForeclosureRequest(BaseModel):
    user_id: str
    application_id: str
    payment_amount: float