import argparse
import base64
import datetime
import io
import os.path
from email.encoders import encode_base64
from email.mime.application import MIMEApplication
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
    gmail = build(serviceName='gmail', version='v1', credentials=creds).users().messages()

    recipients = get_recipients(sheets, config)
    name_column = config['recipients']['name']
    email_column = config['recipients']['email']
    address_column = config['recipients']['address']
    postcode_column = config['recipients']['postcode']
    city_column = config['recipients']['city']

    now = datetime.datetime.now()

    target_folder = '1_5aj2sn7pxGya51JK6WwbLbA11sFEaLc'
    invoice_template_doc_id = '1W7uhfDQFTNnV5DtMEBqtJFmZeWZgZ1Tda87vCQjMvHI'

    for recipient_id, recipient in enumerate(recipients):
        # human-readable invoice id
        invoice_id = f"AMBUFFER-{recipient_id}"

        drive_response = drive.copy(
            fileId=invoice_template_doc_id,
            body={
                'parents': [target_folder],
                'name': f"Factuur id {invoice_id} voor {recipient[name_column]}"
            }
        ).execute()

        # Google doc id
        invoice_copy_id = drive_response.get('id')

        # Configure templated values
        changes = [
            {'replaceAllText': {
                    'containsText': {'text': '{{recipient_name}}'},
                    'replaceText': recipient[name_column],
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{address}}'},
                    'replaceText': recipient[address_column],
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{postcode}}'},
                    'replaceText': recipient[postcode_column],
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{city}}'},
                    'replaceText': recipient[city_column],
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{date}}'},
                    'replaceText': f"{now.day}-{now.month}-{now.year}",
            }},
            {'replaceAllText': {
                    'containsText': {'text': '{{invoice_id}}'},
                    'replaceText': invoice_id,
            }},
        ]

        docs.batchUpdate(documentId=invoice_copy_id, body={'requests': changes}).execute()

        # Save the file locally
        content_type = 'application/pdf'
        request = drive.export_media(fileId=invoice_copy_id, mimeType=content_type)

        with TemporaryDirectory() as tempdir:
            invoice_file_path = os.path.join(tempdir, 'invoice.pdf')

            fh = io.FileIO(file=invoice_file_path, mode='wb')
            downloader = MediaIoBaseDownload(fh, request)

            done = False
            while done is False:
                status, done = downloader.next_chunk()

            fh.close()

            # Create the invoice message
            message = MIMEMultipart()
            main_type, sub_type = content_type.split('/', 1)

            with open(invoice_file_path, 'rb') as f:
                attachment = MIMEApplication(f.read(), _subtype=sub_type, _encoder=encode_base64)
                filename = os.path.basename(invoice_file_path)
                attachment.add_header('content-disposition', 'attachment', filename=filename)
                message.attach(attachment)

            message['to'] = recipient[email_column]
            message['from'] = 'ateliermiereveld@gmail.com'
            message['subject'] = f'Eenmalige factuur huurbuffer'
            body = MIMEText(
                f'Beste {recipient[name_column]},\n\n'
                'Hierbij ontvang je (aangehecht) de eenmalige factuur voor opbouw van de buffer voor het atelier.\n'
                'Gelieve deze z.s.m, doch uiterlijk binnen 14 dagen te voldoen.\n\n'
                'Alvast dank,\n\n'
                'Het bestuur van Atelier Miereveld\n\n'
                '(Dit bericht is automatisch aangemaakt en verzonden)'
            )
            message.attach(body)

            message_b64 = base64.urlsafe_b64encode(message.as_bytes()).decode()
            gmail_response = gmail.send(userId='me', body={'raw': message_b64}).execute()

        print(f"Created invoice {invoice_copy_id} for {recipient[name_column]}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config",   help="Path to config.yaml", required=False, default='config.yaml')
    args = parser.parse_args()

    config = load_config(args.config)
    main(config)
