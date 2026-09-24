#!/usr/bin/env bash
# PLT-002 smoke test: brings the stack up and checks request-ID propagation end to end,
# health of every service, and (with --observability) that Prometheus scrapes both services.
#
#   scripts/smoke.sh                 # core stack
#   scripts/smoke.sh --observability # also Prometheus + Grafana
set -euo pipefail
cd "$(dirname "$0")/.."

GATEWAY=http://localhost:8080
PROFILE_ARGS=()
if [[ "${1:-}" == "--observability" ]]; then
  PROFILE_ARGS=(--profile observability)
fi

pass() { printf '  \033[32m✔\033[0m %s\n' "$1"; }
fail() { printf '  \033[31m✘\033[0m %s\n' "$1"; exit 1; }

echo "Starting stack…"
docker compose "${PROFILE_ARGS[@]}" up -d --build --wait

echo "Checks:"
curl -fsS "$GATEWAY/healthz" >/dev/null && pass "gateway /healthz" || fail "gateway /healthz"

for svc in invoices contracts; do
  rid="smoke-${svc}-$RANDOM$RANDOM"
  headers=$(curl -fsS -D - -o /dev/null -H "X-Request-ID: $rid" "$GATEWAY/api/$svc/openapi.json") \
    || fail "GET /api/$svc/openapi.json through gateway"
  echo "$headers" | grep -qi "^x-request-id: $rid" \
    && pass "/api/$svc: request ID echoed" || fail "/api/$svc: request ID not echoed"
  sleep 1
  docker compose logs --no-log-prefix "${svc%s}-service" 2>/dev/null | grep -q "\"request_id\": \"$rid\"" \
    && pass "/api/$svc: request ID found in service logs" \
    || fail "/api/$svc: request ID missing from service logs"
done

bad_headers=$(curl -sS -D - -o /dev/null -H 'X-Request-ID: bad id' "$GATEWAY/api/invoices/openapi.json")
echo "$bad_headers" | grep -i '^x-request-id:' | grep -qv 'bad id' \
  && pass "malformed request ID replaced" || fail "malformed request ID was not replaced"

status=$(curl -s -o /dev/null -w '%{http_code}' "$GATEWAY/api/unknown/thing")
[[ "$status" == "404" ]] && pass "unknown API path → 404 JSON" || fail "unknown API path returned $status"

for svc in invoice-service contract-service; do
  state=$(docker compose ps --format '{{.Health}}' "$svc")
  [[ "$state" == "healthy" ]] && pass "$svc healthy" || fail "$svc is $state"
done

if [[ ${#PROFILE_ARGS[@]} -gt 0 ]]; then
  echo "Waiting for the first Prometheus scrape…"
  sleep 20
  targets=$(curl -fsS http://localhost:9090/api/v1/targets)
  up=$(echo "$targets" | grep -o '"health":"up"' | wc -l)
  [[ "$up" -ge 2 ]] && pass "Prometheus scraping both services" || fail "Prometheus targets up: $up/2"
  grafana_port=$(docker compose port grafana 3000 | cut -d: -f2)
  curl -fsS "http://localhost:$grafana_port/api/health" | grep -q '"database": *"ok"' \
    && pass "Grafana up (http://localhost:$grafana_port)" || fail "Grafana not responding"
fi

echo "Smoke test passed."
