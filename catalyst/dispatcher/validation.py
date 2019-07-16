import inspect
from dataclasses import is_dataclass, dataclass, fields
from datetime import time, datetime, date
from enum import Enum
from typing import Any, Union, Tuple, Type

from geojson.geometry import Geometry
from sqlalchemy.types import Boolean, DateTime, Float, DATE, Date, Text, Integer, BigInteger, String, Time
from sqlalchemy.dialects.postgresql import JSONB, ENUM, ARRAY, BYTEA

import sqlalchemy
from cerberus import Validator

from catalyst.dispatcher import validation_handler

type_map = {Boolean: 'boolean', DateTime: 'datetime', JSONB: 'dict',
            Float: 'float', Integer: 'integer', BigInteger: 'integer', String: 'string',
            ARRAY: 'list', Geometry: 'geometry', ENUM: 'string',
            Time: 'time', DATE: 'date', Date: 'date', Text: 'string',
            BYTEA: 'string'}

dto_type_map = {bool: 'boolean', datetime: 'datetime',
                float: 'float', int: 'integer', str: 'string',
                tuple: 'list', Enum: 'string', time: 'time', date: 'date',
                list: 'list'}


def create_schema(alchemy_model, ignore: Tuple[str, ...] = ()):
    """
    Creates Cerberus schema from ORM model
    :param alchemy_model: ORM Model type
    :param ignore: ignore columns when creating schema
    :return: Cerberus Schema
    """
    schema = {}
    mapper = sqlalchemy.inspect(alchemy_model)
    for i in mapper.attrs:
        if i.key not in ignore:
            column = getattr(alchemy_model, i.key)
            if hasattr(column, 'type'):
                schema[i.key] = {'type': type_map[type(column.type)],
                                 'required': not (column.nullable or column.primary_key),
                                 'nullable': column.nullable}
                if hasattr(column.type, 'length') and column.type.length:
                    schema[i.key]['maxlength'] = column.type.length
                if column.info:
                    if 'pattern' in column.info:
                        schema[i.key]['regex'] = column.info['pattern']
    return schema


def create_schema_from_dto(data_class: dataclass, ignore=()):
    schema = {}
    for f in fields(data_class):
        if f.name not in ignore:
            t: type = f.type
            optional: bool = False
            if hasattr(f.type, '__origin__'):
                if f.type.__origin__ == Union:
                    t = f.type.__args__[0]
                    optional = True
            if inspect.isclass(t) and issubclass(t, Enum):
                t = Enum

            if t in dto_type_map:
                schema[f.name] = {'type': dto_type_map[t],
                                  'required': not optional}

    return schema


class OurValidator(Validator):
    """
    Custom Validator for Cerberus
    """

    def __init__(self, model_type, schema, *args, **kwargs):
        super().__init__(schema, *args, **kwargs)
        self.alchemy_type = model_type

    def _validate_type_time(self, value):
        try:
            if type(value) == str:
                time.fromisoformat(value)
                return True
            elif type(value) == time:
                return True
        except(ValueError, TypeError):
            return False


@validation_handler
def cerberus_validator(data: Any, model_type: Type, ignore=()) -> Tuple[bool, tuple]:
    if model_type and hasattr(model_type, '__table__'):
        schema = create_schema(model_type, ignore=ignore or ())
        v = OurValidator(model_type, schema, allow_unknown=True)
        return v.validate(data), v.errors
    elif is_dataclass(model_type):
        schema = create_schema_from_dto(model_type, ignore=ignore or ())
        v = OurValidator(model_type, schema, allow_unknown=True)
        return v.validate(data), v.errors
    else:
        return True, ()
