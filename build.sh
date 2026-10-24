#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py check --deploy --fail-level WARNING
python manage.py collectstatic --noinput

# Migrations are version-controlled; deployments apply reviewed migrations only.
python manage.py migrate --noinput
