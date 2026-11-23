import datetime

from invoice_automation.recipients import Recipient
from invoice_automation.render import make_environment, render_invoice_html, render_invoice_pdf

TEMPLATE = (
    '<html><body>'
    '<p>{{ recipient_name }}, {{ address }}, {{ postcode }} {{ city }}</p>'
    '<p>Factuur {{ invoice_id }} d.d. {{ date }} voor {{ month }}/{{ year }}, bedrag {{ amount }}</p>'
    '</body></html>'
)


def _recipient():
    return Recipient(
        name='Piet Puk', email='piet@example.com', address='Hoofdstraat 1',
        postcode='1234AB', city='Amsterdam', active=True,
    )


def _env(tmp_path):
    templates = tmp_path / 'templates'
    templates.mkdir()
    (templates / 'invoice.html').write_text(TEMPLATE, encoding='utf-8')
    return make_environment(templates)


def test_render_invoice_html_fills_placeholders(tmp_path):
    html = render_invoice_html(
        _env(tmp_path),
        recipient=_recipient(), invoice_id='AM20265-0', year=2026, month=5,
        now=datetime.datetime(2026, 4, 28), amount='€ 25,00',
    )

    assert 'Piet Puk, Hoofdstraat 1, 1234AB Amsterdam' in html
    assert 'Factuur AM20265-0 d.d. 28-4-2026 voor 5/2026, bedrag € 25,00' in html


def test_render_invoice_pdf_writes_pdf(tmp_path):
    html = render_invoice_html(
        _env(tmp_path),
        recipient=_recipient(), invoice_id='AM20265-0', year=2026, month=5,
        now=datetime.datetime(2026, 4, 28),
    )

    pdf_path = render_invoice_pdf(html, tmp_path / 'out' / 'AM20265-0.pdf')

    assert pdf_path.exists()
    assert pdf_path.read_bytes().startswith(b'%PDF')
    assert pdf_path.stat().st_size > 500


def test_render_escapes_html_in_recipient_fields(tmp_path):
    recipient = Recipient(
        name='<script>alert(1)</script>', email='x@example.com', address='a',
        postcode='p', city='c', active=True,
    )

    html = render_invoice_html(
        _env(tmp_path),
        recipient=recipient, invoice_id='AM20265-0', year=2026, month=5,
        now=datetime.datetime(2026, 4, 28),
    )

    assert '<script>' not in html
    assert '&lt;script&gt;' in html
