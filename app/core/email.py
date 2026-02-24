import smtplib
import os
from email.mime.text import MIMEText

def send_mail(to_email: str, subject: str, body: str):
    from_email = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASSWORD")

    if not from_email or not password:
        raise Exception("Email credentials missing")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email

    server = smtplib.SMTP(os.getenv("EMAIL_HOST"), int(os.getenv("EMAIL_PORT")))
    server.starttls()
    server.login(from_email, password)
    server.sendmail(from_email, [to_email], msg.as_string())
    server.quit()
