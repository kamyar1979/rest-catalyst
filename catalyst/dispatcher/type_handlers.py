import base64
from datetime import datetime, date, time
from enum import Enum
from typing import Any, AnyStr, Tuple, TypeVar, Type

import geojson
import rapidjson
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
    return datetime.strptime(value, '%Y-%m-%d %H:%M:%S')


@type_handler
def parse_date(val: Any) -> date:
    value = str(val, encoding=DEFAULT_CHARSET) if type(val) is bytes else val
    return datetime.strptime(value, '%Y-%m-%d')


@type_handler
def parse_time(val: Any) -> time:
    value = str(val, encoding=DEFAULT_CHARSET) if type(val) is bytes else val
    return time.fromisoformat(value)


E = TypeVar('E', Enum, type(None))
@type_handler
def parse_enum(val: Any, requested_type: Type[E]) -> Enum:
    if any(val == item.value for item in requested_type):
        return requested_type(val)
    else:
        raise ValueError('Not a valid enum value')



def parse_geometry(val: Any) -> BaseGeometry:
    return shape(geojson.loads(rapidjson.dumps(val)))