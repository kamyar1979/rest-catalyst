from http import HTTPStatus
from typing import Dict, Optional, NamedTuple, Any, TypeVar, Generic, Type, Union

import aiohttp
from catalyst.utils import dict_to_object

from catalyst import service_invoker
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
                                         locale='en-US',
                                         format='application/json',
                                         **kwargs) -> Union[HttpResult, TypedHttpResult[T]]:
    operation: RestfulOperation = service_invoker.operations.get(operation_id)

    if not operation:
        raise InterServiceError(f"There is no operation with id {operation_id}", 404)

    url = service_invoker.base_url + operation.EndPoint.format(
        **{p: kwargs.get(p) for p in kwargs if
           p in operation.Parameters and
           operation.Parameters[p].In == ParameterInputType.Path and
           p in operation.Parameters})

    headers = {}
    query_params = {}
    for item in operation.Parameters:
        if operation.Parameters[item].In == ParameterInputType.Header:
            var_name = item.replace('X-', '').replace('-', '_').lower()
            if var_name in kwargs:
                headers[item] = str(kwargs[var_name])
        elif operation.Parameters[item].In == ParameterInputType.Query:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in kwargs:
                query_params[item] = str(kwargs[var_name])

    if token:
        headers['Authorization'] = f'Bearer {token}'

    headers.update({'Accept-Language': locale, 'Accept': format})

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:

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

        if result_type:
            return TypedHttpResult[result_type](response.status,
                                                dict_to_object(result, result_type),
                                                dict(response.headers))
        else:
            return HttpResult(response.status,
                              result,
                              dict(response.headers))


def invoke_inter_service_operation_sync(operation_id: str, *,
                                        payload: Optional[Any] = None,
                                        token: Optional[str] = None,
                                        result_type: Optional[Type[T]] = None,
                                        locale='en-US',
                                        format='application/json',
                                        **kwargs) -> Union[HttpResult, TypedHttpResult[T]]:
    operation: RestfulOperation = service_invoker.operations.get(operation_id)

    if not operation:
        raise InterServiceError(f"There is no operation with id {operation_id}", 404)

    url = service_invoker.base_url + operation.EndPoint.format(
        **{p: kwargs.get(p) for p in kwargs if
           p in operation.Parameters and
           operation.Parameters[p].In == ParameterInputType.Path and
           p in operation.Parameters})

    headers = {}
    query_params = {}
    for item in operation.Parameters:
        if operation.Parameters[item].In == ParameterInputType.Header:
            var_name = item.replace('X-', '').replace('-', '_').lower()
            if var_name in kwargs:
                headers[item] = str(kwargs[var_name])
        elif operation.Parameters[item].In == ParameterInputType.Query:
            var_name = item.replace('$', '').replace('-', '_').lower()
            if var_name in kwargs:
                query_params[item] = str(kwargs[var_name])

    if token:
        headers['Authorization'] = f'Bearer {token}'

    headers.update({'Accept-Language': locale, 'Accept': format})

    with requests.Session() as session:

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

        if result_type:
            return TypedHttpResult[result_type](response.status_code,
                                                dict_to_object(result, result_type),
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
