# All commands used by the GitHub Actions workflow are wrapped here,
# so CI and local runs execute exactly the same steps.

UV ?= uv
PY := $(UV) run python
PROTON_DRIVE ?= proton-drive
# Official CLI download page: https://proton.me/drive/download (CLI section)
PROTON_DRIVE_URL ?= https://proton.me/download/drive/cli/linux/x64/proton-drive

WORK_DIR ?= .work
OUT_DIR ?= out
MEMBERS_REMOTE ?= /Leden/leden.csv
ARCHIVE_REMOTE_ROOT ?= /Facturen

BRIDGE_IMAGE ?= ghcr.io/aarnaud/docker-protonmail-bridge:v3.27.1
BRIDGE_CONTAINER ?= proton-bridge
BRIDGE_DATA ?= $(CURDIR)/.bridge-data

YEAR ?=
MONTH ?=
DRY_RUN ?=

YEAR_ARG = $(if $(YEAR),--year $(YEAR))
MONTH_ARG = $(if $(MONTH),--month $(MONTH))
DRY_RUN_ARG = $(if $(filter 1 true,$(DRY_RUN)),--dry-run)
COMMON_ENV = RECIPIENTS_FILE=$(WORK_DIR)/leden.csv

.PHONY: install install-system install-cli lint test coverage drive-login fetch-recipients generate send run archive bridge-login bridge-up bridge-creds check-no-pii clean

install: install-system
	$(UV) sync

# System libraries required by WeasyPrint (pango/harfbuzz)
install-system:
	sudo apt-get update
	sudo apt-get install -y libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libharfbuzz-subset0

install-cli:
	curl -fsSL "$(PROTON_DRIVE_URL)" -o /usr/local/bin/$(PROTON_DRIVE)
	sudo chmod +x /usr/local/bin/$(PROTON_DRIVE)

lint:
	$(PY) -m ruff check src tests

test:
	$(PY) -m pytest -q

coverage:
	$(PY) -m pytest -q --cov=invoice_automation --cov-report=term-missing

# Non-interactive login of the official Proton Drive CLI (headless servers
# use the pass credential store; see PROTON_DRIVE_CREDENTIALS_STORE)
drive-login:
	PROTON_DRIVE_CREDENTIALS_STORE=pass $(PROTON_DRIVE) auth login

fetch-recipients:
	$(PROTON_DRIVE) filesystem download $(MEMBERS_REMOTE) $(WORK_DIR)

# Render PDFs only (dry run: no mail is sent; PDFs still go to Drive for inspection)
generate: fetch-recipients
	DRY_RUN=1 $(COMMON_ENV) $(PY) src/main.py --out $(OUT_DIR) $(YEAR_ARG) $(MONTH_ARG)

# Fetch recipients, generate PDFs, send mail, archive to Drive
send: fetch-recipients
	$(COMMON_ENV) $(PY) src/main.py --out $(OUT_DIR) $(YEAR_ARG) $(MONTH_ARG)

# Full pipeline in one process (the CLI fetches recipients and archives itself)
run:
	$(PY) src/main.py --out $(OUT_DIR) $(YEAR_ARG) $(MONTH_ARG) $(DRY_RUN_ARG)

archive:
	$(PROTON_DRIVE) filesystem upload $(OUT_DIR) $(ARCHIVE_REMOTE_ROOT)

# Proton Mail Bridge lifecycle (decided mail path). Login once via stdin
# (CI feeds credentials from secrets); afterwards the session persists
# in the mounted volume and bridge-up just starts the container.
bridge-login:
	docker run -i --rm -v $(BRIDGE_DATA):/home/bridge $(BRIDGE_IMAGE) init

bridge-up:
	docker run -d --name $(BRIDGE_CONTAINER) \
		-p 127.0.0.1:1025:1025 -p 127.0.0.1:1143:1143 \
		-v $(BRIDGE_DATA):/home/bridge $(BRIDGE_IMAGE)

# Print the Bridge-generated SMTP credentials (IMAP/SMTP user + app password)
bridge-creds:
	docker exec $(BRIDGE_CONTAINER) bridge --cli info

# Fail the build if recipient/invoice/credential data would enter the repo
check-no-pii:
	@if git ls-files | grep -E '(^|/)(data|invoices|\.work|out|\.bridge-data)/|(^|/)leden.*\.csv$$|credentials'; then \
		echo 'ERROR: PII or credential files are tracked in the repo'; exit 1; \
	else echo 'OK: no PII or credential files tracked'; fi

clean:
	rm -rf $(WORK_DIR) $(OUT_DIR) .pytest_cache .ruff_cache
