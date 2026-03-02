#!/bin/sh
set -eu

wait_for_host_port() {
  host="$1"
  port="$2"
  name="$3"

  echo "Waiting for ${name} at ${host}:${port}..."
  while ! python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('${host}', int('${port}'))); s.close()" 2>/dev/null; do
    sleep 1
  done
  echo "${name} is available"
}

wait_for_host_port "${POSTGRES_HOST:-db}" "${POSTGRES_PORT:-5432}" "PostgreSQL"
wait_for_host_port "redis" "6379" "Redis"

mode="${1:-web}"

if [ "$mode" = "web" ]; then
  exec python manage.py runserver 0.0.0.0:8000
elif [ "$mode" = "celery" ]; then
  exec celery -A core worker -l info
elif [ "$mode" = "beat" ]; then
  exec celery -A core beat -l info
else
  exec "$@"
fi
