from celery import shared_task

from . import services


@shared_task
def notify_matching_drivers(trip_request_id):
    return services.notify_matching_drivers(trip_request_id)
