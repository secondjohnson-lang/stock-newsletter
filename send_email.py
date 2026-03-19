import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def send_newsletter(html_content):
    host = os.getenv("MAILTRAP_HOST")
    port = int(os.getenv("MAILTRAP_PORT"))
    username = os.getenv("MAILTRAP_USER")
    password = os.getenv("MAILTRAP_PASS")
    mail_from = os.getenv("MAIL_FROM")
    mail_to = os.getenv("MAIL_TO")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"Letters to the Betters"
    msg["From"] = mail_from
    msg["To"] = mail_to

    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(mail_from, mail_to, msg.as_string())

    print(f"Newsletter sent to {mail_to}")
