from unittest.mock import MagicMock, patch

from src.digest_email import send_digest
from src.fetchers.base import Job

JOB = Job(
    id="",
    title="Engineering Manager, Climate Software",
    company="Acme",
    location="Remote",
    description="Lead a team building solar forecasting tools.",
    url="https://example.com/1",
    date_posted="2026-01-15",
    source="greenhouse",
)


def test_send_digest_includes_date_posted_in_body():
    with patch("src.digest_email.smtplib.SMTP") as smtp_cls:
        smtp = MagicMock()
        smtp_cls.return_value.__enter__.return_value = smtp

        send_digest(
            "me@gmail.com",
            "app-password",
            "recipient@example.com",
            [{"job": JOB, "score": 9, "reasoning": "Great fit."}],
        )

    sent_body = smtp.sendmail.call_args[0][2]
    assert "Posted: 2026-01-15" in sent_body


def test_send_digest_does_nothing_for_no_matches():
    with patch("src.digest_email.smtplib.SMTP") as smtp_cls:
        send_digest("me@gmail.com", "app-password", "recipient@example.com", [])

    smtp_cls.assert_not_called()
