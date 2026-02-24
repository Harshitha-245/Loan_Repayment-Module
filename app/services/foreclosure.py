import os
from app.models.users import Foreclosure_Request

GST = float(os.getenv("GST_RATE")) / 100

def foreclosure(db, loan):
    charge = loan.outstanding_amount * 0.04
    gst = charge * GST

    db.add(Foreclosure_Request(
        loan_id=loan.loan_id,
        outstanding=loan.outstanding_amount,
        charge=charge,
        gst=gst
    ))

    loan.outstanding_amount = 0
    loan.status = "CLOSED"
    db.commit()
