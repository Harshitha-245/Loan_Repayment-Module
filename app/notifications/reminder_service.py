import smtplib
from email.mime.text import MIMEText

SMTP_EMAIL = "harshithauppe2@gmail.com"
SMTP_PASSWORD = "jccg jlyu hkfs ndls"


def send_email_real(to_email, message):
    msg = MIMEText(message)
    msg["Subject"] = "EMI Reminder"
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, to_email, msg.as_string())

    print("Email sent to", to_email)


def send_sms(user, message):
    print("SMS sent to", user.phone)


def send_push(user, message):
    print("Push sent to user", user.user_id)