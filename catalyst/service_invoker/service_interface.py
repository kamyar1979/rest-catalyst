import functools
import inspect
import logging
from http import HTTPStatus
from io import BytesIO
from typing import Dict, Optional, NamedTuple, Any, TypeVar, Generic, Type, Union, Mapping

import aiohttp
from aiohttp import FormData

from catalyst.extensions import to_dict
from catalyst.service_invoker.cache import get_cache_item, get_cache_item_sync, set_cache_item, set_cache_item_sync, \
    is_cache_initialized, delete_cache_items, delete_cache_items_sync

from catalyst.utils import dict_to_object

from catalyst import service_invoker, app
from catalyst.constants import HeaderKeys
from catalyst.dispatcher import deserialize
from catalyst.service_invoker.errors import InterServiceError
from catalyst.dispatcher import deserializers

from catalyst.service_invoker.types import ParameterInputType, RestfulOperation
import requests


class HttpResult(NamedTuple):
    Status: int
    Body: Any
    Headers: Dict[str, str]


T = TypeVar("T")


class TypedHttpResult(HttpResult, Generic[T]):
    pass


async def invoke_inter_service_operation(operation_id: str, *,
                                         payload: Optional[Any] = None,
                                         token: Optional[str] = None,
                                         result_type: Optional[Type[T]] = None,
                                         locale: str = 'en-US',
                                         serialization: str = 'application/json',
                                         use_cache: bool = True,
                                         **kwargs) -> Union[HttpResult, TypedHttpResult[T]]:
    logging.debug("Trying to call %s with params %s and body %s from %s",
                  operation_id,
                  kwargs,
                  payload,
                  inspect.currentframe().f_back)

    operation: RestfulOperation = service_invoker.openApi.Operations.get(operation_id)

    if not operation:
        raise InterServiceError(f"There is no operation with id {operation_id}", 404)

    key = '{}:{:x}'.format(operation_id,
                           functools.reduce(lambda p, c: p ^ hash(c), kwargs.items(), 0) & (2 ** 32 - 1))

    logging.debug("Cache key is %s.", key)

    if operation.CacheDuration and is_cache_initialized() and use_cache:
        cached_result = await get_cache_item(key, result_type)
        if cached_result:
            logging.info("Reading %s with %s from cache...",
                         operation_id,
                         kwargs)
            cached_headers = await get_cache_item(key + '_headers')
            if result_type:
                return TypedHttpResult[result_type](HTTPStatus.OK,
                                                    cached_result,
                                                    cached_headers)
            else:
                return HttpResult(HTTPStatus.OK,
                                  cached_result,
                                  cached_headers)

    url = service_invoker.base_url + operation.EndPoint.format(
        **{p: kwargs.get(p) for p in kwargs if
           p in operation.Parameters and
           operation.Parameters[p].In == ParameterInputType.Path and
           p in operation.Parameters})

    headers = {}
    query_params = {}
    data = FormData()
    for item in operation.Parameters:
        if operation.Parameters[item].In == ParameterInputType.Header:
            var_name = item.replace('X-', '').replace('-', '_').lower()
            if var_name in kwargs:
                headers[item] = str(kwargs[var_name])
        elif operation.Parameters[item].In == ParameterInputType.Query:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in kwargs:
                query_params[item] = str(kwargs[var_name])
        elif operation.Parameters[item].In == ParameterInputType.FormData:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in kwargs:
                data.add_field(var_name, BytesIO(kwargs[var_name]))

    if token:
        headers['Authorization'] = f'Bearer {token}'

    headers.update({'Accept-Language': locale, 'Accept': serialization})

    if not isinstance(payload, Mapping):
        payload = to_dict(payload)

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:

        if data().size:
            response = await session.request(operation.Method,
                                             url,
                                             data=data,
                                             headers=headers,
                                             params=query_params)
        else:
            response = await session.request(operation.Method,
                                             url,
                                             json=payload,
                                             headers=headers,
                                             params=query_params)

        if HeaderKeys.ContentType in response.headers:
            content_type, *_ = response.headers[HeaderKeys.ContentType].split(';')
            result = deserialize(await response.content.read(), content_type)
        else:
            result = await response.json()

        if operation.CacheDuration and is_cache_initialized() and response.status == HTTPStatus.OK:
            if result_type:
                await set_cache_item(key, dict_to_object(result, result_type), operation.CacheDuration)
            else:
                await set_cache_item(key, result, operation.CacheDuration)
            await set_cache_item(key + '_headers', response.headers, operation.CacheDuration)

        if result_type:
            if response.status == HTTPStatus.OK:
                return TypedHttpResult[result_type](response.status,
                                                    dict_to_object(result, result_type),
                                                    dict(response.headers))
            else:
                return TypedHttpResult[result_type](response.status,
                                                    await response.text(),
                                                    dict(response.headers))
        else:
            return HttpResult(response.status,
                              result,
                              dict(response.headers))


def invoke_inter_service_operation_sync(operation_id: str, *,
                                        payload: Optional[Any] = None,
                                        token: Optional[str] = None,
                                        result_type: Optional[Type[T]] = None,
                                        locale: str = 'en-US',
                                        serialization: str = 'application/json',
                                        use_cache: bool = True,
                                        **kwargs) -> Union[HttpResult, TypedHttpResult[T]]:
    logging.debug("Trying to call %s with params %s and body %s from %s %s",
                  operation_id,
                  kwargs,
                  payload,
                  app.name,
                  inspect.currentframe().f_back)

    operation: RestfulOperation = service_invoker.openApi.Operations.get(operation_id)

    if not operation:
        raise InterServiceError(f"There is no operation with id {operation_id}", 404)

    key = '{}:{:x}'.format(operation_id,
                           functools.reduce(lambda p, c: p ^ hash(c), kwargs.items(), 0) & (2 ** 32 - 1))

    logging.debug("Cache key is %s.", key)

    if operation.CacheDuration and is_cache_initialized() and use_cache:
        cached_result = get_cache_item_sync(key, result_type)
        if cached_result:
            logging.info("Reading %s with %s from cache...",
                         operation_id,
                         kwargs)
            cached_headers = get_cache_item_sync(key + '_headers')
            if result_type:
                return TypedHttpResult[result_type](HTTPStatus.OK,
                                                    cached_result,
                                                    cached_headers)
            else:
                return HttpResult(HTTPStatus.OK,
                                  cached_result,
                                  cached_headers)

    url = service_invoker.base_url + operation.EndPoint.format(
        **{p: kwargs.get(p) for p in kwargs if
           p in operation.Parameters and
           operation.Parameters[p].In == ParameterInputType.Path and
           p in operation.Parameters})

    headers = {}
    query_params = {}
    data = {}
    for item in operation.Parameters:
        if operation.Parameters[item].In == ParameterInputType.Header:
            var_name = item.replace('X-', '').replace('-', '_').lower()
            if var_name in kwargs:
                headers[item] = str(kwargs[var_name])
        elif operation.Parameters[item].In == ParameterInputType.Query:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in kwargs:
                query_params[item] = str(kwargs[var_name])
        elif operation.Parameters[item].In == ParameterInputType.FormData:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in kwargs:
                data[var_name] = ('', BytesIO(kwargs[var_name]), '', {})

    if token:
        headers['Authorization'] = f'Bearer {token}'

    headers.update({'Accept-Language': locale, 'Accept': serialization})

    if not isinstance(payload, Mapping):
        payload = to_dict(payload)

    with requests.Session() as session:

        if data:
            response = session.request(operation.Method,
                                       url,
                                       data=data,
                                       headers=headers,
                                       params=query_params)
        else:
            response = session.request(operation.Method,
                                       url,
                                       json=payload,
                                       headers=headers,
                                       params=query_params)

        if HeaderKeys.ContentType in response.headers:
            content_type, *_ = response.headers[HeaderKeys.ContentType].split(';')
            result = deserialize(response.content, content_type)
        else:
            result = response.json()

        if operation.CacheDuration and is_cache_initialized() and response.status_code == HTTPStatus.OK:
            if result_type:
                set_cache_item_sync(key, dict_to_object(result, result_type), operation.CacheDuration)
            else:
                set_cache_item_sync(key, result, operation.CacheDuration)
            set_cache_item_sync(key + '_headers', response.headers, operation.CacheDuration)

        if result_type:
            if response.status_code == HTTPStatus.OK:
                return TypedHttpResult[result_type](response.status_code,
                                                    dict_to_object(result, result_type),
                                                    dict(response.headers))
            else:
                return TypedHttpResult[result_type](response.status_code,
                                                    response.text,
                                                    dict(response.headers))
        else:
            return HttpResult(response.status_code,
                              result,
                              dict(response.headers))


def check_result(value: HttpResult) -> HttpResult:
    if value.Status in (HTTPStatus.OK,
                        HTTPStatus.CREATED,
                        HTTPStatus.ACCEPTED,
                        HTTPStatus.NON_AUTHORITATIVE_INFORMATION,
                        HTTPStatus.NO_CONTENT,
                        HTTPStatus.RESET_CONTENT,
                        HTTPStatus.PARTIAL_CONTENT,
                        HTTPStatus.MULTI_STATUS,
                        HTTPStatus.ALREADY_REPORTED,
                        HTTPStatus.IM_USED
                        ):
        return value
    else:
        raise InterServiceError(value.Body.get('message'), value.Body.get('code'), value.Body.get('uri'))


async def invalidate_cache(resource_name: str, **kwargs):
    await delete_cache_items('*{resource_name}*:{params_hash:x}*'.format(
        resource_name=resource_name,
        params_hash=functools.reduce(lambda p, c: p ^ hash(c), kwargs.items(), 0) & (2 ** 32 - 1)))


def invalidate_cache_sync(resource_name: str, **kwargs):
    delete_cache_items_sync('*{resource_name}*:{params_hash:x}*'.format(
        resource_name=resource_name,
        params_hash=functools.reduce(lambda p, c: p ^ hash(c), kwargs.items(), 0) & (2 ** 32 - 1)))
