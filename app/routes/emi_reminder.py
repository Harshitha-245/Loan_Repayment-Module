# from fastapi import APIRouter, Depends
# from sqlalchemy.orm import Session
# from datetime import datetime, timedelta
# from dateutil.relativedelta import relativedelta
# from app.core.db import get_db
# from app.models.reminder_log import Reminder_Log
# from app.models.loans import Loan

# router = APIRouter(prefix="/reminders", tags=["EMI Reminders"])


# @router.post("/emi")
# def generate_emi_reminders(user_id: str, application_id: str, db: Session = Depends(get_db)):

#     loan = db.query(Loan).filter(Loan.loan_id == application_id).first()
#     if not loan:
#         return {"message": "Loan not found"}

#     emi_start_date = datetime(2026, 4, 26)
#     tenure = loan.tenure_months

#     reminder_config = {
#         7: ["EMAIL", "PUSH"],
#         3: ["PUSH", "SMS"],
#         1: ["EMAIL", "PUSH"],
#         0: ["EMAIL", "SMS", "PUSH"]
#     }

#     for emi_num in range(1, tenure + 1):

#         due_date = emi_start_date + relativedelta(months=emi_num - 1)

#         # =====================================================
#         # EMI 1,2,4,6 → NORMAL PAID ON DUE DATE
#         # =====================================================
#         if emi_num in [1, 2, 4, 6]:

#             # 7,3,1 → DUE
#             for day in [7, 3, 1]:
#                 reminder_date = due_date - timedelta(days=day)
#                 for ch in reminder_config[day]:
#                     db.add(Reminder_Log(
#                         user_id=user_id,
#                         application_id=application_id,
#                         emi_number=emi_num,
#                         reminder_day=day,
#                         reminder_stage="DUE",
#                         channel=ch,
#                         penalty_amount=0,
#                         penalty_gst=0,
#                         total_penalty_with_gst=0,
#                         penalty_paid_at=None,
#                         overdue_day_count=0,
#                         message=f"EMI {emi_num} due in {day} day(s)",
#                         sent_at=reminder_date
#                     ))

#             # 0 day → PAID (NO penalty_paid_at)
#             for ch in reminder_config[0]:
#                 db.add(Reminder_Log(
#                     user_id=user_id,
#                     application_id=application_id,
#                     emi_number=emi_num,
#                     reminder_day=0,
#                     reminder_stage="PAID",
#                     channel=ch,
#                     penalty_amount=0,
#                     penalty_gst=0,
#                     total_penalty_with_gst=0,
#                     penalty_paid_at=None,  # ✅ IMPORTANT FIX
#                     overdue_day_count=0,
#                     message=f"EMI {emi_num} paid on due date",
#                     sent_at=due_date
#                 ))

#         # =====================================================
#         # EMI 3 → OVERDUE CASE
#         # =====================================================
#         elif emi_num == 3:

#             # 7,3,1 → DUE
#             for day in [7, 3, 1]:
#                 reminder_date = due_date - timedelta(days=day)
#                 for ch in reminder_config[day]:
#                     db.add(Reminder_Log(
#                         user_id=user_id,
#                         application_id=application_id,
#                         emi_number=emi_num,
#                         reminder_day=day,
#                         reminder_stage="DUE",
#                         channel=ch,
#                         penalty_amount=0,
#                         penalty_gst=0,
#                         total_penalty_with_gst=0,
#                         penalty_paid_at=None,
#                         overdue_day_count=0,
#                         message=f"EMI {emi_num} due in {day} day(s)",
#                         sent_at=reminder_date
#                     ))

#             # Due day → still DUE
#             for ch in reminder_config[0]:
#                 db.add(Reminder_Log(
#                     user_id=user_id,
#                     application_id=application_id,
#                     emi_number=emi_num,
#                     reminder_day=0,
#                     reminder_stage="DUE",
#                     channel=ch,
#                     penalty_amount=0,
#                     penalty_gst=0,
#                     total_penalty_with_gst=0,
#                     penalty_paid_at=None,
#                     overdue_day_count=0,
#                     message=f"EMI {emi_num} due today",
#                     sent_at=due_date
#                 ))

#             # Overdue Day 1 & 2
#             for overdue_day in [1, 2]:

#                 reminder_date = due_date + timedelta(days=overdue_day)
#                 penalty = 50 * overdue_day
#                 gst = round(penalty * 0.18, 2)
#                 total_with_gst = penalty + gst

#                 stage = "OVERDUE" if overdue_day == 1 else "PAID"
#                 paid_at = reminder_date if overdue_day == 2 else None

#                 for ch in ["EMAIL", "SMS", "PUSH"]:
#                     db.add(Reminder_Log(
#                         user_id=user_id,
#                         application_id=application_id,
#                         emi_number=emi_num,
#                         reminder_day=overdue_day,
#                         reminder_stage=stage,
#                         channel=ch,
#                         penalty_amount=penalty,
#                         penalty_gst=gst,
#                         total_penalty_with_gst=total_with_gst,
#                         penalty_paid_at=paid_at,  # ✅ Only EMI 3 overdue day 2
#                         overdue_day_count=overdue_day,
#                         message=f"EMI {emi_num} overdue {overdue_day} day(s)",
#                         sent_at=reminder_date
#                     ))

#         # =====================================================
#         # EMI 5 → PREPAY
#         # =====================================================
#         elif emi_num == 5:
#             db.add(Reminder_Log(
#                 user_id=user_id,
#                 application_id=application_id,
#                 emi_number=emi_num,
#                 reminder_day=0,
#                 reminder_stage="PAID(PREPAY)",
#                 channel="NONE",
#                 penalty_amount=0,
#                 penalty_gst=0,
#                 total_penalty_with_gst=0,
#                 penalty_paid_at=due_date,  # ✅ Only here
#                 overdue_day_count=0,
#                 message="EMI 5 prepaid",
#                 sent_at=due_date
#             ))

#         # =====================================================
#         # EMI 7,8,9 → FORECLOSURE
#         # =====================================================
#         elif emi_num in [7, 8, 9]:
#             db.add(Reminder_Log(
#                 user_id=user_id,
#                 application_id=application_id,
#                 emi_number=emi_num,
#                 reminder_day=0,
#                 reminder_stage="PAID(FORECLOSURE)",
#                 channel="NONE",
#                 penalty_amount=0,
#                 penalty_gst=0,
#                 total_penalty_with_gst=0,
#                 penalty_paid_at=due_date,  # ✅ Only here
#                 overdue_day_count=0,
#                 message=f"EMI {emi_num} closed via foreclosure",
#                 sent_at=due_date
#             ))

#     db.commit()

#     return {
#         "message": "EMI reminders generated successfully",
#     }












from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.core.db import get_db
from app.models.reminder_log import Reminder_Log
from app.models.loans import Loan

router = APIRouter(prefix="/reminders", tags=["EMI Reminders"])

@router.post("/emi")
def generate_emi_reminders(user_id: str, application_id: str, db: Session = Depends(get_db)):

    loan = db.query(Loan).filter(Loan.loan_id == application_id).first()
    if not loan:
        return {"message": "Loan not found"}

    emi_start_date = datetime(2026, 4, 26)
    tenure = loan.tenure_months

    reminder_config = {
        7: ["EMAIL", "PUSH"],
        3: ["PUSH", "SMS"],
        1: ["EMAIL", "PUSH"],
        0: ["EMAIL", "SMS", "PUSH"]
    }

    for emi_num in range(1, tenure + 1):
        due_date = emi_start_date + relativedelta(months=emi_num - 1)

        # =====================================================
        # NORMAL EMIs → 1,2,4,6
        # =====================================================
        if emi_num in [1, 2, 4, 6]:
            for day in [7, 3, 1]:
                reminder_date = due_date - timedelta(days=day)
                for ch in reminder_config[day]:
                    db.add(Reminder_Log(
                        user_id=user_id,
                        application_id=application_id,
                        emi_number=emi_num,
                        reminder_day=day,
                        reminder_stage="DUE",
                        channel=ch,
                        penalty_amount=0,
                        penalty_gst=0,
                        total_penalty_with_gst=0,
                        penalty_paid_at=None,
                        overdue_day_count=0,
                        message=f"EMI {emi_num} due in {day} day(s)",
                        sent_at=reminder_date
                    ))
            for ch in reminder_config[0]:
                db.add(Reminder_Log(
                    user_id=user_id,
                    application_id=application_id,
                    emi_number=emi_num,
                    reminder_day=0,
                    reminder_stage="PAID",
                    channel=ch,
                    penalty_amount=0,
                    penalty_gst=0,
                    total_penalty_with_gst=0,
                    penalty_paid_at=None,
                    overdue_day_count=0,
                    message=f"EMI {emi_num} paid on due date",
                    sent_at=due_date
                ))

        # =====================================================
        # OVERDUE EMI → 3
        # =====================================================
        elif emi_num == 3:
            for day in [7, 3, 1]:
                reminder_date = due_date - timedelta(days=day)
                for ch in reminder_config[day]:
                    db.add(Reminder_Log(
                        user_id=user_id,
                        application_id=application_id,
                        emi_number=emi_num,
                        reminder_day=day,
                        reminder_stage="DUE",
                        channel=ch,
                        penalty_amount=0,
                        penalty_gst=0,
                        total_penalty_with_gst=0,
                        penalty_paid_at=None,
                        overdue_day_count=0,
                        message=f"EMI {emi_num} due in {day} day(s)",
                        sent_at=reminder_date
                    ))

            for ch in reminder_config[0]:
                db.add(Reminder_Log(
                    user_id=user_id,
                    application_id=application_id,
                    emi_number=emi_num,
                    reminder_day=0,
                    reminder_stage="DUE",
                    channel=ch,
                    penalty_amount=0,
                    penalty_gst=0,
                    total_penalty_with_gst=0,
                    penalty_paid_at=None,
                    overdue_day_count=0,
                    message=f"EMI {emi_num} due today",
                    sent_at=due_date
                ))

            for overdue_day in [1, 2]:
                reminder_date = due_date + timedelta(days=overdue_day)
                penalty = 50 * overdue_day
                gst = round(penalty * 0.18, 2)
                total_with_gst = penalty + gst
                stage = "OVERDUE" if overdue_day == 1 else "PAID"
                paid_at = reminder_date if overdue_day == 2 else None

                for ch in ["EMAIL", "SMS", "PUSH"]:
                    db.add(Reminder_Log(
                        user_id=user_id,
                        application_id=application_id,
                        emi_number=emi_num,
                        reminder_day=overdue_day,
                        reminder_stage=stage,
                        channel=ch,
                        penalty_amount=penalty,
                        penalty_gst=gst,
                        total_penalty_with_gst=total_with_gst,
                        penalty_paid_at=paid_at,
                        overdue_day_count=overdue_day,
                        message=f"EMI {emi_num} overdue {overdue_day} day(s)",
                        sent_at=reminder_date
                    ))

        # =====================================================
        # PREPAY EMI → 5
        # =====================================================
        elif emi_num == 5:
            db.add(Reminder_Log(
                user_id=user_id,
                application_id=application_id,
                emi_number=emi_num,
                reminder_day=0,
                reminder_stage="PAID(PREPAY)",
                channel="NONE",
                penalty_amount=0,
                penalty_gst=0,
                total_penalty_with_gst=0,
                penalty_paid_at=None,
                overdue_day_count=0,
                message="EMI 5 prepaid",
                sent_at=None  # ✅ NO date
            ))

        # =====================================================
        # FORECLOSURE EMIs → 7,8,9
        # =====================================================
        elif emi_num in [7, 8, 9]:
            db.add(Reminder_Log(
                user_id=user_id,
                application_id=application_id,
                emi_number=emi_num,
                reminder_day=0,
                reminder_stage="PAID(FORECLOSURE)",
                channel="NONE",
                penalty_amount=0,
                penalty_gst=0,
                total_penalty_with_gst=0,
                penalty_paid_at=None,
                overdue_day_count=0,
                message=f"EMI {emi_num} closed via foreclosure",
                sent_at=None  # ✅ NO date
            ))

    db.commit()

    return {"message": "EMI reminders generated successfully"}