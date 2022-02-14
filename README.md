# Invoice Automation

_Automate the boring stuff_

Google Drive automation of monthly recurring invoices. 

## Requirements
Assumes the following:
- You have a [Google OAuth credentials](https://console.developers.google.com/apis/credentials) file, path specified in config.yaml
- The OAuth account has write permissions on docs and sheets
- You have enabled the [Google Sheets API](https://console.developers.google.com/apis/api/sheets.googleapis.com)
- You have enabled the [Google Docs API](https://console.developers.google.com/apis/api/docs.googleapis.com)
- There's a Google spreadsheet specified in config.yaml containing names and mail addresses of the people
  that need to receive the monthly recurring invoice
- There's an invoice template in the form of a Google document in the folder location specified in config.yaml

## Installation
```shell
pipenv install
```
If you don't have `pipenv`, install it using `pip install --user pipenv`.
