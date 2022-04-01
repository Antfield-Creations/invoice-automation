import argparse
import datetime

from googleapiclient.discovery import build

from auth import get_credentials
from config import load_config, Config
from docs_api import get_recipients


def main(config: Config) -> None:
    # Connect to Google APIs
    creds = get_credentials(config)
    drive = build(serviceName='drive', version='v3', credentials=creds).files()
    docs = build(serviceName='docs', version='v1', credentials=creds).documents()
    sheets = build(serviceName='sheets', version='v4', credentials=creds).spreadsheets()

    recipients = get_recipients(sheets, config)

    # Get the invoice template
    invoice_template_doc_id = config['invoice']['template_doc_id']
    test_folder = '1JgtKVhl7LLll1und9xDjxWunXRQGp__b'
    today = datetime.date.today()

    for recipient in recipients:
        drive_response = drive.copy(
            fileId=invoice_template_doc_id,
            body={
                'parents': [test_folder],
                'name': f"Factuur {today.year} maand {today.month} voor {recipient['Naam']}"
            }
        ).execute()
        invoice_copy_id = drive_response.get('id')
        invoice_copy = docs.get(documentId=invoice_copy_id).execute()

        print(recipient)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config",   help="Path to config.yaml", required=False, default='config.yaml')
    args = parser.parse_args()

    config = load_config(args.config)
    main(config)
