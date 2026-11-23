# Invoice Automation

_Automate the boring stuff_

Monthly recurring invoices for Atelier Miereveld: one PDF per active studio
member, e-mailed from the Proton account (`ateliermiereveld@proton.me`) with
the attachment named after the invoice id. Fully automated via GitHub Actions
(see `.github/workflows/invoice.yml` and `MIGRATION.md`).

**This repository is public: it never contains member data.** The members
spreadsheet and all generated invoices live in Proton Drive and are only
fetched/uploaded at runtime with the official `proton-drive` CLI.

## How it works

1. Fetch the members CSV from Proton Drive (`drive.members_path` in `config.yaml`)
2. Render `templates/invoice.html` per active member to `<invoice_id>.pdf` (WeasyPrint)
3. Send the PDF by SMTP (Proton Mail Bridge locally, or an SMTP submission
   token) with attachment name `<invoice_id>.pdf`
4. Archive PDFs + `invoice_log.csv` back to Proton Drive (`drive.archive_root`)

## Requirements

- [uv](https://docs.astral.sh/uv/) (package manager)
- The official [Proton Drive CLI](https://proton.me/drive/download) (`make install-cli`)
- Docker, only for sending mail through Proton Mail Bridge (`make bridge-up`)
- `config.yaml` (see the file for all options; SMTP credentials come from
  `SMTP_HOST`/`SMTP_PORT`/`SMTP_TLS`/`SMTP_USER`/`SMTP_PASSWORD` env vars —
  never commit them)

## Installation

```shell
make install        # system libs + uv sync
make install-cli    # proton-drive CLI
```

## Running

```shell
make run                          # full pipeline (fetch -> generate -> send -> archive)
make generate                     # dry run: PDFs only, archived to Drive, no mail
make run YEAR=2026 MONTH=5        # override invoice period
make run DRY_RUN=1                # dry run via env
```

Or directly:

```shell
uv run python -m invoice_automation --help
```

## Testing

```shell
make test        # pytest
make coverage    # pytest with coverage report
make lint        # ruff
```

## Layout

```
src/invoice_automation/
  cli.py          # orchestration: fetch -> generate -> send -> archive
  config.py       # config.yaml loading
  recipients.py   # members CSV parsing (never stored in the repo)
  render.py       # Jinja2 -> HTML -> PDF (WeasyPrint)
  mail.py         # MIME message + SMTP send (attachment named <invoice_id>.pdf)
  drive.py        # proton-drive CLI wrapper (download/upload)
templates/invoice.html
tests/
Makefile          # all commands used by the workflow
.github/workflows/invoice.yml
```
