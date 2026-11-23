import os
import smtplib
from dataclasses import dataclass
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from pathlib import Path
from typing import Mapping, Optional


@dataclass
class SmtpConfig:
    host: str
    port: int
    username: Optional[str]
    password: Optional[str]
    use_tls: bool  # STARTTLS

    @classmethod
    def from_env(cls, environ: Mapping[str, str] = os.environ) -> 'SmtpConfig':
        """SMTP settings come from the environment so secrets never touch the repo.

        Defaults target a local Proton Mail Bridge (127.0.0.1:1025, no TLS,
        no login). Set SMTP_TLS=1 + SMTP_USER/SMTP_PASSWORD for an SMTP
        submission token on smtp.protonmail.ch:587.
        """
        return cls(
            host=environ.get('SMTP_HOST', '127.0.0.1'),
            port=int(environ.get('SMTP_PORT', '1025')),
            username=environ.get('SMTP_USER') or None,
            password=environ.get('SMTP_PASSWORD') or None,
            use_tls=environ.get('SMTP_TLS', '0') == '1',
        )


def build_message(
    *,
    sender_name: str,
    sender_email: str,
    recipient_name: str,
    recipient_email: str,
    subject: str,
    body: str,
    pdf_path: str | Path,
    invoice_id: str,
) -> MIMEMultipart:
    """Build the invoice mail. The PDF is attached under the invoice id."""
    message = MIMEMultipart()
    message['From'] = formataddr((sender_name, sender_email))
    message['To'] = formataddr((recipient_name, recipient_email))
    message['Subject'] = subject
    message.attach(MIMEText(body, 'plain', 'utf-8'))

    with open(pdf_path, 'rb') as f:
        attachment = MIMEApplication(f.read(), _subtype='pdf')
    attachment.add_header('Content-Disposition', 'attachment', filename=f'{invoice_id}.pdf')
    message.attach(attachment)
    return message


def send_message(smtp: SmtpConfig, message: MIMEMultipart) -> None:
    with smtplib.SMTP(smtp.host, smtp.port) as server:
        if smtp.use_tls:
            server.starttls()
        if smtp.username is not None:
            server.login(smtp.username, smtp.password or '')
        server.send_message(message)
