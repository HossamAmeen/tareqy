from django.core.management import call_command
from django.urls import reverse

from apps.areas.models import Area, AreaCompatibility


def test_area_list_requires_auth(api_client):
    assert api_client.get(reverse('area-list')).status_code == 401


def test_area_list_returns_only_active_areas(auth_client, customer, areas):
    Area.objects.filter(name='معلمين').update(is_active=False)
    body = auth_client(customer).get(reverse('area-list')).json()
    names = (
        {a['name'] for a in body['results'] if 'results' in body} if 'results' in body else {a['name'] for a in body}
    )
    assert names == {'محطة', 'أربعين'}


def test_seed_areas_is_idempotent(db):
    call_command('seed_areas')
    call_command('seed_areas')
    assert Area.objects.count() == 3
    assert AreaCompatibility.objects.count() == 1
