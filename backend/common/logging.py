import logging
import re

# Phone numbers must never reach logs or error trackers.
PHONE_RE = re.compile(r'\+?\d[\d\s-]{7,16}\d')


class RedactPhoneFilter(logging.Filter):
    def filter(self, record):
        record.msg = PHONE_RE.sub('[phone]', str(record.getMessage()))
        record.args = ()
        return True
