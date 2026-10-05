#!/usr/bin/env bash
# End-to-end run: regenerate the date-relative sample files, start the stack with the stand-in
# contract extractor and assistant model (no AI calls, no cost), run Playwright, then remove the
# test contracts and switch both services back to Claude. Extra arguments go to Playwright, e.g.:
#   scripts/e2e.sh                         # everything
#   scripts/e2e.sh npx playwright test contracts
set -euo pipefail
cd "$(dirname "$0")/.."

# This run recreates the gateway WITHOUT its access password, which would open a public tunnel
# (PLT-003). Stop the tunnel first (Ctrl+C in the terminal running scripts/tunnel.sh).
if ps -eo comm= | grep -qx cloudflared; then  # not pgrep: it misses processes under WSL
  echo "ABORT: a Cloudflare tunnel is running. e2e.sh would open it without a password." >&2
  echo "Stop the tunnel (scripts/tunnel.sh) and run this again." >&2
  exit 1
fi

# Exported for EVERY compose command below: `compose run` re-checks the services the tests depend
# on and would otherwise recreate contract-service with the default (real) extractor.
export CONTRACT_EXTRACTOR=fake
export ASSISTANT_LLM=fake
# Reminder emails (INV-004) must land in the local Mailpit inbox, never reach a real client.
export SMTP_HOST=mailpit SMTP_PORT=1025 SMTP_USERNAME= SMTP_PASSWORD= SMTP_STARTTLS=false
# The tests open the app without a login. The password from .env is put back by cleanup.
export ACCESS_USERNAME=user ACCESS_PASSWORD=

cleanup() {
  echo "Removing e2e test contracts…"
  paths=$(docker compose exec -T db sh -c \
    'psql -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DELETE FROM contracts.contracts WHERE file_name LIKE '"'"'e2e-%'"'"' RETURNING stored_path"' || true)
  if [[ -n "$paths" ]]; then
    # shellcheck disable=SC2086
    docker compose exec -T contract-service rm -f $paths || true
  fi
  echo "Removing e2e test reminders (sample customers only: reserved .example addresses)…"
  docker compose exec -T db sh -c     'psql -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DELETE FROM invoices.invoice_reminders WHERE recipient LIKE '"'"'%.example'"'"'"' >/dev/null || true
  echo "Switching contract reading and Talk to Me back to Claude, and the mail server back to your .env…"
  echo "Putting the access password from your .env back on the gateway…"
  env -u SMTP_HOST -u SMTP_PORT -u SMTP_USERNAME -u SMTP_PASSWORD -u SMTP_STARTTLS \
    -u ACCESS_USERNAME -u ACCESS_PASSWORD \
    docker compose up -d --wait invoice-service gateway >/dev/null 2>&1 || true
  CONTRACT_EXTRACTOR=claude ASSISTANT_LLM=claude \
    docker compose up -d --wait contract-service assistant-service >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Regenerating samples…"
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/work -w /work python:3.12-slim \
  sh -c "pip install -q --disable-pip-version-check --target /tmp/py openpyxl python-docx \
         && PYTHONPATH=/tmp/py python scripts/make_samples.py" >/dev/null

echo "Starting stack (stand-in contract extractor and assistant model)…"
docker compose up -d --build --wait >/dev/null

# Safety: never let an e2e run send test documents or questions to the real (paid) AI.
active=$(docker compose exec -T contract-service printenv CONTRACT_EXTRACTOR)
if [[ "$active" != "fake" ]]; then
  echo "ABORT: contract-service is using the '$active' extractor, not the stand-in." >&2
  exit 1
fi
active=$(docker compose exec -T assistant-service printenv ASSISTANT_LLM)
if [[ "$active" != "fake" ]]; then
  echo "ABORT: assistant-service is using the '$active' model, not the stand-in." >&2
  exit 1
fi

# Safety: never let an e2e run send reminder emails anywhere but the local Mailpit inbox.
active=$(docker compose exec -T invoice-service printenv SMTP_HOST)
if [[ "$active" != "mailpit" ]]; then
  echo "ABORT: invoice-service would send email to '$active', not the local Mailpit inbox." >&2
  exit 1
fi

echo "Running Playwright…"
if [[ $# -gt 0 ]]; then
  docker compose --profile e2e run --rm --no-deps -T e2e "$@"
else
  docker compose --profile e2e run --rm --no-deps -T e2e
fi
