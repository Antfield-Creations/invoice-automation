import argparse
import csv
import datetime
import os
import sys
from pathlib import Path
from typing import List, Optional, Sequence

from . import drive
from .config import Config, load_config
from .mail import SmtpConfig, build_message, send_message
from .recipients import load_recipients
from .render import make_environment, render_invoice_html, render_invoice_pdf

LOG_FIELDS = ['invoice_id', 'name', 'email', 'year', 'month', 'status']


def resolve_period(
    now: datetime.datetime,
    config: Config,
    year_arg: Optional[int],
    month_arg: Optional[int],
) -> tuple[int, int]:
    """Invoice period: CLI args override config, config overrides system time.

    Defaults to the current year and month. Out-of-range months roll over
    into adjacent years: month 13 -> January of next year, month 0 ->
    December of the previous year.
    """
    invoice_config = config.get('invoice', {})

    year = year_arg if year_arg is not None else invoice_config.get('year') or now.year
    month = month_arg if month_arg is not None else invoice_config.get('month') or now.month
    year, month = int(year), int(month)

    if not 1 <= month <= 12:
        year += (month - 1) // 12
        month = (month - 1) % 12 + 1

    return year, month


def make_invoice_id(prefix: str, year: int, month: int, index: int) -> str:
    return f'{prefix}{year}{month}-{index}'


def _resolve_recipients_path(args: argparse.Namespace, config: Config) -> Path:
    if args.recipients:
        return Path(args.recipients)
    env_path = os.environ.get('RECIPIENTS_FILE')
    if env_path:
        return Path(env_path)
    # No local file: fetch the members spreadsheet from Proton Drive
    work_dir = Path(os.environ.get('WORK_DIR', '.work'))
    remote_path = config['drive']['members_path']
    print(f'Fetching recipients from Proton Drive: {remote_path}')
    return drive.download(remote_path, work_dir)


def _write_log(out_dir: Path, rows: List[dict]) -> Path:
    log_path = out_dir / 'invoice_log.csv'
    with open(log_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return log_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog='invoice_automation')
    parser.add_argument('-c', '--config', help='Path to config.yaml', default='config.yaml')
    parser.add_argument('--year', type=int, help='Override invoice year')
    parser.add_argument('--month', type=int, help='Override invoice month (wraps past 12)')
    parser.add_argument('--recipients',
                        help='Local members CSV (default: $RECIPIENTS_FILE, else fetched from Proton Drive)')
    parser.add_argument('--out', default=os.environ.get('INVOICE_OUT_DIR', 'out'),
                        help='Output dir for PDFs and invoice_log.csv')
    parser.add_argument('--templates', default=None, help='Template dir (default: config templates_dir)')
    parser.add_argument('--member',
                        help='Invoice only this member, by name or email (default: $MEMBER, else all members)')
    parser.add_argument('--dry-run', action='store_true', help='Generate PDFs and log, but do not send mail or archive')
    parser.add_argument('--no-archive', action='store_true', help='Do not upload results to Proton Drive')
    args = parser.parse_args(argv)

    config = load_config(args.config)
    now = datetime.datetime.now()
    year, month = resolve_period(now, config, args.year, args.month)

    recipients_path = _resolve_recipients_path(args, config)
    recipients = load_recipients(
        str(recipients_path),
        active_values=config.get('recipients', {}).get('active_values'),
    )

    # Optional single-member run: match on name or email (case-insensitive).
    # An explicitly selected member is invoiced even if marked inactive.
    member = (args.member or os.environ.get('MEMBER') or '').strip()
    if member:
        needle = member.lower()
        recipients = [r for r in recipients if r.email.lower() == needle or r.name.lower() == needle]
        if not recipients:
            print(f'No member matches {member!r} (tried name and email)', file=sys.stderr)
            return 1

    templates_dir = args.templates or config.get('templates_dir', 'templates')
    env = make_environment(templates_dir)

    sender = config['sender']
    mail_config = config.get('mail', {})
    id_prefix = config.get('invoice', {}).get('id_prefix', 'AM')

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    smtp = SmtpConfig.from_env()
    dry_run = args.dry_run or os.environ.get('DRY_RUN', '') == '1'

    log_rows: List[dict] = []
    for index, recipient in enumerate(recipients):
        if not recipient.active and not member:
            print(f'Skipping inactive member: {recipient.name}')
            continue

        invoice_id = make_invoice_id(id_prefix, year, month, index)
        html = render_invoice_html(
            env, recipient=recipient, invoice_id=invoice_id, year=year, month=month, now=now,
            amount=str(config.get('invoice', {}).get('amount', '')),
        )
        pdf_path = render_invoice_pdf(html, out_dir / f'{invoice_id}.pdf')

        subject = mail_config.get('subject', 'Contributie {year}-{month}').format(year=year, month=month)
        body = mail_config.get('body', '').format(
            name=recipient.name, year=year, month=month, invoice_id=invoice_id,
        )
        message = build_message(
            sender_name=sender['name'],
            sender_email=sender['email'],
            recipient_name=recipient.name,
            recipient_email=recipient.email,
            subject=subject,
            body=body,
            pdf_path=pdf_path,
            invoice_id=invoice_id,
        )

        status = 'dry-run'
        if not dry_run:
            send_message(smtp, message)
            status = 'sent'

        log_rows.append({
            'invoice_id': invoice_id,
            'name': recipient.name,
            'email': recipient.email,
            'year': year,
            'month': month,
            'status': status,
        })
        print(f'{status}: {invoice_id} -> {recipient.email} ({pdf_path})')

    log_path = _write_log(out_dir, log_rows)

    # Archive to Proton Drive even on dry-run (that is how PDFs are inspected);
    # only the e-mail is skipped on dry-run.
    if not args.no_archive and 'drive' in config:
        archive_remote = f"{config['drive']['archive_root']}/{year}/{month}"
        print(f'Archiving {out_dir} to Proton Drive: {archive_remote}')
        drive.upload(out_dir, archive_remote)

    print(f'Done. {len(log_rows)} invoice(s), log: {log_path}')
    return 0
