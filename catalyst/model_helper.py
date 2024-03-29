from enum import Enum
from operator import attrgetter, itemgetter
from typing import Type, Tuple, Dict, Callable, Union, Mapping, get_type_hints, Any, TypeVar, Optional, NamedTuple

import geojson
import rapidjson
from geoalchemy2 import WKBElement
from geoalchemy2.shape import to_shape
from sqlalchemy import inspect
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.engine import Row
from toolz import compose
from inspect import isclass


def create_named_tuple_mapping(model: Mapping,
                               dto_type: Type,
                               include: Optional[Tuple[str]] = None,
                               exclude: Optional[Tuple[str]] = None,
                               prefix: Optional[str] = None,
                               **kwargs: Callable[[NamedTuple], Any]) -> Dict[str, Callable[[object], object]]:
    """
    Creates a mapping between entity model and DTO getting named tuple object
    :param model: ORM Model Type
    :param dto_type: DTO data class type
    :param include: Include items from entity model
    :param exclude: Exclude items from entity model
    :param prefix: Prefix of the DTO properties to be added to the result
    :param kwargs:
    :return:
    """
    result_object = dto_type()
    result = {}

    for k in model.keys():

        attr_name = k[len(prefix):] if prefix and k.startswith(prefix) else k

        if attr_name in kwargs:

            if hasattr(result_object, attr_name):
                result[attr_name] = kwargs[attr_name]
        else:
            if (include is None or attr_name in include) and (exclude is None or attr_name not in exclude):
                if hasattr(result_object, attr_name):
                    result[attr_name] = attrgetter(k)

    for k in kwargs:

        attr_name = k[len(prefix):] if prefix and k.startswith(prefix) else k

        if hasattr(result_object, attr_name):
            result[attr_name] = kwargs[k]

    return result


T = TypeVar('T', object, Tuple)
U = TypeVar('U')


def create_mapping(model: T,
                   dto_type: Type[U], *,
                   include: Optional[Tuple[str, ...]] = None,
                   exclude: Optional[Tuple[str, ...]] = None,
                   prefix: Optional[str] = None,
                   model_item_index: int = 0,
                   **kwargs: Callable[[T], Any]) -> Dict[str, Callable[[T], Any]]:
    """
    Recursively creates mapping between ORm model objects and Python data classes
    :param model: input object, ORM model type, or Named Tuple
    :param dto_type: Type of output, usually a Python 3.7+ dataclass
    :param include: Include extra fields that may not be in DTO type
    :param exclude: Exclude fields although they are in DTO type
    :param prefix: Add extra prefix to the field names
    :param model_item_index: Starting index of named tuple, if the first parameter is named tuple
    :param kwargs: Any extra fields that may not be in input type. Overrides the default implementation.
    :return: A dictionary mapping values with corresponding functions
    """

    if model is None:
        return {}

    if isinstance(model, Row):
        model_type_name = type(model[model_item_index]).__name__
        model_object_info = inspect(getattr(model, model_type_name))
        extractor = itemgetter(model_item_index)
        extra_fields = frozenset(model._fields[1:])
    else:
        model_object_info = inspect(model)
        extractor = None
        extra_fields = frozenset()

    model_empty_fields = model_object_info.unloaded  # Omit lazy-loaded fields
    attributes = model_object_info.attrs
    hybrid_properties = frozenset(i.__name__ for i in
                                    model_object_info.mapper.all_orm_descriptors if type(i) == hybrid_property)
    relationships = model_object_info.mapper.relationships  # Discover relationships for nested objects
    result_object = dto_type()
    result = {}
    attr_list = frozenset(item.key for item in attributes) | extra_fields | hybrid_properties

    for k in attr_list:
        attr_name = (prefix or '') + k

        if k in kwargs:
            if hasattr(result_object, attr_name):
                result[attr_name] = kwargs[k]
        elif k not in model_empty_fields:
            if k in relationships.keys() and (exclude is None or k not in exclude) and not relationships[k].uselist:
                model_proxy = extractor(model) if extractor else model
                if hasattr(model_proxy, k) and getattr(model_proxy, k):
                    my_mapping = create_mapping(getattr(model_proxy, k), dto_type,
                                                prefix=(prefix or '') + k + '_',
                                                include=include,
                                                exclude=exclude)
                    for key in my_mapping:
                        if extractor:
                            result[key] = compose(my_mapping[key], attrgetter(k), extractor)
                        else:
                            result[key] = compose(my_mapping[key], attrgetter(k))
            elif (include is None or attr_name in include) and (exclude is None or attr_name not in exclude):
                if hasattr(result_object, attr_name):
                    if extractor and attr_name not in extra_fields:
                        result[attr_name] = compose(attrgetter(k), extractor)
                    else:
                        result[attr_name] = attrgetter(k)

    for k in kwargs:
        attr_name = (prefix or '') + k
        if hasattr(result_object, attr_name):
            result[attr_name] = kwargs[k]

    return result


def create_dto(model: T,
               dto_type: Type[U],
               mapping: Dict[str, Callable[[T], Any]]) -> U:
    annotations = get_type_hints(dto_type)

    def create_result_dict():
        for k in mapping:
            try:
                val: Any = mapping[k](model)
                t: type = annotations[k]
                if not isclass(t):
                    if hasattr(t, '__origin__'):
                        if t.__origin__ == Union:
                            if hasattr(t, '__args__') and t.__args__:
                                t = t.__args__[0]
                            if hasattr(t, '__origin__') and (t.__origin__ == tuple or t.__origin__ == dict):
                                t = t.__origin__

                if val is not None:
                    if issubclass(t, Enum):
                        yield k, t(val).value
                    else:
                        if type(val) != t:
                            if type(val) == WKBElement:
                                yield k, rapidjson.loads(geojson.dumps(to_shape(val)))
                            else:
                                yield k, t(val)
                        else:
                            yield k, val
            except AttributeError:
                pass

    return dto_type(**{k: v for k, v in create_result_dict()})


def update_from(obj, **kwargs):
    for item in kwargs:
        if hasattr(obj, item):
            setattr(obj, item, kwargs[item])
