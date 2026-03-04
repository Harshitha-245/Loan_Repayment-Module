from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session
from app.core.db import get_db
from app.models.users import User
from uuid import UUID


def get_current_user(
    user_id: str = Header(...),   # user_id will come from header
    db: Session = Depends(get_db)
):

    try:
        user_uuid = UUID(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid user_id format")

    user = db.query(User).filter(User.user_id == user_uuid).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
