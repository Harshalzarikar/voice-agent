#!/bin/bash
echo "Running Database Migrations..."
python backend_core/manage.py migrate

# Optional: Create superuser if needed (you might want to script this safely later)
# python backend_core/manage.py createsuperuser --noinput ...

echo "Starting Supervisord..."
/usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
