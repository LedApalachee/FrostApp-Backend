import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os
import secrets

load_dotenv()
sender = os.getenv("SENDER_EMAIL")
mail_password = os.getenv("SENDER_PASSWORD")

# временное хранилище неверифицированных пользователей
# когда почта верифицирована - из vercodes удаляется запись о ней
vercodes = {}

def send_code(email: str) -> str:
    global mail_password, vercodes
    vercode = ''.join(secrets.choice('0123456789') for _ in range(6))
    msg = EmailMessage()
    msg.set_content(f"Hi! Your verification code is {vercode}")
    msg["Subject"] = 'Verification code for SmartFrost App'
    msg["From"] = sender
    msg["To"] = email
    
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, mail_password)
            server.send_message(msg)
            vercodes[vercode] = email
            return "ok"
    except Exception as e:
        return "Error: {e}"


def verify(email: str, vercode: str) -> str | None:
    global vercodes
    if vercodes.get(vercode, None) == email:
        vercodes.pop(vercode, None)
        return "ok"
    return None
