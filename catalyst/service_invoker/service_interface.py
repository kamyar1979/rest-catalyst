from typing import Dict, Optional, NamedTuple, Any

import aiohttp
import rapidjson

from catalyst import service_invoker
from catalyst.constants import HeaderKeys
from catalyst.dispatcher import deserialize


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
                               json=rapidjson.dumps(payload) if payload else '',
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
                               json=rapidjson.dumps(payload) if payload else '',
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