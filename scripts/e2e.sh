#!/usr/bin/env bash
# End-to-end run: regenerate the date-relative sample files, (re)build and start the stack,
# then run Playwright against it. Extra arguments go to Playwright, e.g.:
#   scripts/e2e.sh                         # everything
#   scripts/e2e.sh npx playwright test invoice-dashboard
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Regenerating samples…"
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD":/work -w /work python:3.12-slim \
  sh -c "pip install -q --disable-pip-version-check --target /tmp/py openpyxl python-docx \
         && PYTHONPATH=/tmp/py python scripts/make_samples.py" >/dev/null

echo "Starting stack…"
docker compose up -d --build --wait >/dev/null

echo "Running Playwright…"
if [[ $# -gt 0 ]]; then
  docker compose --profile e2e run --rm -T e2e "$@"
else
  docker compose --profile e2e run --rm -T e2e
fi
