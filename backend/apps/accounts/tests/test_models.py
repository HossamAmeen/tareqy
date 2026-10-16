import pytest
from django.db import IntegrityError

from apps.accounts.models import User


def test_create_user_without_password_has_unusable_password(make_user):
    user = make_user()
    assert not user.has_usable_password()
    assert user.is_customer and not user.is_driver


def test_create_superuser(db):
    admin = User.objects.create_superuser(phone='+201099999999', password='pw12345678')
    assert admin.is_staff and admin.is_superuser


def test_phone_is_unique(make_user):
    make_user(phone='+201011111111')
    with pytest.raises(IntegrityError):
        make_user(phone='+201011111111')


def test_create_user_requires_phone(db):
    with pytest.raises(ValueError):
        User.objects.create_user(phone='')


def test_suspended_user_is_not_active(make_user):
    user = make_user(account_status=User.AccountStatus.SUSPENDED)
    assert user.is_active is False


def test_soft_delete_and_restore_use_managers(make_user):
    user = make_user()
    user.soft_delete()
    assert not User.objects.filter(pk=user.pk).exists()
    assert User.deleted_objects.filter(pk=user.pk).exists()
    assert User.all_objects.filter(pk=user.pk).exists()
    assert user.is_active is False

    user.restore()
    assert User.objects.filter(pk=user.pk).exists()
    assert user.is_active is True
