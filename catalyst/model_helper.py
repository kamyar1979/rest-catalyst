from operator import attrgetter
from typing import Type, Tuple, Set, Dict, Callable, Union, Mapping, get_type_hints, Any, TypeVar, Optional

import geojson
import rapidjson
from geoalchemy2 import WKBElement
from shapely import wkb
from sqlalchemy import inspect
from toolz import compose


def create_named_tuple_mapping(model: Mapping,
                               dto_type: Type,
                               include: Set[str] = None,
                               exclude: Set[str] = None,
                               prefix: str = None,
                               **kwargs) -> Dict[str, Callable[[object], object]]:
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


def create_mapping(model: Type[T],
                   dto_type: Type[U], *,
                   include: Optional[Set[str]] = None,
                   exclude: Optional[Set[str]] = None,
                   prefix: Optional[str] = None,
                   model_item_index: int = 0,
                   **kwargs: Dict[str, Callable[[Type[T]], Any]]) -> Dict[str, Callable[[Type[T]], Any]]:
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

    if issubclass(type(model), Tuple):  # The type is named tuple
        model_object_info = inspect(getattr(model, type(model[model_item_index]).__name__))
        extractor = attrgetter(type(model[0]).__name__)
    else:
        model_object_info = inspect(model)
        extractor = None

    model_empty_fields = model_object_info.unloaded  # Omit lazy-loaded fields
    attributes = model_object_info.attrs
    relationships = model_object_info.mapper.relationships  # Discover relationships for nested objects
    result_object = dto_type()
    result = {}
    attr_list = set(item.key for item in attributes)

    for k in attr_list:
        attr_name = (prefix or '') + k

        if k in kwargs:
            if hasattr(result_object, attr_name):
                result[attr_name] = kwargs[k]
        elif k not in model_empty_fields:
            if k in relationships.keys():
                if getattr(model, k):
                    my_mapping = create_mapping(getattr(model, k), dto_type,
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
                    if extractor:
                        result[attr_name] = compose(attrgetter(k), extractor)
                    else:
                        result[attr_name] = attrgetter(k)

    for k in kwargs:
        attr_name = (prefix or '') + k
        if hasattr(result_object, attr_name):
            result[attr_name] = kwargs[k]

    return result


def create_dto(model: Type[T],
               dto_type: Type[U],
               mapping: Dict[str, Callable[[object], object]]) -> U:
    annotations = get_type_hints(dto_type)

    def create_result_dict():
        for k in mapping:
            try:
                val: Any = mapping[k](model)
                t: type = annotations[k].__args__[0] if hasattr(annotations[k], '__origin__') and \
                                                        annotations[k].__origin__ == Union else annotations[k]
                if val is not None and type(val) != t:
                    if type(val) == WKBElement:
                        geom = wkb.loads(bytes(val.data))
                        yield k, rapidjson.loads(geojson.dumps(geojson.Feature(geom)))
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
