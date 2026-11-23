# Migration plan: Google Workspace → Proton (ateliermiereveld@proton.me)

Goal: make the monthly invoicing fully automatic in GitHub Actions — one PDF
invoice per active studio member, e-mailed to the member, attachment named
after the invoice id — with no manual sign-in anywhere.

**Hard constraint: this repo is public.** No member data may be tracked *or*
left untracked-and-committable in the repo. All personal data (recipient list,
generated invoice PDFs, invoice log) lives in **Proton Drive** and is only
pulled into the CI runner at runtime, into a temp dir outside the checkout.

## 1. Current state

| Concern          | Today (Google)                                                                       | Pain point                                                        |
|------------------|--------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| Recipients       | Google Sheet (`config.yaml → recipients.sheet_id`)                                   | Needs Sheets API + OAuth; public repo can't hold the sheet export |
| Invoice template | Google Doc, copied per recipient, text replaced via Docs API                         | Needs Docs + Drive API                                            |
| PDF              | Drive export of the copied doc                                                       | Needs Drive API                                                   |
| Sending          | Gmail API (`gmail.send`), attachment hardcoded `invoice.pdf` (see TODO in `main.py`) | Needs OAuth + manual re-auth                                      |
| Auth             | `auth.py`: interactive `run_local_server` OAuth flow, token cached on disk           | Not automatable in CI                                             |
| Archive          | Copies kept in a Google Drive folder per year                                        | Tied to Google; also PII                                          |
| Runtime          | pipenv + `main.py`, one-off `buffer-invoice.py`, `termux.sh`                         | Android hack, no CI                                               |

## 2. Research findings: what Proton offers programmatically (as of 2026)

**Proton Mail (sending)** — no public REST send API. Options:

- **A. SMTP submission token** — send via `smtp.protonmail.ch:587` (STARTTLS)
  with address + token from Proton → Settings → IMAP/SMTP. Easiest in CI,
  but tokens only pair with a **custom-domain** address, not @proton.me.
- **B. Proton Mail Bridge in Docker** — Bridge exposes local SMTP on
  `127.0.0.1:1025`; run it headless in the runner, feed login via stdin (TOTP
  computed from a secret), cache the vault with `actions/cache`. Works with
  @proton.me as-is; more moving parts (paid plan, pinned image).
- **C. Unofficial API clients** (e.g. PyPI `proton-mail-api`) — not
  recommended: unofficial, breaks with 2FA, ToS risk.

**Proton Drive (files, incl. the members spreadsheet)** — this is the API path:

- **Official Proton Drive CLI** (`proton-drive`, released June 2026, v0.9.x;
  binary from `proton.me/download/drive/cli`, source
  `github.com/ProtonDriveApps/sdk` → `cli/README.md`). Built for exactly this:
  "Run Drive operations from any shell, container, or CI runner with JSON
  output and predictable exit codes." Commands: `proton-drive auth login`,
  `proton-drive filesystem list|upload|download <cloud-path> [local-path]`,
  `proton-drive sharing ...`, `--json` everywhere.
- **Headless auth**: browser login by default, but on servers
  `PROTON_DRIVE_CREDENTIALS_STORE=pass` (passwordstore + non-interactively
  unlocked GPG key) stores the session; the session/pass store can be cached
  between runs with `actions/cache`. There are no Drive API keys/PATs (only
  Proton Pass CLI has those) — auth is session-based via username + password
  (+ TOTP, computable in CI from a `PROTON_TOTP_SECRET` secret with
  `oathtool`). Note: an open SDK issue reports incomplete 2FA support in the
  raw SDK, so verify the CLI login path with TOTP first during implementation.
  Decision: **official `proton-drive` CLI only** — no rclone or other
  third-party clients.
- **Proton Sheets has no API yet** (automation requests are still open
  threads) — a Sheets file cannot be *queried* via API, and CSV/TSV/XLSX
  export exists only in the UI (File → Download), not via the CLI. Decision:
  members keep editing the spreadsheet in **Proton Sheets**; the workflow
  downloads the file from Drive with `proton-drive filesystem download` and
  extracts the data from it. During implementation, verify what format the CLI
  yields for a Sheets file — if it is not directly parseable, fall back to a
  **CSV export uploaded to Drive** (`/Leden/leden.csv`) as the machine-readable
  copy the workflow reads.

## 3. Target architecture

```
templates/invoice.html     # Jinja2 template (was: Google Doc), same placeholders
config.yaml                # sender, invoice id prefix, Drive paths, defaults
pyproject.toml + uv.lock   # dependencies via uv (replaces Pipfile/pipenv)
src/invoice_automation/
  config.py                # load config + env overrides
  drive.py                 # proton-drive CLI wrapper: login, download, upload
  recipients.py            # parse members CSV from a temp path (never the repo)
  render.py                # Jinja2 -> HTML -> PDF (WeasyPrint)
  mail.py                  # MIME message, attachment "<invoice_id>.pdf", send via SMTP
  cli.py                   # orchestrates fetch -> generate -> send (or --dry-run) -> archive
Makefile                   # every command the workflow runs
.github/workflows/invoice.yml
```

Data flow (nothing personal ever enters the repo):

```
Proton Drive /Leden/leden.csv  --(proton-drive filesystem download)-->  $RUNNER_TEMP/
$RUNNER_TEMP/leden.csv + template --> PDFs in $RUNNER_TEMP/invoices/<id>.pdf
PDFs --(SMTP, attachment "<invoice_id>.pdf")--> member
PDFs + invoice_log.csv --(proton-drive filesystem upload)--> Proton Drive /Facturen/<year>/<month>/
```

Kept from the old script: invoices are issued for *next* month, `year`/`month`
overridable (workflow inputs / CLI flags), inactive members skipped, invoice id
`AM<year><month>-<n>`. Attachment is written to `<invoice_id>.pdf` and attached
under exactly that name (fixes the old hardcoded `invoice.pdf` / TODO).

Repo hygiene: `.gitignore` gains `data/`, `*.csv`, `invoices/`,
`credentials*`; a CI guard step fails the build if `git ls-files` (or the
working tree) contains recipient/invoice data files. Downloads go to
`$RUNNER_TEMP`, outside the checkout, via `RECIPIENTS_FILE` env var.

## 4. Repo refactor

- Replace the Google Sheet with a **CSV in Proton Drive**, fetched at runtime
  by `drive.py` (official proton-drive CLI). Columns: Naam,
  E-mailadres, Adres, Postcode, Woonplaats, Actief.
- Replace the Google Doc template with `templates/invoice.html` (Jinja2,
  placeholders `{{recipient_name}}`, `{{address}}`, `{{postcode}}`, `{{city}}`,
  `{{date}}`, `{{year}}`, `{{month}}`, `{{invoice_id}}`) rendered to PDF with
  WeasyPrint (HTML/CSS keeps the invoice easy to restyle; system libs via
  Makefile).
- Archive: generated PDFs and `invoice_log.csv` are **uploaded to Proton Drive**
  (`/Facturen/<year>/<month>/`), not committed; workflow artifacts are used only
  as a non-PII debug aid (logs without addresses, or PDFs only on private
  forks). The old `invoice_log` sheet maps to the CSV log in Drive.
- Dependencies: move from pipenv to **uv** — `pyproject.toml` + `uv.lock`,
  installed in CI via `astral-sh/setup-uv`, synced with `uv sync` and run with
  `uv run` (Python 3.12 on ubuntu-latest).
- Remove: `Pipfile`/`Pipfile.lock`, `auth.py`, `docs_api.py`,
  `buffer-invoice.py` (one-off buffer invoice is no longer needed — dropped
  entirely), `credentials/` (untracked, but
  delete `credentials.zip` locally and revoke the Google OAuth client),
  `.idea/`, `termux.sh` (superseded by CI).
- Add `tests/` (CSV parsing, id generation, MIME attachment filename, dry-run
  render with a **fake** recipient fixture) run by `make test` in CI.

## 5. Makefile (all commands the workflow uses)

| Target                                                       | Purpose                                                                                      |
|--------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| `make install`                                               | system libs (WeasyPrint/pango) + `uv sync` + install `proton-drive` CLI                      |
| `make lint` / `make test`                                    | ruff + pytest + pytest-cov (`make coverage`)                                                                                |
| `make drive-login`                                           | non-interactive `proton-drive auth login` from secrets (pass store in `$RUNNER_TEMP`)        |
| `make fetch-recipients`                                      | download `/Leden/leden.csv` to `$RUNNER_TEMP`                                                |
| `make generate`                                              | render all PDFs named `<invoice_id>.pdf` into `$RUNNER_TEMP/invoices/`                       |
| `make send`                                                  | send each PDF by SMTP, attachment named `<invoice_id>.pdf`                                   |
| `make archive`                                               | upload PDFs + `invoice_log.csv` to Proton Drive `/Facturen/<year>/<month>/`                  |
| `make run`                                                   | fetch + generate + send + archive (honors `YEAR=`, `MONTH=`, `DRY_RUN=1`)                    |
| `make bridge-login` / `make bridge-up` / `make bridge-creds` | Docker lifecycle for Proton Mail Bridge (decided mail path) — wrapped so it runs locally too |
| `make check-no-pii`                                          | fail if repo tracks/contains recipient or invoice data files                                 |
| `make clean`                                                 | remove build artifacts                                                                       |

All Makefile targets run identically locally and in CI — the Docker details of
Bridge are hidden inside the `make bridge-*` targets, so a successor only ever
runs `make run` (Docker required locally for the mail step).

## 6. GitHub Actions workflows

Two workflows, deliberately separated:

- `.github/workflows/ci.yml` — code changes only: runs on `push` and
  `pull_request`, executes `make install-system`, `uv sync`, `make lint`,
  `make coverage`, `make check-no-pii`.
- `.github/workflows/invoice.yml` — invoicing: **never on push**, only
  `schedule` cron `0 8 1 * *` (1st of the month, 08:00 UTC) and
  `workflow_dispatch` with inputs `year` (empty = current year), `month`
  (empty = current month), `member` (empty = all members; otherwise a single
  member by name or email) and
  `dry_run` (default **true** for manual runs — recipients fetched, PDFs
  generated and uploaded to Drive, nothing e-mailed).
- Steps: checkout → `astral-sh/setup-uv` → `make install` → `make drive-login` →
  `make bridge-login && make bridge-up` (Bridge is the decided mail path) →
  `make run` with secrets as env → summary output (no artifact upload —
  the repo is public and PDFs/log contain member data; inspect them in
  Proton Drive instead). On dry-run no mail is sent, but PDFs are still
  archived to Drive for inspection.
- Secrets (GitHub Actions secrets only, never in the repo):
  `PROTON_USERNAME`, `PROTON_PASSWORD`, `PROTON_MAILBOX_PASSWORD`,
  `PROTON_TOTP_SECRET`, `PROTON_DRIVE_CREDENTIALS_STORE` setup (cached pass
  store / GPG key as secrets), and — if a custom domain is added —
  `SMTP_HOST/PORT/USER/TOKEN`.

## 7. Migration steps

1. **Export data**: export the Google Sheet (CSV/XLSX) for import into Proton
   Sheets; recreate the invoice layout as `templates/invoice.html`.
2. **Proton setup**: confirm `ateliermiereveld@proton.me`; enable 2FA (TOTP);
   upload the members spreadsheet to a Drive folder (e.g. `/Leden/`); create
   the `/Facturen/` archive folder; set up headless Proton Mail Bridge (the
   decided mail path); verify `proton-drive auth login` works headless; store
   everything as GitHub secrets.
3. **Refactor the repo** on this `proton` branch: new package, template,
   Makefile, tests; delete Google-specific modules; harden `.gitignore`.
4. **Add the workflow in dry-run** and test via `workflow_dispatch` with
   `year`/`month` set to a past month; inspect PDFs in Drive/artifacts.
5. **First real send** (scheduled, or manual dispatch with `dry_run=false`);
   verify members received mail with attachment e.g. `AM2026-5-3.pdf`, and that
   PDFs + log landed in `/Facturen/<year>/<month>/` in Drive.
6. **Decommission Google**: revoke OAuth client + tokens, delete local
   `credentials.zip`, remove Drive/Sheets API access, archive the old sheet.
7. **Cleanup**: remove legacy files listed in section 4, update README.

## 8. Decisions

1. **Mail: Proton Mail Bridge in Docker** (option B), the straightforward path
   for @proton.me. All Docker complexity is wrapped in the `make bridge-*`
   targets, which run identically locally and in CI — nobody after us has to
   touch Docker directly, they just run `make run`. If a custom domain is ever
   added to the account, switching to an SMTP submission token (option A)
   removes the container entirely; `mail.py` already speaks plain SMTP from
   env vars, so that is a config change, not a code change.
2. **Drive: official `proton-drive` CLI only** — no rclone, no unofficial
   clients.
3. **Members spreadsheet stays in Proton Sheets.** The workflow downloads the
   file from Drive with the CLI and extracts the data from it; if the
   downloaded format turns out not to be parseable, fall back to a CSV export
   in Drive as the machine-readable copy. No member data in the repo, ever.
4. **One-off buffer invoice: dropped.** `buffer-invoice.py` is deleted with no
   replacement.
