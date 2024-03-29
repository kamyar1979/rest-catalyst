from datetime import datetime, date, time, timedelta
from enum import Enum
from typing import Any, AnyStr, Tuple, TypeVar, Type, Optional

import geojson
import rapidjson
import re
from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

from catalyst.constants import DEFAULT_CHARSET
from catalyst.dispatcher import type_handler


@type_handler
def handle_byte_string(val: AnyStr) -> bytes:
    if type(val) != bytes:
        return bytes(val, encoding=DEFAULT_CHARSET)
    else:
        return val


@type_handler
def parse_tuple(val: Any, *, requested_type: type) -> tuple:
    if isinstance(val, str) or isinstance(val, bytes):
        val_seq = (val,)
    else:
        val_seq = val
    if type(requested_type) is type(Tuple) and \
            hasattr(requested_type, '__tuple_params__'):
        if hasattr(requested_type, '__tuple_use_ellipsis__'):
            t_types = requested_type.__tuple_params__ * len(val_seq)
        else:
            t_types = requested_type.__tuple_params__
        t_list = []
        for i, t_item in enumerate(val):
            if isinstance(t_item, bytes) and t_types[i] is str:
                t_list.append(str(t_item, encoding=DEFAULT_CHARSET))
            else:
                if isinstance(t_item, dict):
                    t_list.append(t_types[i](**t_item))
                else:
                    t_list.append(t_types[i](t_item))
        return tuple(t_list)
    else:
        return tuple(val_seq)


@type_handler
def parse_string(val: AnyStr) -> str:
    if type(val) is bytes:
        return str(val, encoding=DEFAULT_CHARSET)
    else:
        return val


@type_handler
def parse_datetime(val: Any) -> datetime:
    value = str(val, encoding=DEFAULT_CHARSET) if type(val) is bytes else val
    if re.match(r'^\d{2,4}-\d{,2}-\d{,2}\s\d{,2}:\d{,2}:\d{,2}$', value):
        return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
    elif re.match(r'^\d{2,4}-\d{,2}-\d{,2}T\d{,2}:\d{,2}:\d{,2}$', value):
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
    elif re.match(r'^\d{2,4}-\d{,2}-\d{,2}T\d{,2}:\d{,2}:\d{,2}\.\d+$', value):
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f')
    elif re.match(r'^\d{2,4}-\d{,2}-\d{,2}T\d{,2}:\d{,2}:\d{,2}\.\d+[+-]\d{,2}:?\d{,2}$', value):
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%f%z')


@type_handler
def parse_date(val: Any) -> date:
    value = str(val, encoding=DEFAULT_CHARSET) if type(val) is bytes else val
    return datetime.strptime(value, '%Y-%m-%d')


@type_handler
def parse_time(val: Any) -> time:
    value = str(val, encoding=DEFAULT_CHARSET) if type(val) is bytes else val
    return time.fromisoformat(value)


@type_handler
def parse_timedelta(val: Any) -> timedelta:
    value = str(val, encoding=DEFAULT_CHARSET) if type(val) is bytes else val
    m = re.match(
        r'P(?:(?P<year>\d+)Y)?(?:(?P<month>\d+)M)?(?:(?P<day>\d+)D)?(?:T(?:(?P<hour>\d+)H)?(?:(?P<minute>\d+)M)?(?:(?P<second>\d+)S)?)?',
        value)
    if m:
        return timedelta(
            days=int(m.group('year') or 0) * 365 + int(m.group('month') or 0) * 30 + int(m.group('day') or 0),
            hours=int(m.group('hour') or 0),
            minutes=int(m.group('minute') or 0),
            seconds=int(m.group('second') or 0)
        )


E = TypeVar('E', Enum, type(None))


@type_handler
def parse_enum(val: Any, requested_type: Type[E]) -> Enum:
    if any(val == item.value for item in requested_type):
        return requested_type(val)
    else:
        raise ValueError('Not a valid enum value')


@type_handler
def parse_geometry(val: Any) -> Optional[BaseGeometry]:
    if val:
        return shape(geojson.loads(rapidjson.dumps(val)))
    else:
        return
