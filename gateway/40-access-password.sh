#!/bin/sh
# Optional shared password for the whole gateway (PLT-003). Runs before Nginx starts.
# With ACCESS_PASSWORD empty the gateway stays open, exactly as before.
set -eu

user="${ACCESS_USERNAME:-user}"

if [ -z "${ACCESS_PASSWORD:-}" ]; then
  echo "access: ACCESS_PASSWORD is not set, so the gateway asks for no password"
  exit 0
fi

case "$user" in
  *[[:space:]:]*)
    echo "ACCESS_USERNAME must not contain a colon or whitespace." >&2
    exit 1
    ;;
esac

if [ "${#ACCESS_PASSWORD}" -lt 12 ]; then
  echo "ACCESS_PASSWORD must be at least 12 characters long. A weak password on a public" \
    "address is worse than none; use a long random one." >&2
  exit 1
fi

# bcrypt hash only; the password itself is never written anywhere.
htpasswd -nbB "$user" "$ACCESS_PASSWORD" > /etc/nginx/htpasswd
chown nginx:nginx /etc/nginx/htpasswd
chmod 600 /etc/nginx/htpasswd

cat > /etc/nginx/access.conf <<'EOF'
auth_basic "MSME Contracts & Invoices";
auth_basic_user_file /etc/nginx/htpasswd;
EOF

echo "access: the gateway now asks for a password (user name: $user)"
