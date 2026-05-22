import requests
import smtplib
import os
import re
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from datetime import datetime

URL = "https://www.objednatvysetrenie.sk/vyber-druhu-vysetrenia.html?page_id=89960&zid=131424"
TARGET = os.environ.get("TARGET", "nový pacient")  # fallback if not set
SENDER = os.environ["GMAIL_SENDER"]
RECIPIENT = os.environ["GMAIL_RECIPIENT"]
LAST_DATE_FILE = "last_date.txt"


def get_last_known_date():
    if os.path.exists(LAST_DATE_FILE):
        with open(LAST_DATE_FILE, "r") as f:
            content = f.read().strip()
            if content:
                return datetime.strptime(content, "%d.%m.%Y")
    return None


def save_date(date_str):
    with open(LAST_DATE_FILE, "w") as f:
        f.write(date_str)


def check():
    response = requests.get(URL)
    soup = BeautifulSoup(response.text, "html.parser")

    for link in soup.find_all("a"):
        text = link.get_text()
        if TARGET.lower() in text.lower():
            parent = link.find_parent()
            page_text = parent.get_text()

            match = re.search(r"najbližší termín: (\d+\.\d+\.\d+)", page_text)
            if match:
                date_str = match.group(1)
                date = datetime.strptime(date_str, "%d.%m.%Y")
                last_date = get_last_known_date()

                print(f"Found: {text.strip()} — {date_str}")

                if last_date is None or date < last_date:
                    print(f"Sooner slot! Was: {last_date}, now: {date_str}")
                    send_alert(date_str, last_date)
                    save_date(date_str)
                else:
                    print("No improvement, skipping.")

                return  # stop after finding the target procedure


def send_alert(date_str, previous_date):
    previous_str = previous_date.strftime("%d.%m.%Y") if previous_date else "unknown"

    msg = MIMEText(
        f"Skorší termín pre '{TARGET}' je dostupný!\n\n"
        f"Predtým: {previous_str}\n"
        f"Teraz:   {date_str}\n\n"
        f"{URL}"
    )
    msg["Subject"] = f"Skorší termín: {date_str}"
    msg["From"] = SENDER
    msg["To"] = RECIPIENT

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER, os.environ["GMAIL_APP_PASSWORD"])
        server.sendmail(SENDER, RECIPIENT, msg.as_string())

    print("Alert sent!")


check()