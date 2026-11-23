from invoice_automation.docs_api import get_recipients


class _Values:
    def __init__(self, payload):
        self._payload = payload

    def get(self, spreadsheetId, range):
        return self

    def execute(self):
        return self._payload


class _Sheets:
    def __init__(self, payload):
        self._values = _Values(payload)

    def values(self):
        return self._values


def _config():
    return {
        "recipients": {
            "sheet_id": "sheet-1",
            "tab": "Factuurgegevens",
            "range": "A:J",
        }
    }


def test_get_recipients_maps_header_to_row_values():
    sheets = _Sheets({
        "values": [
            ["Naam", "E-mailadres", "Actief"],
            ["Piet", "piet@example.com", "Ja"],
            ["Klaas", "klaas@example.com", "Nee"],
        ]
    })

    recipients = get_recipients(sheets, _config())

    assert recipients == [
        {"Naam": "Piet", "E-mailadres": "piet@example.com", "Actief": "Ja"},
        {"Naam": "Klaas", "E-mailadres": "klaas@example.com", "Actief": "Nee"},
    ]


def test_get_recipients_raises_on_empty_sheet():
    import pytest

    sheets = _Sheets({})

    with pytest.raises(ValueError):
        get_recipients(sheets, _config())
