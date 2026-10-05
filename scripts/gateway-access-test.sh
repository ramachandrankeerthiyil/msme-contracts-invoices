#!/usr/bin/env bash
# PLT-003: tests the gateway's optional access password with real HTTP against the gateway image.
# The gateway starts without its upstream services (it resolves them per request), so no stack is
# needed and nothing here touches your running app. Each check prints the acceptance criterion.
#   scripts/gateway-access-test.sh
set -uo pipefail
cd "$(dirname "$0")/.."

IMAGE=msme-gateway-access-test
PORT=${GATE_TEST_PORT:-18080}
URL="http://127.0.0.1:$PORT"
USER_NAME=owner
SECRET='correct horse battery staple'
GOOD="$USER_NAME:$SECRET"
failed=0

pass() { printf '  ok    %s\n' "$1"; }
fail() { printf '  FAIL  %s\n' "$1"; failed=1; }
expect() { # expect "<AC> description" "<actual>" "<expected>"
  if [[ "$2" == "$3" ]]; then pass "$1"; else fail "$1 (got '$2', wanted '$3')"; fi
}
expect_not() { # expect_not "<AC> description" "<actual>" "<unwanted>"
  if [[ "$2" != "$3" ]]; then pass "$1"; else fail "$1 (got the unwanted '$2')"; fi
}
code() { curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$@"; }

cleanup() { docker rm -f gate-test >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

start() { # start <docker run args...>; waits until /healthz answers
  docker run -d --name gate-test -p "127.0.0.1:$PORT:80" "$@" "$IMAGE" >/dev/null
  for _ in $(seq 1 40); do
    [[ "$(code "$URL/healthz")" == "200" ]] && return 0
    sleep 0.25
  done
  echo "gateway did not start:"; docker logs gate-test 2>&1 | tail -5; return 1
}

echo "Building the gateway image…"
docker build -q -t "$IMAGE" ./gateway >/dev/null || { echo "build failed"; exit 1; }

echo "No password set"
start || exit 1
expect_not "PLT-003-AC2 / is not asked for a password"            "$(code "$URL/")" 401
expect_not "PLT-003-AC2 /api/invoices is not asked for a password" "$(code "$URL/api/invoices")" 401
expect     "PLT-003-AC5 /healthz is open"                          "$(code "$URL/healthz")" 200
cleanup

echo "Password set"
start -e ACCESS_USERNAME="$USER_NAME" -e ACCESS_PASSWORD="$SECRET" || exit 1
expect "PLT-003-AC1 / without a login is refused"                 "$(code "$URL/")" 401
expect "PLT-003-AC1 /api/invoices without a login is refused"     "$(code "$URL/api/invoices")" 401
expect "PLT-003-AC1 /api/assistant/chat without a login is refused" \
  "$(code -X POST -H 'Content-Type: application/json' -d '{}' "$URL/api/assistant/chat")" 401
expect "PLT-003-AC1 a wrong password is refused"                  "$(code -u "$USER_NAME:nope-nope-nope" "$URL/")" 401
expect "PLT-003-AC1 a wrong user name is refused"                 "$(code -u "intruder:$SECRET" "$URL/")" 401
challenge=$(curl -s -D - -o /dev/null "$URL/" | tr -d '\r' | grep -i '^www-authenticate:' || true)
[[ "$challenge" == *"Basic realm="* ]] \
  && pass "PLT-003-AC1 the refusal carries a WWW-Authenticate: Basic challenge" \
  || fail "PLT-003-AC1 no Basic challenge (got '$challenge')"
expect_not "PLT-003-AC1 the right login gets through to the app (not 401)" "$(code -u "$GOOD" "$URL/")" 401
expect_not "PLT-003-AC1 the right login reaches the API (not 401)" "$(code -u "$GOOD" "$URL/api/invoices")" 401
expect "PLT-003-AC1 unauthenticated callers get 401, not a 503 that reveals the stack" \
  "$(code "$URL/api/contracts")" 401
expect "PLT-003-AC5 /healthz stays open without a login"          "$(code "$URL/healthz")" 200
expect "PLT-003-AC5 /healthz stays open with a login"             "$(code -u "$GOOD" "$URL/healthz")" 200

hash_line=$(docker exec gate-test cat /etc/nginx/htpasswd)
[[ "$hash_line" == "$USER_NAME:\$2y\$"* ]] \
  && pass "PLT-003-AC4 only a bcrypt hash is stored" || fail "PLT-003-AC4 unexpected hash file"
[[ "$hash_line" != *"$SECRET"* ]] \
  && pass "PLT-003-AC4 the hash file does not contain the password" \
  || fail "PLT-003-AC4 the password is in the hash file"
b64=$(printf '%s' "$GOOD" | base64)
logs=$(docker logs gate-test 2>&1)
[[ "$logs" != *"$SECRET"* && "$logs" != *"$b64"* ]] \
  && pass "PLT-003-AC4 the password is not in the container logs" \
  || fail "PLT-003-AC4 the password or its encoding is in the container logs"
access_lines=$(grep '"event":"http.access"' <<<"$logs" || true)
[[ -n "$access_lines" && "$access_lines" != *"$USER_NAME"* && "$access_lines" != *"$b64"* ]] \
  && pass "PLT-003-AC4 access log lines hold no login or user name" \
  || fail "PLT-003-AC4 access log lines are missing or contain the login"
history=$(docker history --no-trunc "$IMAGE")
[[ "$history" != *"$SECRET"* ]] \
  && pass "PLT-003-AC4 the password is not in the image layers" || fail "PLT-003-AC4 password in image"
cleanup

echo "Bad configuration"
refuses() { # refuses "<description>" <env args...>: the container must stop with a message
  local what=$1; shift
  local out rc
  out=$(docker run --rm "$@" "$IMAGE" 2>&1); rc=$?
  if [[ $rc -ne 0 && "$out" == *"must"* ]]; then pass "$what"; else fail "$what (exit $rc: $out)"; fi
}
refuses "PLT-003-AC3 an 11-character password is refused at start" -e ACCESS_PASSWORD=elevenchars
refuses "PLT-003-AC3 a user name with a colon is refused at start" \
  -e ACCESS_USERNAME=a:b -e ACCESS_PASSWORD=long-enough-password
refuses "PLT-003-AC3 a user name with a space is refused at start" \
  -e "ACCESS_USERNAME=a b" -e ACCESS_PASSWORD=long-enough-password
start -e ACCESS_PASSWORD=exactly12chr || exit 1
expect "PLT-003-AC3 a 12-character password is accepted"          "$(code -u "user:exactly12chr" "$URL/healthz")" 200
expect "PLT-003-AC3 ...and enforced (default user name is 'user')" "$(code "$URL/")" 401
cleanup

echo
if [[ $failed -eq 0 ]]; then echo "All gateway access checks passed."; else echo "Some checks failed."; fi
exit $failed
