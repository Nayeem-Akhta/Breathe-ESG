#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py shell -c "
from core.models import User, Organization
if not User.objects.filter(username='admin').exists():
    org, _ = Organization.objects.get_or_create(name='Test Company', slug='test-company')
    user = User.objects.create_superuser('admin3', 'admin@breatheesg.com', 'Admin@123')
    user.organization = org
    user.save()
    print('Superuser and organization created')
else:
    print('Superuser already exists')
"