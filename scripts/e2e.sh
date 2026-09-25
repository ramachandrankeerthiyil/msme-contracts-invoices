#!/usr/bin/env bash
# End-to-end run: regenerate the date-relative sample files, start the stack with the stand-in
# contract extractor (no AI calls, no cost), run Playwright, then remove the test contracts and
# switch the contract service back to Claude. Extra arguments go to Playwright, e.g.:
#   scripts/e2e.sh                         # everything
#   scripts/e2e.sh npx playwright test contracts
set -euo pipefail
cd "$(dirname "$0")/.."

# Exported for EVERY compose command below: `compose run` re-checks the services the tests depend
# on and would otherwise recreate contract-service with the default (real) extractor.
export CONTRACT_EXTRACTOR=fake

cleanup() {
  echo "Removing e2e test contracts…"
  paths=$(docker compose exec -T db sh -c \
    'psql -qAt -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "DELETE FROM contracts.contracts WHERE file_name LIKE '"'"'e2e-%'"'"' RETURNING stored_path"' || true)
  if [[ -n "$paths" ]]; then
    # shellcheck disable=SC2086
    docker compose exec -T contract-service rm -f $paths || true
  fi
  echo "Switching contract reading back to Claude…"
  CONTRACT_EXTRACTOR=claude docker compose up -d --wait contract-service >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Regenerating samples…"
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/work -w /work python:3.12-slim \
  sh -c "pip install -q --disable-pip-version-check --target /tmp/py openpyxl python-docx \
         && PYTHONPATH=/tmp/py python scripts/make_samples.py" >/dev/null

echo "Starting stack (stand-in contract extractor)…"
docker compose up -d --build --wait >/dev/null

# Safety: never let an e2e run send test documents to the real (paid) AI.
active=$(docker compose exec -T contract-service printenv CONTRACT_EXTRACTOR)
if [[ "$active" != "fake" ]]; then
  echo "ABORT: contract-service is using the '$active' extractor, not the stand-in." >&2
  exit 1
fi

echo "Running Playwright…"
if [[ $# -gt 0 ]]; then
  docker compose --profile e2e run --rm --no-deps -T e2e "$@"
else
  docker compose --profile e2e run --rm --no-deps -T e2e
fi
