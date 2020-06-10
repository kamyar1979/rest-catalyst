import inspect
import re
import struct
import uuid
from dataclasses import fields, dataclass, is_dataclass
from datetime import datetime
from typing import Tuple, TypeVar, Dict, Any, Type, Optional, Union

import ntplib
import pytz
from catalyst.dispatcher import parse_value

from catalyst.constants import ConfigKeys
from . import app
import base62
from catalyst.dispatcher import type_handlers


def get_current_time(tz=pytz.utc, config: Optional[Dict[str, Any]] = None) -> datetime:
    """
    Get current time from time server (NTP) and optionally apply time zone
    :param tz: Time zone to be applied
    :return: Python standard datetime
    """
    if not config:
        if app:
            config = app.config
    if not config or ConfigKeys.NTPServer not in config:
        return tz.fromutc(datetime.utcnow())
    try:
        c = ntplib.NTPClient()
        response = c.request(config[ConfigKeys.NTPServer], version=3)
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


T = TypeVar('T')


def dict_to_object(data: Dict[str, Any], cls: Type[T]) -> T:
    def get_field_value(val: Any, annotation: Optional[Type[T]] = None):
        if annotation:
            if hasattr(annotation, '__origin__'):
                if annotation.__origin__ == Union:
                    if hasattr(annotation, '__args__'):
                        annotation = annotation.__args__[0]

            if is_dataclass(annotation):
                return dict_to_object(val, annotation)
            else:
                return parse_value(val, annotation)
        else:
            return val

    if is_dataclass(cls):
        cons_params = inspect.signature(cls).parameters
        return cls(**{k: get_field_value(data.get(k), cons_params[k].annotation) for k in data if k in cons_params})
