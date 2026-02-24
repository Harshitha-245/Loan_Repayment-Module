from uuid import UUID
from .base_schema import BaseSchema


class PrepaymentSchema(BaseSchema):
    loan_id: UUID
    amount: float
    charge: float
    gst: float
    status: str
