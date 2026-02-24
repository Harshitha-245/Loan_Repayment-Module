from app.notifications.email_service import send_email

def notify_user(user, message, reminder_type):
    print("\n========== EMI NOTIFICATION ==========")

    # SMS 
    print("[SMS NOTIFICATION]")
    print(f"To     : {user.mobile_number}")
    print(f"Message: {message}")
    print("-------------------------------------")

    # PUSH Notification
    print("[PUSH NOTIFICATION]")
    print(f"User ID: {user.user_id}")
    print(f"Message: {message}")
    print("-------------------------------------")

    # EMAIL 
    print("[EMAIL]")
    print(f"To     : {user.email}")
    print("Status : Sending email...")
    
    send_email(
        to_email=user.email,
        subject="EMI Payment Reminder",
        body=message
    )

    print("Status : Email sent successfully")
    print("=====================================\n")
