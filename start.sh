#!/usr/bin/env bash
set -euo pipefail

python -m flask --app app init-db
exec gunicorn --bind 0.0.0.0:${PORT:-10000} app:app
