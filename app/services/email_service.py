import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "harshithauppe2@gmail.com"      
SMTP_PASSWORD = "zzap hdig kwsj dhwz"         # gmail app password


def send_email(to_email: str, subject: str, body: str):

    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_USERNAME
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()

        print(f"EMAIL SENT TO {to_email}")

    except Exception as e:
        print("Email Error:", str(e))
