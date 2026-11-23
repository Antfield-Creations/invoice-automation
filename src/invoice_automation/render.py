import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .recipients import Recipient


def make_environment(templates_dir: str | Path) -> Environment:
    return Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(['html', 'xml']),
    )


def render_invoice_html(
    env: Environment,
    *,
    recipient: Recipient,
    invoice_id: str,
    year: int,
    month: int,
    now: datetime.datetime,
    amount: str = '',
) -> str:
    template = env.get_template('invoice.html')
    return template.render(
        recipient_name=recipient.name,
        address=recipient.address,
        postcode=recipient.postcode,
        city=recipient.city,
        date=f'{now.day}-{now.month}-{year}',
        year=str(year),
        month=str(month),
        invoice_id=invoice_id,
        amount=amount,
    )


def render_invoice_pdf(html: str, target_path: str | Path) -> Path:
    # Imported lazily so that CLI help and HTML-only tests do not need pango
    from weasyprint import HTML

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html).write_pdf(str(target_path))
    return target_path
