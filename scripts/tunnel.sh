#!/usr/bin/env bash
# Puts the app on a public Cloudflare address (PLT-003). Starts a "quick tunnel" to the gateway
# and prints a https://<random>.trycloudflare.com address. It refuses to start unless the gateway
# is asking for a password, because the app has no user accounts of its own.
#   scripts/tunnel.sh        # Ctrl+C stops it; the address stops working then
set -euo pipefail
cd "$(dirname "$0")/.."

GATEWAY=${GATEWAY:-http://localhost:8080}

cloudflared=$(command -v cloudflared || true)
if [[ -z "$cloudflared" && -x "$HOME/bin/cloudflared" ]]; then cloudflared="$HOME/bin/cloudflared"; fi
if [[ -z "$cloudflared" ]]; then
  echo "cloudflared is not installed. Get it from https://github.com/cloudflare/cloudflared/releases" >&2
  echo "(for Linux x86-64, save cloudflared-linux-amd64 as ~/bin/cloudflared and make it executable)." >&2
  exit 1
fi

status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "$GATEWAY/" || true)
case "$status" in
  401) ;;
  000|"")
    echo "ABORT: nothing is answering at $GATEWAY. Start the app first: docker compose up -d" >&2
    exit 1 ;;
  *)
    echo "ABORT: the gateway at $GATEWAY is not asking for a password (it answered $status)." >&2
    echo "Set ACCESS_PASSWORD (12+ characters) in .env, then run: docker compose up -d gateway" >&2
    echo "Nothing was exposed." >&2
    exit 1 ;;
esac

echo "The gateway asks for a password. Starting the tunnel."
echo "Share the https://….trycloudflare.com address below with the user name and password from .env"
echo "(ACCESS_USERNAME / ACCESS_PASSWORD). Press Ctrl+C to stop; the address stops working then."
echo
exec "$cloudflared" tunnel --no-autoupdate --url "$GATEWAY"
