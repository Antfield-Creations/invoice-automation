# Invoice Automation

_Automate the boring stuff_

Google Drive automation of monthly recurring invoices. 

## Requirements
Assumes the following:
- You have a Google credentials file, path specified in config.yaml
- The service account
- There's a Google spreadsheet in the folder location specified in config.yaml containing names and mail addresses of the people
  that need to receive the monthly recurring invoice
- There's an invoice template in the form of a Google document in the folder location specified in config.yaml

## Installation
```shell
pipenv install
```
If you don't have `pipenv`, install it using `pip install --user pipenv`.
