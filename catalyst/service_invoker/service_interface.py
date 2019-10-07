from http import HTTPStatus
from typing import Dict, Optional, NamedTuple, Any

import aiohttp

from catalyst import service_invoker
from catalyst.constants import HeaderKeys
from catalyst.dispatcher import deserialize
from catalyst.service_invoker.errors import InterServiceError

from catalyst.service_invoker.types import ParameterInputType, RestfulOperation
import requests


class HttpResult(NamedTuple):
    Status: int
    Body: Any
    Headers: Dict[str, str]


async def invoke_inter_service_operation(operation_id: str, *, payload: Optional[Any] = None, **kwargs) -> HttpResult:
    operation: RestfulOperation = service_invoker.operations.get(operation_id)
    url = service_invoker.base_url + operation.EndPoint.format(
        **{p: kwargs.get(p) for p in kwargs if
           operation.Parameters[p].In == ParameterInputType.Path and p in operation.Parameters})
    headers = {p: kwargs.get(p) for p in kwargs if
               operation.Parameters[p].In == ParameterInputType.Header and p in operation.Parameters}

    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(verify_ssl=False)) as session:

        response = await session.request(operation.Method,
                                         url,
                                         json=payload,
                                         headers=headers,
                                         params={p: kwargs.get(p) for p in operation.Parameters if
                                                 operation.Parameters[p].In == ParameterInputType.Query})
        if HeaderKeys.ContentType in response.headers:
            content_type, *_ = response.headers[HeaderKeys.ContentType].split(';')
            return HttpResult(response.status,
                              deserialize(await response.content.read(), content_type),
                              response.headers)
        else:
            return HttpResult(response.status, await response.json(), response.headers)


def invoke_inter_service_operation_sync(operation_id: str, *, payload: Optional[Any] = None, **kwargs) -> HttpResult:
    operation: RestfulOperation = service_invoker.operations.get(operation_id)
    url = service_invoker.base_url + operation.EndPoint.format(
        **{p: kwargs.get(p) for p in kwargs if
           operation.Parameters[p].In == ParameterInputType.Path and p in operation.Parameters})
    headers = {p: kwargs.get(p) for p in kwargs if
               operation.Parameters[p].In == ParameterInputType.Header and p in operation.Parameters}

    with requests.Session() as session:

        response = session.request(operation.Method,
                                   url,
                                   json=payload,
                                   headers=headers,
                                   params={p: kwargs.get(p) for p in operation.Parameters if
                                           operation.Parameters[p].In == ParameterInputType.Query})
        if HeaderKeys.ContentType in response.headers:
            content_type, *_ = response.headers[HeaderKeys.ContentType].split(';')
            return HttpResult(response.status_code,
                              deserialize(response.content, content_type),
                              response.headers)
        else:
            return HttpResult(response.status_code, response.json(), response.headers)


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
