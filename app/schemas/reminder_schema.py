from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ReminderLogCreate(BaseModel):
    user_id: int
    emi_id: int
    channel: str
    status: str


class ReminderLogResponse(BaseModel):
    log_id: int
    user_id: int
    emi_id: int
    channel: str
    status: str
    sent_at: datetime

    class Config:
        orm_mode = True