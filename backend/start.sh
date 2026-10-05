#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# Free hosts have no shell, so the first admin user can be created from environment variables.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput --email "${DJANGO_SUPERUSER_EMAIL:-admin@example.com}" 2>/dev/null \
    || echo "Admin user already exists."
fi

exec gunicorn config.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 2
