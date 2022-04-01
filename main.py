import argparse
import datetime
import io
import mimetypes
import os.path
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from tempfile import TemporaryDirectory

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

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
    now = datetime.datetime.now()

    # Get the invoice template
    invoice_template_doc_id = config['invoice']['template_doc_id']
    if config['invoice']['target_folder'] is not None:
        target_folder = config['invoice']['target_folder']
    else:
        # Get list of folders by current year
        year_folders = drive.list(
            q=f"mimeType='application/vnd.google-apps.folder' and name='{now.year}'",
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
                'name': f"Factuur {now.year} maand {now.month} voor {recipient['Naam']}"
            }
        ).execute()
        invoice_copy_id = drive_response.get('id')

        changes = [
            {'replaceAllText': {
                    'containsText': {'text': '{{recipient_name}}'},
                    'replaceText': recipient['Naam'],
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{address}}'},
                    'replaceText': recipient['Adres'],
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{postcode}}'},
                    'replaceText': recipient['Postcode'],
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{city}}'},
                    'replaceText': recipient['Plaats'],
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{date}}'},
                    'replaceText': f"{now.day}-{now.month}-{now.year}",
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{year}}'},
                    'replaceText': str(now.year),
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{month}}'},
                    'replaceText': str(now.month),
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{invoice_id}}'},
                    'replaceText': f"AM{now.year}{now.month}-{now.microsecond}",
            }},
        ]

        docs.batchUpdate(documentId=invoice_copy_id, body={'requests': changes}).execute()
        print(f"Created invoice {invoice_copy_id}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config",   help="Path to config.yaml", required=False, default='config.yaml')
    args = parser.parse_args()

    config = load_config(args.config)
    main(config)
