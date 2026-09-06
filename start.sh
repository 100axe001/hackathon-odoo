#!/usr/bin/env bash
#
# Start everything: Postgres, the API, and the frontend.
#
#   ./start.sh              start on the demo seed if the database is empty
#   ./start.sh --reset      drop, recreate and reseed first (the demo data)
#   ./start.sh --large      load the 793-row stress dataset instead
#   ./start.sh --stop       stop the API and frontend, leave Postgres running
#
# Logs go to .run/, and Ctrl-C stops both servers.

set -euo pipefail
cd "$(dirname "$0")"

BACKEND_PORT=8000
FRONTEND_PORT=3000
PY=backend/.venv/bin/python
RUN=.run

green() { printf '\033[32m%s\033[0m\n' "$1"; }
warn()  { printf '\033[33m%s\033[0m\n' "$1"; }
die()   { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

stop_servers() {
  pkill -f "uvicorn main:app" 2>/dev/null || true
  pkill -f "vite.*$FRONTEND_PORT" 2>/dev/null || true
}

if [[ "${1:-}" == "--stop" ]]; then
  stop_servers
  green "Stopped. Postgres is still up — 'docker compose down' if you want it gone too."
  exit 0
fi

[[ -x "$PY" ]] || die "No virtualenv at $PY. Run: cd backend && python -m venv .venv && ./.venv/bin/python -m pip install -r requirements.txt"
[[ -d frontend/node_modules ]] || die "Frontend dependencies missing. Run: cd frontend && npm install"

mkdir -p "$RUN"

# --- Postgres -------------------------------------------------------------
green "Starting Postgres…"
docker compose up -d >/dev/null

# Wait for it rather than sleeping a fixed guess: on a cold start the container
# accepts connections several seconds after docker returns.
for _ in $(seq 1 30); do
  docker compose exec -T db pg_isready -U dealflow >/dev/null 2>&1 && break
  sleep 1
done
docker compose exec -T db pg_isready -U dealflow >/dev/null 2>&1 \
  || die "Postgres did not come up. Check: docker compose logs db"

# --- Data -----------------------------------------------------------------
case "${1:-}" in
  --reset) green "Reseeding the demo data…"; (cd backend && ../$PY reset_db.py >/dev/null) ;;
  --large) green "Loading the large dataset…"; (cd backend && ../$PY seed_large.py >/dev/null) ;;
  "")
    # Only seed an empty database. Reseeding silently would destroy whatever the
    # last session was in the middle of.
    rows=$(cd backend && ../$PY -c "
from app.database.connection import engine
from sqlalchemy import text
try:
    with engine.connect() as c:
        print(c.execute(text('select count(*) from users')).scalar())
except Exception:
    print(0)
" 2>/dev/null || echo 0)
    if [[ "$rows" == "0" ]]; then
      green "Empty database — seeding the demo data…"
      (cd backend && ../$PY reset_db.py >/dev/null)
    else
      warn "Database already has $rows user(s) — leaving it alone. Use --reset to reseed."
    fi
    ;;
  *) die "Unknown option: $1" ;;
esac

# --- Servers --------------------------------------------------------------
stop_servers
sleep 1

green "Starting the API…"
(cd backend && exec ../$PY -m uvicorn main:app --port "$BACKEND_PORT" --reload) > "$RUN/api.log" 2>&1 &
API_PID=$!

for _ in $(seq 1 40); do
  curl -sf "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf "http://localhost:$BACKEND_PORT/health" >/dev/null 2>&1 \
  || { cat "$RUN/api.log" | tail -20; die "API failed to start — log above."; }

green "Starting the frontend…"
(cd frontend && exec npm run dev -- --port "$FRONTEND_PORT" --strictPort) > "$RUN/web.log" 2>&1 &
WEB_PID=$!

for _ in $(seq 1 40); do
  curl -sf "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 && break
  sleep 0.5
done
curl -sf "http://localhost:$FRONTEND_PORT" >/dev/null 2>&1 \
  || { tail -20 "$RUN/web.log"; die "Frontend failed to start — log above."; }

# Read the accounts out of the database rather than printing a fixed list:
# the large dataset has entirely different people, and a banner naming accounts
# that do not exist is worse than none.
ACCOUNTS=$(cd backend && ../$PY -c "
from app.database.connection import SessionLocal
import app.models
from sqlalchemy import text
order = {'SALES_REP': 0, 'SALES_MANAGER': 1, 'FINANCE': 2, 'ADMIN': 3, 'CUSTOMER': 4}
rows = SessionLocal().execute(text('select email, role, full_name from users')).all()
seen, out = set(), []
for email, role, name in sorted(rows, key=lambda r: (order.get(r[1], 9), r[0])):
    if role in seen:
        continue
    seen.add(role)
    out.append(f'    {email:<38} {role.replace(chr(95), chr(32)).title()} — {name}')
print(chr(10).join(out))
" 2>/dev/null || echo "    (could not read accounts — see backend/seed.py)")

cat <<EOF

$(green "DealFlow360 is running.")

  App        http://localhost:$FRONTEND_PORT
  API docs   http://localhost:$BACKEND_PORT/docs

  Sign in with any of these — password is dealflow123

$ACCOUNTS

  Logs   $RUN/api.log   $RUN/web.log
  Stop   Ctrl-C, or ./start.sh --stop

EOF

trap 'echo; green "Stopping…"; kill $API_PID $WEB_PID 2>/dev/null || true; stop_servers; exit 0' INT TERM
wait
