import yaml
from typing import Dict

from catalyst.service_invoker.types import RestfulOperation, ParameterInputType, ParameterInfo, SwaggerInfo


def get_swagger_info(swagger: dict) -> SwaggerInfo:
    return SwaggerInfo(swagger.get('host'),
                       swagger.get('tags'),
                       swagger.get('x-timeout') or 0,
                       swagger.get('x-retry-on-failure') or 0)


def get_operation_info(swagger: dict, path: str, action: str) -> RestfulOperation:
    swagger_info = get_swagger_info(swagger)
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


def get_swagger_operations(file_handle) -> Dict[str, RestfulOperation]:
    swagger = yaml.load(file_handle, Loader=yaml.FullLoader)
    return {swagger['paths'][path][action]['operationId']: get_operation_info(swagger, path, action) for path in
            swagger['paths'] for action in swagger['paths'][path] if 'operationId' in swagger['paths'][path][action]}
