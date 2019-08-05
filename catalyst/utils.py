from datetime import datetime
from typing import Tuple

import ntplib
import pytz

from catalyst.constants import ConfigKeys
from . import app


def get_current_time(tz=pytz.utc):
    """
    Get current time from time server (NTP) and optionally apply time zone
    :param tz: Time zone to be applied
    :return: Python standard datetime
    """
    c = ntplib.NTPClient()
    if ConfigKeys.NTPServer not in app.config:
        return tz.fromutc(datetime.utcnow())
    try:
        response = c.request(app.config[ConfigKeys.NTPServer], version=3)
        return datetime.fromtimestamp(response.tx_time, tz)
    except:
        return tz.fromutc(datetime.utcnow())


def validate(model: object, *required_fields: str, allow_blank: Tuple[str, ...] = ()) -> Tuple[str, ...]:
    """
    Validate DTO Model
    :param model: DTO Model
    :return: Validation errors list
    """
    return tuple(f'Field {field} is required' for field in required_fields
                 if hasattr(model, field) and (
                         getattr(model, field) is None or (getattr(model, field) == '' and field not in allow_blank)
                 ))
