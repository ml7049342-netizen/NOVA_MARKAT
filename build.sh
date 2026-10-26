#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py check --deploy --fail-level WARNING
python manage.py collectstatic --noinput

# Apply only reviewed, version-controlled migrations. Never generate schema changes during deploy.
python manage.py migrate --noinput
