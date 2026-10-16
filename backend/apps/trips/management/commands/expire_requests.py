from django.core.management.base import BaseCommand

from apps.trips.services import expire_due_requests


class Command(BaseCommand):
    help = 'Mark open trip requests past their expiry as EXPIRED (use from cron when Celery is disabled).'

    def handle(self, *args, **options):
        self.stdout.write(f'Expired {expire_due_requests()} request(s).')
