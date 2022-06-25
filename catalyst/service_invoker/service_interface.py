import functools
import inspect
import logging
from dataclasses import dataclass
from http import HTTPStatus
from io import BytesIO
from typing import Dict, Optional, Any, TypeVar, Generic, Type, Mapping, FrozenSet

import aiohttp
import tomlkit
from aiohttp import FormData
import requests
from requests.adapters import HTTPAdapter, Retry

from catalyst.extensions import to_dict
from catalyst.service_invoker.cache import get_cache_item, get_cache_item_sync, set_cache_item, set_cache_item_sync, \
    is_cache_initialized, delete_cache_items, delete_cache_items_sync
from catalyst.utils import dict_to_object
from catalyst import service_invoker
from catalyst.constants import HeaderKeys
from catalyst.dispatcher import deserialize
from catalyst.service_invoker.errors import InterServiceError
from catalyst.dispatcher import deserializers
from catalyst.service_invoker.types import ParameterInputType, RestfulOperation, OpenAPI
from tenacity import retry, wait_fixed, stop_after_attempt, retry_if_result

T = TypeVar("T")

import importlib.resources as pkg_resources

defaults = tomlkit.loads(pkg_resources.read_text(service_invoker, 'defaults.toml'))
config = defaults['config']


@dataclass
class HttpResult(Generic[T]):
    Status: int
    Body: T
    Headers: Dict[str, str]


async def invoke_inter_service_operation(operation_id: str, *,
                                         payload: Optional[Any] = None,
                                         security: Optional[Dict[str, str]] = None,
                                         result_type: Optional[Type[T]] = None,
                                         locale: str = 'en-US',
                                         serialization: str = 'application/json',
                                         use_cache: bool = True,
                                         swagger: Optional[OpenAPI] = None,
                                         inflection: bool = False,
                                         raw_response: bool = False,
                                         success_status: FrozenSet[int] = frozenset({HTTPStatus.OK,
                                                                                     HTTPStatus.CREATED,
                                                                                     HTTPStatus.NO_CONTENT,
                                                                                     HTTPStatus.ACCEPTED}),
                                         parse_unknown_response=True,
                                         pass_through_headers=None,
                                         **kwargs) -> HttpResult[T]:
    logging.debug("Trying to call %s with params %s and body %s from %s",
                  operation_id,
                  kwargs,
                  payload,
                  inspect.currentframe().f_back)

    if swagger:
        openApi = swagger
        base_url = f'{openApi.Info.Schemes[0]}://{openApi.Info.Host}{openApi.Info.BasePath}'
    else:
        openApi = service_invoker.openApi
        base_url = service_invoker.base_url

    operation: RestfulOperation = openApi.Operations.get(operation_id)

    if not operation:
        raise InterServiceError(f"There is no operation with id {operation_id}", 404)

    key = '{}:{:x}'.format(operation_id,
                           functools.reduce(lambda p, c: p ^ hash(c), kwargs.items(), 0) & (2 ** 32 - 1))

    logging.debug("Cache key is %s.", key)

    if operation.CacheDuration and is_cache_initialized() and use_cache:
        cached_result = await get_cache_item(key, result_type)
        if cached_result:
            logging.debug("Reading %s with %s from cache...",
                          operation_id,
                          kwargs)
            cached_headers = await get_cache_item(key + '_headers')

            return HttpResult(HTTPStatus.OK,
                              cached_result,
                              cached_headers)

    values = kwargs.copy()
    url = base_url + operation.EndPoint.format(
        **{p: values.pop(p) for p in kwargs if
           p in operation.Parameters and
           operation.Parameters[p].In == ParameterInputType.Path and
           p in operation.Parameters})

    headers = pass_through_headers or {}
    query_params = {}
    data = FormData()
    for item in operation.Parameters:
        if operation.Parameters[item].In == ParameterInputType.Header:
            var_name = item.replace('X-', '').replace('-', '_').lower()
            if var_name in values:
                headers[item] = str(values.pop(var_name))
        elif operation.Parameters[item].In == ParameterInputType.Query:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in values:
                query_params[item] = str(values.pop(var_name))
        elif operation.Parameters[item].In == ParameterInputType.FormData:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in values:
                if isinstance(values[var_name], bytes):
                    data.add_field(var_name, BytesIO(values.pop(var_name)))
                else:
                    data.add_field(var_name, str(values.pop(var_name)))

    if security:
        for item in security:
            sec = openApi.Info.SecurityDefinitions.get(item)
            if sec:
                if sec.In == ParameterInputType.Header:
                    headers[sec.Name] = security[item]
                elif sec.In == ParameterInputType.Query:
                    query_params[sec.Name] = security[item]

    if not raw_response:
        headers.update({'Accept-Language': locale, 'Accept': serialization})

    if payload != None and not isinstance(payload, (str, bytes)) and not isinstance(payload, Mapping):
        payload = to_dict(payload, inflection=inflection)
        if values:
            payload.update(values)
    if values and not payload:
        payload = values

    timeout: Optional[float] = config['timeout']
    if operation.Timeout:
        timeout = operation.Timeout / 1000.0
    elif openApi.Info.Timeout:
        timeout = openApi.Info.Timeout / 1000.0

    retry_params = config['async_retry_params']

    if openApi.Info.RetryOnFailure:
        retry_params = openApi.Info.RetryOnFailure
    if operation.RetryOnFailure:
        retry_params.update(**operation.RetryOnFailure)


    def is_retriable(method_whitelist, status_forcelist, res):
        return (operation.Method.upper() not in method_whitelist) and \
               (res.Status in status_forcelist)

    @retry(wait=wait_fixed(retry_params['backoff_factor']),
           stop=stop_after_attempt(retry_params['total']),
           retry=retry_if_result(functools.partial(is_retriable,
                                                   retry_params['method_whitelist'],
                                                   retry_params['status_forcelist'])))
    async def do_request() -> HttpResult:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:
            response = await session.request(operation.Method,
                                             url,
                                             data=payload if isinstance(payload, (
                                             str, bytes)) else data if data().size else None,
                                             json=payload if not isinstance(payload,
                                                                            (str, bytes)) and not data().size else None,
                                             headers=headers,
                                             params=query_params,
                                             timeout=timeout,
                                             proxy=openApi.Info.Proxy)

            if raw_response:
                result = await response.read()
            else:
                if HeaderKeys.ContentType in response.headers:
                    content_type, *_ = response.headers[HeaderKeys.ContentType].split(';')
                    response_data = await response.read()
                    result = deserialize(response_data, content_type) if response_data else None
                else:
                    result = await response.json() if parse_unknown_response else None

            if use_cache and operation.CacheDuration and is_cache_initialized() and response.status == HTTPStatus.OK:
                logging.debug("Writing %s with %s to cache...", operation_id,
                              kwargs)
                if result_type:
                    await set_cache_item(key, dict_to_object(result, result_type), operation.CacheDuration)
                else:
                    await set_cache_item(key, result, operation.CacheDuration)
                await set_cache_item(key + '_headers', response.headers, operation.CacheDuration)

            if result_type:
                if response.status in success_status:
                    return HttpResult(response.status,
                                      dict_to_object(result, result_type),
                                      dict(response.headers))
                else:
                    return HttpResult(response.status,
                                      await response.text(),
                                      dict(response.headers))
            else:
                return HttpResult(response.status,
                                  result,
                                  dict(response.headers))

    return await do_request()


def invoke_inter_service_operation_sync(operation_id: str, *,
                                        payload: Optional[Any] = None,
                                        security: Optional[Dict[str, str]] = None,
                                        result_type: Optional[Type[T]] = None,
                                        locale: str = 'en-US',
                                        serialization: str = 'application/json',
                                        use_cache: bool = True,
                                        swagger: Optional[OpenAPI] = None,
                                        inflection: bool = False,
                                        raw_response: bool = False,
                                        success_status: FrozenSet[int] = frozenset({HTTPStatus.OK,
                                                                                    HTTPStatus.CREATED,
                                                                                    HTTPStatus.NO_CONTENT,
                                                                                    HTTPStatus.ACCEPTED}),
                                        parse_unknown_response=True,
                                        pass_through_headers=None,
                                        **kwargs) -> HttpResult[T]:
    logging.debug("Trying to call %s with params %s and body %s from %s",
                  operation_id,
                  kwargs,
                  payload,
                  inspect.currentframe().f_back)

    if swagger:
        openApi = swagger
        base_url = f'{openApi.Info.Schemes[0]}://{openApi.Info.Host}{openApi.Info.BasePath}'
    else:
        openApi = service_invoker.openApi
        base_url = service_invoker.base_url

    operation: RestfulOperation = openApi.Operations.get(operation_id)

    if not operation:
        raise InterServiceError(f"There is no operation with id {operation_id}", 404)

    key = '{}:{:x}'.format(operation_id,
                           functools.reduce(lambda p, c: p ^ hash(c), kwargs.items(), 0) & (2 ** 32 - 1))

    logging.debug("Cache key is %s.", key)

    if operation.CacheDuration and is_cache_initialized() and use_cache:
        cached_result = get_cache_item_sync(key, result_type)
        if cached_result:
            logging.debug("Reading %s with %s from cache...",
                          operation_id,
                          kwargs)
            cached_headers = get_cache_item_sync(key + '_headers')

            return HttpResult(HTTPStatus.OK,
                              cached_result,
                              cached_headers)

    values = kwargs.copy()
    url = base_url + operation.EndPoint.format(
        **{p: values.pop(p) for p in kwargs if
           p in operation.Parameters and
           operation.Parameters[p].In == ParameterInputType.Path and
           p in operation.Parameters})

    headers = pass_through_headers or {}
    query_params = {}
    data = {}
    for item in operation.Parameters:
        if operation.Parameters[item].In == ParameterInputType.Header:
            var_name = item.replace('X-', '').replace('-', '_').lower()
            if var_name in values:
                headers[item] = str(values.pop(var_name))
        elif operation.Parameters[item].In == ParameterInputType.Query:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in values:
                query_params[item] = str(values.pop(var_name))
        elif operation.Parameters[item].In == ParameterInputType.FormData:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in values:
                if isinstance(values[var_name], bytes):
                    data[var_name] = ('', BytesIO(values.pop(var_name)), '', {})
                else:
                    data[var_name] = ('', str(values.pop(var_name)), '', {})

    if security:
        for item in security:
            sec = openApi.Info.SecurityDefinitions.get(item)
            if sec:
                if sec.In == ParameterInputType.Header:
                    headers[sec.Name] = security[item]
                elif sec.In == ParameterInputType.Query:
                    query_params[sec.Name] = security[item]

    if not raw_response:
        headers.update({'Accept-Language': locale, 'Accept': serialization})

    if isinstance(payload, (str, bytes)):
        data = payload
    elif payload != None and not isinstance(payload, Mapping):
        payload = to_dict(payload, inflection=inflection)
        if values:
            payload.update(values)
    if values and not payload:
        payload = values

    timeout: Optional[float] = config['timeout']
    if operation.Timeout:
        timeout = operation.Timeout / 1000.0
    elif openApi.Info.Timeout:
        timeout = openApi.Info.Timeout / 1000.0

    retry_params = config['retry_params']

    if openApi.Info.RetryOnFailure:
        retry_params = openApi.Info.RetryOnFailure
    if operation.RetryOnFailure:
        retry_params.update(**operation.RetryOnFailure)

    adapter = HTTPAdapter(max_retries=Retry(**retry_params))

    with requests.Session() as session:

        session.mount(base_url, adapter)

        response = session.request(operation.Method,
                                   url,
                                   data=data,
                                   json=payload if not data else None,
                                   headers=headers,
                                   params=query_params,
                                   timeout=timeout,
                                   verify=False,
                                   proxies={'http': openApi.Info.Proxy, 'https': openApi.Info.Proxy})

        if raw_response:
            result = response.content
        else:
            if HeaderKeys.ContentType in response.headers:
                content_type, *_ = response.headers[HeaderKeys.ContentType].split(';')
                result = deserialize(response.content, content_type) if response.content else None
            else:
                result = response.json() if parse_unknown_response and response.content else None

        if use_cache and operation.CacheDuration and is_cache_initialized() and response.status_code == HTTPStatus.OK:
            logging.debug("Writing %s with %s to cache...", operation_id,
                          kwargs)
            if result_type:
                set_cache_item_sync(key, dict_to_object(result, result_type), operation.CacheDuration)
            else:
                set_cache_item_sync(key, result, operation.CacheDuration)
            set_cache_item_sync(key + '_headers', response.headers, operation.CacheDuration)

        if result_type:
            if response.status_code in success_status:
                return HttpResult(response.status_code,
                                  dict_to_object(result, result_type),
                                  dict(response.headers))
            else:
                return HttpResult(response.status_code,
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
