import smtplib
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def send_digest(gmail_address: str, gmail_app_password: str, recipient: str, matches: list[dict]):
    if not matches:
        return

    lines = []
    for m in matches:
        job = m["job"]
        lines.append(
            f"[{m['score']}/10] {job.title} @ {job.company} ({job.location})\n"
            f"Posted: {job.date_posted}\n"
            f"{m['reasoning']}\n{job.url}\n"
        )
    body = "\n".join(lines)

    msg = MIMEText(body)
    msg["Subject"] = f"Job matches digest — {len(matches)} new"
    msg["From"] = gmail_address
    msg["To"] = recipient

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(gmail_address, gmail_app_password)
        server.sendmail(gmail_address, [recipient], msg.as_string())
