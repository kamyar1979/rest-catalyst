import base64
from dataclasses import is_dataclass
from datetime import datetime, date, time
from typing import Any, AnyStr, Tuple

import sqlalchemy
from geojson.geometry import Geometry
from sqlalchemy import Binary
from sqlalchemy.orm import RelationshipProperty

from catalyst.constants import DEFAULT_CHARSET
from catalyst.dispatcher import type_handler
from catalyst.constants import SRID


def adapt_field_type(column, value):
    """
    Adapt field type from Python types into RDBMS types
    :param column: SqlAlchemy Column
    :param value: The Python value to fill in database
    :return:
    """
    if type(column.type) == Geometry:
        geo_type = column.type.geometry_type
        if geo_type == 'POINT':
            return f'SRID=${SRID};POINT(${value[0]} ${value[1]})'
    elif type(column.type) == Binary:
        return base64.b64encode(value)
    return value


def create_model(alchemy_model, **kwargs):
    """
    Creates a model object form items dictionary
    :param alchemy_model: SqlAlchemy model Type
    :param kwargs: Items dictionary
    :return: Model object
    """
    model = {}
    for k in sqlalchemy.inspect(alchemy_model).attrs:
        if kwargs.get(k.key) is not None:
            column = getattr(alchemy_model, k.key)
            if hasattr(column, 'type'):
                model[k.key] = adapt_field_type(column, kwargs[k.key])
    if hasattr(alchemy_model, 'registered_date'):
        setattr(alchemy_model, 'registered_date', datetime.now())
    return alchemy_model(**model)


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


@type_handler
def parse_object(data: Any, requested_type: type) -> object:
    if hasattr(requested_type, '__table__'):
        params = {attr.key: data.get(attr.key) for attr in
                  sqlalchemy.inspect(requested_type).attrs
                  if
                  type(attr) != RelationshipProperty}
        return create_model(requested_type, **params)
    elif is_dataclass(requested_type):
        return requested_type(**data)
