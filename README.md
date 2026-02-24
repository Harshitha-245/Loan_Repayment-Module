# Loan Management & Repayment System

This project is a backend-based Loan Management system built using FastAPI.  
It handles the complete loan lifecycle — starting from user creation all the way to loan closure and certificate generation.

---

## Project Overview

The system manages:

- User creation
- Loan calculation
- Loan approval & activation
- EMI schedule generation
- Reminder notifications
- Payment tracking
- Prepayment & foreclosure handling
- Complete payment history with receipts
- Loan closure & certificate generation

---

## Application Flow

### 1. User Creation
A user is first created in the system.

### 2. Loan Calculation
The user applies for a loan by entering:
- Loan amount
- Tenure

The system calculates the EMI.

At this stage:
Loan Status → **CALCULATED**

---

### 3. Loan Approval & Activation

The loan does not become active immediately.

After:
- 1 month
- + 2 additional days

The loan status becomes:

Loan Status → **ACTIVE**

---

## EMI Schedule Logic

Once the loan becomes ACTIVE (Disbursed):

- EMI schedule is generated.
- The first EMI is generated within a **30 to 45 days span** from activation.
- All EMIs are scheduled accordingly.

---

## Reminder System

For every EMI, reminders are sent at different stages.

### Before Due Date:
- 7 days before
- 3 days before
- 1 day before

Channels used:
- Email
- SMS
- Push

---

### On Due Date:
- Email
- SMS
- Push Notification

---

### Overdue:
- Email
- SMS
- Push Notification

If an EMI becomes overdue:
→ A penalty is collected.

---

## Payment Types

The system supports:

- Manual payments
- Auto-debit payments
- Prepayment
- Foreclosure

All payments are recorded and tracked.

---

## Prepayment

If the user chooses to prepay:

→ A **2% charge** is collected on the outstanding amount.

---

## Foreclosure

If the user wants to close the loan completely:

→ A **4% foreclosure charge** is collected.

After successful foreclosure:

- Loan status becomes **CLOSED**
- Loan Closure and Credit Bureau Notice Update is generated
- NDC (No Dues Certificate) is issued

---

## Certificates & Receipts

After loan closure:
- Loan Closure and  Credit Bureau Notice Update is generated.
- NDC Certificate is provided.

Users can also:
- View complete payment history
- Download payment receipts

---

## Tech Stack

- Python
- FastAPI
- PostgreSQL
- SQLAlchemy

---

## How to Run the Project

```bash
pip install -r requirements.txt
uvicorn main:app --reload

## Flow: 

User Created  
↓  
POST /users  

Creates a new user in the system.

---

Loan Calculated  
(Status: CALCULATED)  
↓  
POST /loans/calculate  

Calculates EMI based on loan amount, interest , gst and tenure.  
Loan is saved with status → CALCULATED

---

Loan Approved (After 1 Month)  
↓  
POST /loans/{loan_id}/approve  

Approves the loan after the defined approval period.  
Status still controlled until activation.

---

Loan ACTIVE (Loan Approved + 2 Days)  
↓  
PATCH /loans/{loan_id}/activate  

Loan becomes ACTIVE after approval date + 2 days.

---

EMI Schedule Generated (30–45 Days Span)  
↓  
POST /loans/{loan_id}/emi-schedule  

Generates EMI schedule.  
EMI's are created within 30–45 days from activation.

---

Reminders Sent  
↓  
POST /reminders/trigger?loan_id={loan_id}  

Sends reminders for:
- 7 days before (Email, SMS)
- 3 days before (Email, SMS)
- 1 day before (Email, SMS)
- Due day (Email, SMS, Push)
- Overdue (Email, SMS, Push + Penalty)

---

Payments  
(Manual / Auto_debit / Prepay / Foreclosure)  
↓

Manual EMI Payment  
POST /payments/emi  

Auto Debit  
POST /payments/auto-debit  

Prepayment (2% charge)  
POST /payments/prepay  

Foreclosure (4% charge)  
POST /payments/foreclosure  

If foreclosure successful → Loan Status becomes CLOSED

---

Payment History & Receipts  
↓

GET /payments/{loan_id}  

Returns complete payment history.

GET /payments/{loan_id}/receipt/{emi_id}  

Downloads EMI receipt.

---

Loan Closed  
(Status: CLOSED)

Automatically updated after full payment or foreclosure.

---

Loan Closure Credit Bureau Update Notice
↓

GET /loans/{loan_id}/closure-certificate  

Generates Loan Closure and Credit Bureau Update Notice

---

NDC Certificate  
↓

GET /loans/{loan_id}/ndc  

Generates No Due Certificate after loan closure.

## 3rd party integrations

---


## Diagramatic Flow

Users
   │
   └───< Loans (ACTIVE)
            │
            ├───< EMI_Schedule (PENDING)
            │         │
            │         └── Due Date Reached
            │                │
            │                └── Reminder Sent (SMS / Email / Push)
            │
            └───< Payments
                      │
                      ├── EMI Payment (Manual / Auto-Debit)
                      │        │
                      │        └── EMI Status → PAID
                      │
                      ├── Prepayment
                      │
                      └── Foreclosure
                               │
                               └── Outstanding Recalculated
                                        │
                                        └── Outstanding = 0 ?
                                                │
                                                ├── NO → Continue EMIs
                                                │
                                                └── YES
                                                       │
                                                       └── Loan Status → CLOSED
                                                                │
                                                                └── Generate NDC Certificate
                                                                        │
                                                                        └── Store PDF (S3)

## 🔗 Third-Party Integrations

To make the system production-ready and scalable, the following third-party integrations are planned/designed as part of the architecture.

Even though some integrations may currently run in a simulated mode, the system is structured to plug into real external services without changing core business logic.

---

### Payment Gateway

Used For:
- Online EMI Payments
- Auto-Debit (eMandate)
- Manual Payments (UPI / Card / NetBanking)

Integrated With:
→ Razorpay Payment Gateway

Flow Mapping:
Payments (Manual / Auto-Debit / Prepay / Foreclosure)
↓
Payment captured via Razorpay
↓
Webhook validation
↓
Payment recorded in system
↓
Receipt generated

---

### SMS Notifications

Used For:
- EMI reminders (7, 3, 1 days before)
- Due day alerts
- Overdue alerts

Integrated With:
→ MSG91 / Twilio

Flow Mapping:
Reminder Engine
↓
SMS API triggered
↓
Notification delivered to borrower

---

### Email Service

Used For:
- EMI Receipts
- Payment confirmations
- Loan Schedule
- Loan Closure Certificate
- NDC Certificate

Integrated With:
→ Amazon SES / SMTP / SendGrid

Flow Mapping:
Payment / Loan Closure
↓
PDF generated
↓
Email service sends attachment

---

### Push Notifications

Used For:
- Due date reminders
- Overdue alerts

Integrated With:
→ Firebase Cloud Messaging (FCM)

Flow Mapping:
Reminder Trigger
↓
Push Notification Service
↓
Mobile App Notification

---

### Credit Bureau Reporting

Used For:
- Loan status reporting
- Closure updates
- Overdue reporting

Integrated With:
→ TransUnion CIBIL
→ Karza (as API aggregator)

Flow Mapping:
Loan Status Change (ACTIVE / CLOSED / OVERDUE)
↓
Bureau Reporting API
↓
Credit Score Updated

---

### Storage (PDF & Documents)

Used For:
- EMI Receipts
- Loan Closure Certificate
- NDC Certificate
- Payment History Documents

Integrated With:
→ Amazon Web Services (S3)

Flow Mapping:
PDF Generated
↓
Stored in S3 Bucket
↓
Secure download link shared

---

## Architectural Approach

All third-party services are integrated using:
- Service Layer abstraction
- API-based communication
- Webhook handling for payment confirmations
- Secure credential management using environment variables


