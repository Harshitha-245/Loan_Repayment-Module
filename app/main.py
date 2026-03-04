from fastapi import FastAPI 
from app.core.db import engine,Base
from app.models import *
from app.routes.generate_emi import router as generate_emi_router
from app.routes.emi_pdf import router as emi_pdf_router
from app.routes.emi_reminder import router as emi_reminder_router
from app.routes.overdue import router as emi_overdue_router
from app.routes.auto_debit import router as auto_debit_router
from app.routes.manual import router as manual_router
from app.routes.prepay_route import router as prepay_router
from app.routes.foreclosure import router as foreclosure_router
from app.routes.payment_history import router as payment_history_router
from app.routes.payment_receipt import router as payment_receipt_router
from app.routes.loan_closure import router as loan_closure_router
from app.routes.ndc import router as ndc_router
from fastapi import FastAPI
from app.core.scheduler import start_scheduler



app=FastAPI(title="EMI Repayment Module")

Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def startup():
    start_scheduler()

app.include_router(generate_emi_router)
app.include_router(emi_pdf_router)
app.include_router(emi_reminder_router)
app.include_router(emi_overdue_router)
app.include_router(auto_debit_router)
app.include_router(manual_router)
app.include_router(prepay_router)
app.include_router(foreclosure_router)
app.include_router(payment_history_router)
app.include_router(payment_receipt_router)
app.include_router(loan_closure_router)
app.include_router(ndc_router)



@app.get("/")
def root():
    return {"status":"EMI module running"}

