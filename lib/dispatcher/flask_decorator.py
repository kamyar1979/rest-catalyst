from typing import Union, Tuple
import rapidjson
import inspect
from http import HTTPStatus
from urllib.parse import parse_qs

from lib.dispatcher import parse_value, registered_deserializers, deserialize, validate_model
from lib.errors import ApiError
from flask import request
from functools import wraps
from lib.constants import HeaderKeys, MimeTypes, DEFAULT_CHARSET
from lib.extensions import serialize


def dispatch(validate: Union[type, bool] = True, from_header: Tuple[str, ...] = (),
             no_validation: Tuple[str, ...] = (), ignore_fields: Tuple[str, ...] = (), query_string_arg: str = None):
    """
    Deserialize and validate http input parameters and dispatch them into function arguments.
    :param validate: If the parameter is false, no validation takes place. If true, validation performs according to
        Python type annotation or ORM types. If set to some Python type, the input data validates according to given
        type.
    :param from_header: Tells the decorator list of parameters should be read from http header items.
    :param binary: Tells the decorator to suppose this list of parameters are binary (not string/text)
    :param no_validation: List of parameters to be ignored whn validation.
    :param ignore_fields: Ignore this list of parameters whn deserialization.
    :param query_string_arg: Sets this argument with thw complete query string.
    :return:
    """

    def decorate(func):
        sig = inspect.signature(func)
        func_args = sig.parameters

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                data = {}  # Data inventory to be feed with request data
                arg_values = []  # Extra arguments provided by Flask

                # region Get the decorated function signature with type hints
                if len(sig.parameters) == len(args):
                    bind = sig.bind(*args, **kwargs)
                else:
                    bind = sig.bind_partial(*args, **kwargs)
                # endregion

                # region Fill the data inventory with marked header items
                if from_header:
                    for h in from_header:
                        if request.headers.get(h):
                            data[h.replace('x-', '').replace('-', '_')] = request.headers[h]
                content_type_header = request.headers.get(HeaderKeys.ContentType) or MimeTypes.JSON
                # endregion

                # region Try to deserialize the body into data inventory
                if MimeTypes.URLEncoded in content_type_header:
                    data.update(request.args)
                else:
                    for item in registered_deserializers:
                        if item in content_type_header:
                            data.update(deserialize(request.data, item))
                            break
                # endregion

                # region Fill the inventory with query string items
                if request.query_string:
                    qs_dict = parse_qs(str(request.query_string, encoding=DEFAULT_CHARSET))
                    data.update(qs_dict)
                else:
                    qs_dict = {}
                # endregion

                # region Exclude fields due to caller demand
                for item in ignore_fields:
                    if item in data:
                        del data[item]
                # endregion

                # region Collect arguments from anywhere possible
                i = 0
                for k in func_args:  # Iterate through function signature for feeding arguments

                    val: Union[str, bytes, None] = None

                    if k == query_string_arg:  # The argument must be filled with QueryString due to consumer request
                        val = str(request.query_string, DEFAULT_CHARSET)

                    elif k in bind.arguments:  # The argument is requested within dispatching signature (Not Flask)
                        val = bind.arguments[k]

                    elif k in request.args:  # The argument is provided by Flask
                        val = request.args[k] if len(
                            request.args[k]) > 1 \
                            else request.args[k][0]

                    elif request.query_string and k in qs_dict:  # The argument is provided by query string items
                        val = qs_dict[k] if len(qs_dict[k]) > 1 else qs_dict[k][0]

                    elif k in data:  # The argument is already filled
                        val = data[k]

                    elif k.replace('_', '') in data:  # The argument is provided using another naming conventions
                        val = data[k.replace('_', '')]

                    elif i < len(args):  # Fill the argument using Flask values
                        val = args[i]

                    if func_args[k].annotation != inspect.Parameter.empty:
                        if val:
                            arg_values.append(parse_value(val, func_args[k].annotation))

                        elif func_args[k].default != inspect.Parameter.empty:
                            arg_values.append(func_args[k].default)

                        elif i >= len(args):

                            # region Fill attribute values using constructore
                            result_type = func_args[k].annotation
                            cons_params = inspect.signature(result_type).parameters
                            obj = result_type({k:
                                                   parse_value(data.get(k), cons_params[k].annotation)
                                                   if cons_params[k].annotation else data.get(k)
                                               for k in data if k in cons_params})
                            # endregion

                            # region Fill attribute values fusing setattr
                            for k2 in data:
                                if hasattr(obj, k2):
                                    setattr(obj, k2, data[k2])
                            # endregion

                            is_valid, validation_errors = validate_model(data, result_type)
                            if is_valid:
                                arg_values.append(obj)
                            else:
                                raise ValueError(rapidjson.dumps(validation_errors, ensure_ascii=False))


                    elif func_args[k].kind == inspect.Parameter.VAR_KEYWORD:
                        kwargs.update(data)
                    else:
                        if val is None and func_args[k].default != inspect.Parameter.empty:
                            if i >= len(args):
                                arg_values.append(func_args[k].default)
                        else:
                            if val is not None:
                                arg_values.append(val)
                    i += 1

                # endregion

                # region Validate deserialized data
                if validate and type(validate) != bool:
                    model_type = validate
                    is_valid, validation_errors = validate_model(data, model_type, ignore=no_validation)
                    if not is_valid:
                        raise ValueError(rapidjson.dumps(validation_errors, ensure_ascii=False))
                # endregion

                # region Stop arguments once appeared in data inventory to be passed again
                for k in func_args:
                    if k in kwargs:
                        del kwargs[k]
                # endregion

                return func(*arg_values, **kwargs)

            except ValueError as e:
                return serialize({"code": 10400, "message": str(e)}), HTTPStatus.BAD_REQUEST

            except ApiError as e:
                return serialize(e.purified()), e.http_status_code

        wrapper.__name__ = func.__name__
        wrapper.__signature__ = sig

        return wrapper

    return decorate


def handle_error(e: ApiError):
    return serialize(e.purified()), e.http_status_code
