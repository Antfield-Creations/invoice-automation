import smtplib
from email import message_from_bytes

import pytest

from invoice_automation.mail import SmtpConfig, build_message, send_message


@pytest.fixture
def pdf_file(tmp_path):
    pdf = tmp_path / 'AM20265-0.pdf'
    pdf.write_bytes(b'%PDF-1.4 fake pdf bytes')
    return pdf


@pytest.fixture
def message(pdf_file):
    return build_message(
        sender_name='Atelier Miereveld', sender_email='ateliermiereveld@proton.me',
        recipient_name='Piet Puk', recipient_email='piet@example.com',
        subject='Contributie 2026-5', body='Beste Piet,',
        pdf_path=pdf_file, invoice_id='AM20265-0',
    )


def test_build_message_headers(message):
    assert message['From'] == 'Atelier Miereveld <ateliermiereveld@proton.me>'
    assert message['To'] == 'Piet Puk <piet@example.com>'
    assert message['Subject'] == 'Contributie 2026-5'


def test_build_message_attachment_named_after_invoice_id(message):
    attachment = next(p for p in message.get_payload() if p.get_content_type() == 'application/pdf')
    assert attachment.get_filename() == 'AM20265-0.pdf'
    assert attachment.get_payload(decode=True) == b'%PDF-1.4 fake pdf bytes'

    # the message must survive a serialization round-trip intact
    parsed = message_from_bytes(message.as_bytes())
    parsed_attachment = next(p for p in parsed.get_payload() if p.get_content_type() == 'application/pdf')
    assert parsed_attachment.get_filename() == 'AM20265-0.pdf'


class _FakeSMTP:
    instances = []

    def __init__(self, host, port):
        self.host, self.port = host, port
        self.calls = []
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.calls.append('starttls')

    def login(self, user, password):
        self.calls.append(('login', user, password))

    def send_message(self, message):
        self.calls.append(('send', message['To']))


def test_send_message_bridge_defaults_no_tls_no_login(monkeypatch, message):
    monkeypatch.setattr(smtplib, 'SMTP', _FakeSMTP)

    send_message(SmtpConfig(host='127.0.0.1', port=1025, username=None, password=None, use_tls=False), message)

    smtp = _FakeSMTP.instances[-1]
    assert (smtp.host, smtp.port) == ('127.0.0.1', 1025)
    assert smtp.calls == [('send', 'Piet Puk <piet@example.com>')]


def test_send_message_smtp_token_uses_starttls_and_login(monkeypatch, message):
    monkeypatch.setattr(smtplib, 'SMTP', _FakeSMTP)

    config = SmtpConfig(
        host='smtp.protonmail.ch', port=587,
        username='ateliermiereveld@proton.me', password='token', use_tls=True,
    )
    send_message(config, message)

    smtp = _FakeSMTP.instances[-1]
    assert smtp.calls[0] == 'starttls'
    assert smtp.calls[1] == ('login', 'ateliermiereveld@proton.me', 'token')
    assert smtp.calls[2][0] == 'send'


def test_smtp_config_from_env_defaults_to_bridge(monkeypatch):
    monkeypatch.delenv('SMTP_HOST', raising=False)
    config = SmtpConfig.from_env({})
    assert (config.host, config.port, config.username, config.use_tls) == ('127.0.0.1', 1025, None, False)


def test_smtp_config_from_env_token(monkeypatch):
    env = {'SMTP_HOST': 'smtp.protonmail.ch', 'SMTP_PORT': '587', 'SMTP_TLS': '1',
           'SMTP_USER': 'ateliermiereveld@proton.me', 'SMTP_PASSWORD': 'secret'}
    config = SmtpConfig.from_env(env)
    assert (config.host, config.port, config.username, config.password, config.use_tls) == \
        ('smtp.protonmail.ch', 587, 'ateliermiereveld@proton.me', 'secret', True)
