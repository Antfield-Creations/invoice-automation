from invoice_automation.recipients import load_recipients

CSV = (
    'Naam,E-mailadres,Adres,Postcode,Woonplaats,Actief\n'
    'Piet Puk,piet@example.com,Hoofdstraat 1,1234AB,Amsterdam,Ja\n'
    'Klaas,Klaas@example.com,Keukenweg 2,5678CD,Rotterdam,Nee\n'
)


def test_load_recipients_parses_columns_and_active_flag(tmp_path):
    csv_file = tmp_path / 'leden.csv'
    csv_file.write_text(CSV, encoding='utf-8')

    recipients = load_recipients(str(csv_file))

    assert len(recipients) == 2
    piet = recipients[0]
    assert piet.name == 'Piet Puk'
    assert piet.email == 'piet@example.com'
    assert piet.address == 'Hoofdstraat 1'
    assert piet.postcode == '1234AB'
    assert piet.city == 'Amsterdam'
    assert piet.active is True
    assert recipients[1].active is False


def test_load_recipients_handles_bom_and_custom_active_values(tmp_path):
    csv_file = tmp_path / 'leden.csv'
    csv_file.write_bytes(b'\xef\xbb\xbf' + CSV.encode('utf-8'))

    recipients = load_recipients(str(csv_file), active_values=['Ja'])

    assert recipients[0].name == 'Piet Puk'
    assert recipients[0].active is True


def test_load_recipients_missing_columns_become_empty(tmp_path):
    csv_file = tmp_path / 'leden.csv'
    csv_file.write_text('Naam\nAlleen een naam\n', encoding='utf-8')

    (recipient,) = load_recipients(str(csv_file))

    assert recipient.name == 'Alleen een naam'
    assert recipient.email == ''
    assert recipient.active is False
