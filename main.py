import argparse
from googleapiclient.discovery import build

from auth import get_credentials
from config import load_config, Config
from docs_api import get_recipients


def main(config: Config) -> None:
    # Connect to Google Docs API
    creds = get_credentials(config)
    docs = build(serviceName='docs', version='v1', credentials=creds).documents()
    sheets = build(serviceName='sheets', version='v4', credentials=creds).spreadsheets()

    recipients = get_recipients(sheets, config)

    # Get the invoice template
    doc_id = config['invoice']['template_doc_id']
    template_document = docs.get(documentId=doc_id).execute()
    print("Done!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config",   help="Path to config.yaml", required=False, default='config.yaml')
    args = parser.parse_args()

    config = load_config(args.config)
    main(config)
