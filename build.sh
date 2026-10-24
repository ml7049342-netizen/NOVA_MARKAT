#!/usr/bin/env bash
set -euo pipefail

python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py check --deploy --fail-level WARNING
python manage.py collectstatic --noinput

# The repository currently has no checked-in initial migration for store.
# Keep this bootstrap until a generated and reviewed initial migration is committed.
python manage.py makemigrations store --noinput
python manage.py migrate --noinput
