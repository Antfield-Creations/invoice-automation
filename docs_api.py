from typing import List, Dict

from config import Config


def get_recipients(sheets, config: Config) -> List[Dict[str, str]]:
    # Get the recipients sheet
    sheet_id = config['recipients']['sheet_id']
    range = f"{config['recipients']['tab']}!{config['recipients']['range']}"

    recipients = sheets.values().get(spreadsheetId=sheet_id, range=range).execute()

    if len(recipients) == 0:
        sheet_link = f'https://docs.google.com/spreadsheets/d/{sheet_id}'
        raise ValueError(f'Unable to find single tab with name "{config["recipients"]["tab"]}" in {sheet_link}')

    header = recipients['values'][0]
    rows = recipients['values'][1:]

    recipients_list: List[Dict[str, str]] = []

    for row in rows:
        recipient_dict = {key: val for key, val in zip(header, row)}
        recipients_list.append(recipient_dict)

    return recipients_list
