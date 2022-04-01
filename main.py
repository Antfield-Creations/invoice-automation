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
    today = datetime.date.today()

    # Get the invoice template
    invoice_template_doc_id = config['invoice']['template_doc_id']
    if config['invoice']['target_folder'] is not None:
        target_folder = config['invoice']['target_folder']
    else:
        year_folders = drive.list(
            q=f"mimeType='application/vnd.google-apps.folder' and name='{today.year}'",
            spaces='drive',
            fields='nextPageToken, files(id, name)',
        ).execute()
        if len(year_folders) == 0:
            raise NotImplementedError('Still have to implement making target year folder')
        else:
            target_folder = year_folders[0]

    for recipient in recipients:
        drive_response = drive.copy(
            fileId=invoice_template_doc_id,
            body={
                'parents': [target_folder],
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
