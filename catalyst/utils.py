import re
import struct
import uuid
from dataclasses import fields, dataclass
from datetime import datetime
from functools import wraps
from typing import Tuple, Callable

import ntplib
import pytz

from catalyst.constants import ConfigKeys
from . import app
import base62


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


def uuid_comb() -> uuid.UUID:
    uuid_array = bytearray(uuid.uuid1().bytes)
    base_date = datetime(1900, 1, 1)
    now = datetime.now()
    days = now - base_date
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    sec = int((datetime.now() - midnight).total_seconds() * 300)

    days_array = struct.pack('I', days.days)
    sec_array = struct.pack('L', sec)

    uuid_array[-6:-4] = days_array[:2:][::-1]
    uuid_array[-4:] = sec_array[:4:][::-1]

    return uuid.UUID(bytes=bytes(uuid_array))


def create_tracking_code(value: uuid.UUID) -> str:
    h, l = struct.unpack('LL', value.bytes)
    return base62.encode(h ^ l)


def validation_patterns(**kwargs: str):

    def decorate(cls: dataclass):
        cls.validate = lambda self: tuple(f'Field {f.name} pattern does not match.' for f in fields(cls)
                                          if f.name in kwargs and not re.match(kwargs[f.name], getattr(self, f.name)))
        return cls

    return decorate


