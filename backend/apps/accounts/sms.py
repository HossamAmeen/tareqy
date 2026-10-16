import logging

from django.conf import settings
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)


class BaseSMSBackend:
    def send(self, phone: str, message: str) -> None:
        raise NotImplementedError


class ConsoleSMSBackend(BaseSMSBackend):
    """Development only: logs the message instead of sending it."""

    def send(self, phone, message):
        logger.warning('SMS to %s: %s', phone, message)


class LocMemSMSBackend(BaseSMSBackend):
    """Tests: keeps messages in `outbox`."""

    outbox: list = []

    def send(self, phone, message):
        self.outbox.append((phone, message))


def send_sms(phone, message):
    import_string(settings.SMS_BACKEND)().send(phone, message)
