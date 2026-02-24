from datetime import time, datetime

START_TIME = time(9, 0)
END_TIME = time(18, 0)

def allowed_time(now: datetime) -> bool:
    return START_TIME <= now.time() <= END_TIME

def push(message: str):
    print(f"[PUSH] {message}")

def sms(message: str):
    print(f"[SMS] {message}")
