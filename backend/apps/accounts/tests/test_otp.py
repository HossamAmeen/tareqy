import re
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import OTPCode, User

PHONE = '+201012345678'


def _code(outbox):
    return re.search(r'(\d{6})', outbox[-1][1]).group(1)


@pytest.fixture
def request_url():
    return reverse('otp-request')


@pytest.fixture
def verify_url():
    return reverse('otp-verify')


@pytest.mark.django_db
def test_request_otp_sends_sms_and_stores_only_hash(api_client, request_url, sms_outbox):
    response = api_client.post(request_url, {'phone': PHONE})
    assert response.status_code == 200
    code = _code(sms_outbox)
    assert sms_outbox[-1][0] == PHONE
    assert OTPCode.objects.get(phone=PHONE).code_hash != code


@pytest.mark.django_db
def test_request_otp_rejects_invalid_phone(api_client, request_url):
    response = api_client.post(request_url, {'phone': 'abc'})
    assert response.status_code == 400
    assert 'phone' in response.json()['errors']


@pytest.mark.django_db
def test_request_otp_enforces_resend_cooldown(api_client, request_url):
    assert api_client.post(request_url, {'phone': PHONE}).status_code == 200
    assert api_client.post(request_url, {'phone': PHONE}).status_code == 400


@pytest.mark.django_db
def test_verify_otp_creates_user_and_returns_tokens(api_client, request_url, verify_url, sms_outbox):
    api_client.post(request_url, {'phone': PHONE})
    response = api_client.post(verify_url, {'phone': PHONE, 'code': _code(sms_outbox)})
    assert response.status_code == 200
    data = response.json()['data']
    assert {'access', 'refresh'} <= data.keys()
    assert data['user']['phone'] == PHONE
    assert User.objects.filter(phone=PHONE).exists()


@pytest.mark.django_db
def test_verify_otp_logs_in_existing_user_without_duplicating(
    api_client, request_url, verify_url, sms_outbox, make_user
):
    existing = make_user(phone=PHONE)
    api_client.post(request_url, {'phone': PHONE})
    response = api_client.post(verify_url, {'phone': PHONE, 'code': _code(sms_outbox)})
    assert response.json()['data']['user']['id'] == existing.id
    assert User.objects.filter(phone=PHONE).count() == 1


@pytest.mark.django_db
def test_verify_otp_code_is_single_use(api_client, request_url, verify_url, sms_outbox):
    api_client.post(request_url, {'phone': PHONE})
    code = _code(sms_outbox)
    assert api_client.post(verify_url, {'phone': PHONE, 'code': code}).status_code == 200
    assert api_client.post(verify_url, {'phone': PHONE, 'code': code}).status_code == 400


@pytest.mark.django_db
def test_verify_otp_wrong_code_counts_attempts_then_locks(api_client, request_url, verify_url, sms_outbox, settings):
    settings.OTP_MAX_ATTEMPTS = 2
    api_client.post(request_url, {'phone': PHONE})
    real = _code(sms_outbox)
    wrong = '000000' if real != '000000' else '111111'
    assert api_client.post(verify_url, {'phone': PHONE, 'code': wrong}).status_code == 400
    assert api_client.post(verify_url, {'phone': PHONE, 'code': wrong}).status_code == 400
    # locked: even the right code is refused now
    assert api_client.post(verify_url, {'phone': PHONE, 'code': real}).status_code == 400


@pytest.mark.django_db
def test_verify_otp_rejects_expired_code(api_client, request_url, verify_url, sms_outbox):
    api_client.post(request_url, {'phone': PHONE})
    OTPCode.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert api_client.post(verify_url, {'phone': PHONE, 'code': _code(sms_outbox)}).status_code == 400


@pytest.mark.django_db
def test_verify_otp_rejects_suspended_account(api_client, request_url, verify_url, sms_outbox, make_user):
    make_user(phone=PHONE, account_status=User.AccountStatus.SUSPENDED)
    api_client.post(request_url, {'phone': PHONE})
    assert api_client.post(verify_url, {'phone': PHONE, 'code': _code(sms_outbox)}).status_code == 400


@pytest.mark.django_db
def test_otp_access_token_authenticates_me(api_client, request_url, verify_url, sms_outbox):
    api_client.post(request_url, {'phone': PHONE})
    token = api_client.post(verify_url, {'phone': PHONE, 'code': _code(sms_outbox)}).json()['data']['access']
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
    assert api_client.get(reverse('me')).json()['data']['phone'] == PHONE
