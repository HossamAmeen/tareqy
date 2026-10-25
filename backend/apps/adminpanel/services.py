from django.db import transaction
from django.utils import timezone

from apps.accounts.models import DriverProfile, User
from apps.reports.models import Report
from apps.trips.services import record_status_event
from common.exceptions import BusinessRuleError, ConflictError

REPORT_OUTCOMES = (Report.Status.REVIEWING, Report.Status.RESOLVED, Report.Status.DISMISSED)


@transaction.atomic
def set_account_status(user, status, actor):
    """Suspend or re-activate an account. Staff cannot lock themselves out or touch other staff."""
    user = User.objects.select_for_update().get(pk=user.pk)
    if user.pk == actor.pk:
        raise BusinessRuleError('You cannot change your own account status.')
    if user.is_staff and not actor.is_superuser:
        raise BusinessRuleError('Only a superuser can change a staff account.')
    if user.account_status != status:
        previous = user.account_status
        user.account_status = status
        user.save(update_fields=['account_status', 'modified_at'])
        record_status_event(user, previous, status, actor)
    return user


@transaction.atomic
def set_driver_verified(user, verified, actor):
    if not user.is_driver:
        raise BusinessRuleError('This user is not a driver.')
    profile = DriverProfile.objects.select_for_update().get_or_create(user=user)[0]
    if profile.is_verified != verified:
        profile.is_verified = verified
        profile.verified_at = timezone.now() if verified else None
        if not verified:
            profile.availability_status = DriverProfile.Availability.OFFLINE  # stops matching immediately
        profile.save()
        record_status_event(
            profile, 'VERIFIED' if not verified else 'UNVERIFIED', 'VERIFIED' if verified else 'UNVERIFIED', actor
        )
    return profile


@transaction.atomic
def review_report(report, outcome, note, actor):
    report = Report.objects.select_for_update().get(pk=report.pk)
    if outcome not in REPORT_OUTCOMES:
        raise BusinessRuleError('Invalid report outcome.')
    if report.status in (Report.Status.RESOLVED, Report.Status.DISMISSED):
        raise ConflictError('This report is already closed.')
    previous = report.status
    report.status = outcome
    report.resolution_note = note
    if outcome != Report.Status.REVIEWING:
        report.resolved_by, report.resolved_at = actor, timezone.now()
    report.save()
    record_status_event(report, previous, outcome, actor)
    return report
