from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.areas.models import Area

STAFF_PHONE = '+201999000001'
# Coordinates let a driver's browser location resolve to an area (matching is area based).
COORDINATES = {
    'المحطة': ('30.000000', '32.000000'),
    'الأربعين': ('30.050000', '32.050000'),
    'المعلمين': ('30.100000', '32.100000'),
}


class Command(BaseCommand):
    help = 'Seed areas (with coordinates) and a staff user for the browser e2e tests.'

    def handle(self, *args, **options):
        call_command('seed_areas')
        for name, (lat, lng) in COORDINATES.items():
            Area.objects.filter(name=name).update(latitude=lat, longitude=lng)
        staff, _ = User.objects.get_or_create(phone=STAFF_PHONE, defaults={'name': 'Staff', 'is_staff': True})
        staff.is_staff = True
        staff.save()
        self.stdout.write(self.style.SUCCESS(f'Seeded areas and staff {STAFF_PHONE}.'))
