from datetime import timedelta

from django.core.management import call_command
from django.utils import timezone

from apps.trips.tasks import expire_requests


def test_expire_task_runs_inline_when_celery_disabled(make_request):
    req = make_request(expires_at=timezone.now() - timedelta(minutes=1))
    assert expire_requests.delay().get() == 1
    req.refresh_from_db()
    assert req.status == 'EXPIRED'


def test_expire_management_command(make_request, capsys):
    make_request(expires_at=timezone.now() - timedelta(minutes=1))
    call_command('expire_requests')
    assert 'Expired 1' in capsys.readouterr().out
