from uuid import UUID
from datetime import datetime
from typing import Optional
from .base_schema import BaseSchema


class PaymentReminderSettingSchema(BaseSchema):
    user_id: UUID
    remind_before_days: int
    reminder_type: str
    active: Optional[bool] = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
