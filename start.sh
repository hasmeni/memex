#!/usr/bin/env bash
# ironyLabs Links — start.sh
# Usage: ./start.sh
# Override defaults: ADMIN_PASSWORD=mypass SECRET_KEY=mykey ./start.sh

set -e

# Source .env file if it exists (docker compose also reads it, but we need
# the vars available in this shell for the status message below)
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

export ADMIN_PASSWORD="${ADMIN_PASSWORD:-ironyLabs2024!}"
export SECRET_KEY="${SECRET_KEY:-supersecretkey_change_me}"

echo "ironyLabs Links — starting..."
docker compose up -d --build

echo ""
echo "✓ Running at http://localhost:8098"
echo "✓ Admin panel: http://localhost:8098/admin.html"
echo "  Admin username: admin"
echo "  Admin password: (set in .env)"
