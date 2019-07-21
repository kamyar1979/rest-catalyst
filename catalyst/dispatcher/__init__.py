from typing import Callable, TypeVar, Type, Dict, Any, Union, Tuple
import inspect

T = TypeVar('T')

registered_types: Dict[Type, Callable[[Any], Any]] = {}
registered_deserializers: Dict[str, Callable[[str], Any]] = {}
validator_func: Callable[[Any], bool]


def type_handler(func: Callable[[Any, Type], T]):
    sig = inspect.signature(func)
    registered_types[sig.return_annotation] = func


def parse_value(val: Any, t: Type[T]) -> T:
    for k in registered_types:

        #region The type is Union/Optional or mix of them
        if hasattr(k, '__origin__'):
            if k.__origin__ == Union:
                if hasattr(k, '__args__'):
                    for c in k.__args__:
                        if inspect.isclass(t) and issubclass(t, c):
                            if t != type(None):
                                return registered_types[k](val, requested_type=t)
        #endregion

        #region The type is Generic with constraints (TypeVar)
        elif hasattr(k, '__constraints__'):
            for c in k.__constraints__:
                if inspect.isclass(t) and issubclass(t, c):
                    return registered_types[k](val, requested_type=t)
        #endregion

        #region The type is simple Python type
        if inspect.isclass(t):
            if issubclass(t, k):
                return registered_types[k](val, requested_type=t)
            else:
                return t(val)
        else:
            return val
        #endregion


def deserialization_handler(mime_type: str):
    def decorate(func: Callable[[str], Any]):
        registered_deserializers[mime_type] = func

    return decorate


def deserialize(data: str, mime_type: str) -> Any:
    if mime_type in registered_deserializers:
        return registered_deserializers[mime_type](data)


def validation_handler(func: Callable[[Any, Type], Tuple[bool, Tuple[str]]]):
    global validator_func
    validator_func = func


def validate_model(data: Any, t: Type, ignore=()) -> bool:
    return validator_func(data, t, ignore=ignore)
