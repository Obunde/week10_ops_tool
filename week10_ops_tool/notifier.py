"""Deliver the alert summary by email, with a console fallback.

All SMTP settings come from environment variables (loaded from ``.env`` by the
caller via python-dotenv). Nothing is hardcoded. If the required SMTP variables
are not set, or ``--dry-run`` is used, the alert is printed to the console
instead so the tool always runs end-to-end without credentials.
"""
from __future__ import annotations

import os
import smtplib
import ssl
import sys
from dataclasses import dataclass
from email.message import EmailMessage

_TRUTHY = {"1", "true", "yes", "on"}


class NotifyError(RuntimeError):
    """Raised when an email alert could not be sent."""


@dataclass
class SmtpSettings:
    host: str
    port: int
    username: str | None
    password: str | None
    use_tls: bool
    sender: str
    recipients: list[str]

    @classmethod
    def from_env(cls) -> "SmtpSettings | None":
        """Build settings from env vars, or return ``None`` if not configured.

        The minimum needed to send is ``SMTP_HOST``, ``ALERT_FROM`` and
        ``ALERT_TO``. Auth is optional (some relays are IP-allowlisted).
        """
        host = os.getenv("SMTP_HOST", "").strip()
        sender = os.getenv("ALERT_FROM", "").strip()
        recipients = [a.strip() for a in os.getenv("ALERT_TO", "").split(",") if a.strip()]
        if not (host and sender and recipients):
            return None

        try:
            port = int(os.getenv("SMTP_PORT", "587"))
        except ValueError:
            raise NotifyError(f"SMTP_PORT must be an integer, got {os.getenv('SMTP_PORT')!r}")

        return cls(
            host=host,
            port=port,
            username=(os.getenv("SMTP_USERNAME") or "").strip() or None,
            password=(os.getenv("SMTP_PASSWORD") or "").strip() or None,
            use_tls=os.getenv("SMTP_USE_TLS", "true").strip().lower() in _TRUTHY,
            sender=sender,
            recipients=recipients,
        )


def send_email(settings: SmtpSettings, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = settings.sender
    msg["To"] = ", ".join(settings.recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.host, settings.port, timeout=30) as server:
            server.ehlo()
            if settings.use_tls:
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
            if settings.username and settings.password:
                server.login(settings.username, settings.password)
            server.send_message(msg)
    except (smtplib.SMTPException, OSError) as exc:
        raise NotifyError(f"failed to send alert email: {exc}") from exc


def deliver(subject: str, body: str, *, dry_run: bool = False, stream=None) -> str:
    """Deliver the alert. Returns the channel used: ``"email"`` or ``"console"``."""
    stream = stream or sys.stdout
    settings = SmtpSettings.from_env()

    if dry_run or settings is None:
        reason = "dry run" if dry_run else "SMTP env vars not set"
        print(f"\n--- ALERT NOT EMAILED ({reason}); printing instead ---", file=stream)
        print(f"Subject: {subject}", file=stream)
        print(body, file=stream)
        print("--- end of alert ---\n", file=stream)
        return "console"

    send_email(settings, subject, body)
    print(
        f"Alert emailed to {', '.join(settings.recipients)} via {settings.host}:{settings.port}",
        file=stream,
    )
    return "email"
