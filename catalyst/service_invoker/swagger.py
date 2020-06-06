import yaml
from typing import Optional
from .types import SwaggerInfo

swagger_info: Optional[SwaggerInfo] = None

from catalyst.service_invoker.types import RestfulOperation, ParameterInputType, ParameterInfo, SwaggerInfo, OpenAPI


def get_swagger_info(swagger: dict) -> SwaggerInfo:
    return SwaggerInfo(swagger.get('host'),
                       swagger.get('tags'),
                       swagger.get('x-timeout') or 0,
                       swagger.get('x-retry-on-failure') or 0)


def get_operation_info(swagger: dict, path: str, action: str) -> RestfulOperation:
    path_info = swagger['paths'][path]
    action_info = path_info[action]
    params = action_info.get('parameters') or {}
    cache_duration = action_info.get('x-cache-duration') or 0
    timeout = action_info.get('x-timeout') or swagger_info.Timeout
    retry_on_failure = action_info.get('x-retry-on-failure') or swagger_info.RetryOnFailure
    return RestfulOperation(path, action,
                            {p['name']: ParameterInfo(ParameterInputType(p['in']), p.get('type')) for p in params},
                            cache_duration,
                            timeout,
                            retry_on_failure)


def get_openAPI_info(file_handle) -> OpenAPI:
    global swagger_info
    swagger = yaml.load(file_handle, Loader=yaml.FullLoader)
    swagger_info = get_swagger_info(swagger)
    return OpenAPI(swagger_info,
                   {swagger['paths'][path][action]['operationId']: get_operation_info(swagger, path, action) for path in
                    swagger['paths'] for action in swagger['paths'][path] if
                    'operationId' in swagger['paths'][path][action]})
