import resend

from app.core.config import settings
from app.templates.otp_email import otp_email_html, otp_email_text

resend.api_key = settings.resend_api_key


def send_otp_email(to: str, code: str, minutes: int = 10) -> None:
    resend.Emails.send({
        "from": settings.email_from,
        "to": [to],
        "subject": f"Your NoraChat code: {code}",
        "html": otp_email_html(code, minutes),
        "text": otp_email_text(code, minutes),
    })