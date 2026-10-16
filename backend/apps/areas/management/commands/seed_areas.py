from django.core.management.base import BaseCommand
from django.db import transaction

from apps.areas.models import Area, AreaCompatibility

# Placeholder data from the business doc examples; replace with the launch city's real areas (Sprint 0).
AREAS = ['المحطة', 'الأربعين', 'المعلمين']
# (origin, driver destination, request destination): destination lies on the driver's way.
COMPATIBILITY = [('المحطة', 'الأربعين', 'المعلمين')]


class Command(BaseCommand):
    help = 'Seed areas and compatibility rules (idempotent).'

    @transaction.atomic
    def handle(self, *args, **options):
        areas = {name: Area.all_objects.get_or_create(name=name)[0] for name in AREAS}
        for origin, driver_dest, request_dest in COMPATIBILITY:
            AreaCompatibility.all_objects.get_or_create(
                origin=areas[origin], driver_destination=areas[driver_dest], request_destination=areas[request_dest]
            )
        self.stdout.write(self.style.SUCCESS(f'{len(areas)} areas, {len(COMPATIBILITY)} compatibility rules.'))
