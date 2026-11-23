import csv
import datetime

import pytest

from invoice_automation import cli, drive

CONFIG = """
sender:
  name: Atelier Miereveld
  email: ateliermiereveld@proton.me
invoice:
  id_prefix: AM
  amount: "EUR 25,00"
  year:
  month:
templates_dir: {templates}
drive:
  members_path: /Leden/leden.csv
  archive_root: /Facturen
recipients:
  active_values: [Ja]
mail:
  subject: "Contributie {{year}}-{{month}}"
  body: "Beste {{name}}, factuur {{invoice_id}} voor {{month}}/{{year}}"
"""

MEMBERS_CSV = (
    'Naam,E-mailadres,Adres,Postcode,Woonplaats,Actief\n'
    'Piet Puk,piet@example.com,Hoofdstraat 1,1234AB,Amsterdam,Ja\n'
    'Klaas Klaassen,klaas@example.com,Keukenweg 2,5678CD,Rotterdam,Nee\n'
)

TEMPLATE = '<html><body>Factuur {{ invoice_id }} voor {{ recipient_name }} ({{ month }}/{{ year }})</body></html>'


@pytest.fixture
def workspace(tmp_path):
    templates = tmp_path / 'templates'
    templates.mkdir()
    (templates / 'invoice.html').write_text(TEMPLATE, encoding='utf-8')
    members = tmp_path / 'leden.csv'
    members.write_text(MEMBERS_CSV, encoding='utf-8')
    config = tmp_path / 'config.yaml'
    config.write_text(CONFIG.format(templates=templates), encoding='utf-8')
    return tmp_path, config, members, templates


def _run(workspace, *extra_args):
    tmp_path, config, members, templates = workspace
    out = tmp_path / 'out'
    argv = ['-c', str(config), '--recipients', str(members), '--out', str(out), *extra_args]
    assert cli.main(argv) == 0
    return out


def test_dry_run_generates_pdf_named_after_invoice_id_and_log(workspace, monkeypatch):
    uploads = []
    monkeypatch.setattr(drive, 'upload', lambda local, remote: uploads.append((str(local), remote)))
    sent = []
    monkeypatch.setattr(cli, 'send_message', lambda smtp, message: sent.append(message))

    out = _run(workspace, '--dry-run', '--year', '2026', '--month', '5')

    pdf = out / 'AM20265-0.pdf'
    assert pdf.exists()
    assert pdf.read_bytes().startswith(b'%PDF')
    # inactive member Klaas is skipped
    assert not (out / 'AM20265-1.pdf').exists()
    # dry-run: nothing mailed, but PDFs still archived to Drive for inspection
    assert sent == []
    assert uploads == [(str(out), '/Facturen/2026/5')]

    with open(out / 'invoice_log.csv', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert rows == [{
        'invoice_id': 'AM20265-0', 'name': 'Piet Puk', 'email': 'piet@example.com',
        'year': '2026', 'month': '5', 'status': 'dry-run',
    }]


def test_send_sends_only_to_active_members_and_archives(workspace, monkeypatch):
    sent = []
    monkeypatch.setattr(cli, 'send_message', lambda smtp, message: sent.append(message))
    uploads = []
    monkeypatch.setattr(drive, 'upload', lambda local, remote: uploads.append((str(local), remote)))

    out = _run(workspace, '--year', '2026', '--month', '5')

    assert len(sent) == 1
    assert sent[0]['To'] == 'Piet Puk <piet@example.com>'
    assert sent[0]['Subject'] == 'Contributie 2026-5'
    attachment = next(p for p in sent[0].get_payload() if p.get_content_type() == 'application/pdf')
    assert attachment.get_filename() == 'AM20265-0.pdf'

    assert uploads == [(str(out), '/Facturen/2026/5')]

    with open(out / 'invoice_log.csv', newline='', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    assert rows[0]['status'] == 'sent'


def test_recipients_fetched_from_drive_when_no_local_file(workspace, monkeypatch, tmp_path):
    _, config, members, _ = workspace
    monkeypatch.setattr(cli, 'send_message', lambda smtp, message: None)
    monkeypatch.setattr(drive, 'upload', lambda local, remote: None)
    monkeypatch.setenv('WORK_DIR', str(tmp_path / 'work'))

    def fake_download(remote_path, local_dir):
        assert remote_path == '/Leden/leden.csv'
        local_dir.mkdir(parents=True, exist_ok=True)
        target = local_dir / 'leden.csv'
        target.write_text(MEMBERS_CSV, encoding='utf-8')
        return target

    monkeypatch.setattr(drive, 'download', fake_download)
    monkeypatch.delenv('RECIPIENTS_FILE', raising=False)

    out = tmp_path / 'out'
    assert cli.main(['-c', str(config), '--out', str(out), '--dry-run', '--year', '2026', '--month', '5']) == 0
    assert (out / 'AM20265-0.pdf').exists()


def test_recipients_file_env_var_is_used(workspace, monkeypatch, tmp_path):
    _, config, members, _ = workspace
    monkeypatch.setattr(cli, 'send_message', lambda smtp, message: None)
    monkeypatch.setattr(drive, 'upload', lambda local, remote: None)
    monkeypatch.setenv('RECIPIENTS_FILE', str(members))

    out = tmp_path / 'out'
    assert cli.main(['-c', str(config), '--out', str(out), '--dry-run', '--year', '2026', '--month', '5']) == 0
    assert (out / 'AM20265-0.pdf').exists()


def test_dry_run_env_var(workspace, monkeypatch):
    monkeypatch.setenv('DRY_RUN', '1')
    sent = []
    monkeypatch.setattr(cli, 'send_message', lambda smtp, message: sent.append(message))
    monkeypatch.setattr(drive, 'upload', lambda local, remote: None)

    _run(workspace, '--year', '2026', '--month', '5')

    assert sent == []


def test_resolve_period_wraps_past_december():
    now = datetime.datetime(2026, 12, 15)
    assert cli.resolve_period(now, {}, None, None) == (2027, 1)


def test_resolve_period_config_overrides_system_time_and_args_win():
    now = datetime.datetime(2026, 4, 28)
    assert cli.resolve_period(now, {'invoice': {'year': 2026, 'month': 5}}, None, None) == (2026, 5)
    assert cli.resolve_period(now, {'invoice': {'year': 2026, 'month': 5}}, 2030, 11) == (2030, 11)


def test_make_invoice_id():
    assert cli.make_invoice_id('AM', 2026, 5, 3) == 'AM20265-3'
