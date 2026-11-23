import csv
from dataclasses import dataclass
from typing import List, Optional, Sequence

# Column headers as exported from the members spreadsheet (Proton Sheets / CSV)
COLUMN_NAME = 'Naam'
COLUMN_EMAIL = 'E-mailadres'
COLUMN_ADDRESS = 'Adres'
COLUMN_POSTCODE = 'Postcode'
COLUMN_CITY = 'Woonplaats'
COLUMN_ACTIVE = 'Actief'

DEFAULT_ACTIVE_VALUES = ['Ja', 'ja', 'Actief lid']


@dataclass
class Recipient:
    name: str
    email: str
    address: str
    postcode: str
    city: str
    active: bool


def load_recipients(path: str, active_values: Optional[Sequence[str]] = None) -> List[Recipient]:
    """Read the members CSV downloaded from Proton Drive.

    utf-8-sig strips the BOM that spreadsheet exports often carry.
    """
    if active_values is None:
        active_values = DEFAULT_ACTIVE_VALUES

    recipients: List[Recipient] = []
    with open(path, newline='', encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            recipients.append(Recipient(
                name=row.get(COLUMN_NAME, '').strip(),
                email=row.get(COLUMN_EMAIL, '').strip(),
                address=row.get(COLUMN_ADDRESS, '').strip(),
                postcode=row.get(COLUMN_POSTCODE, '').strip(),
                city=row.get(COLUMN_CITY, '').strip(),
                active=row.get(COLUMN_ACTIVE, '').strip() in active_values,
            ))
    return recipients
