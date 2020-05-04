import yaml
from typing import Dict

from catalyst.service_invoker.types import RestfulOperation, ParameterInputType, ParameterInfo


def get_operation_info(swagger: dict, path: str, action: str) -> RestfulOperation:
    path_info = swagger['paths'][path]
    action_info = path_info[action]
    params = action_info.get('parameters') or {}
    cache_duration = action_info.get('x-cache-duration') or 0
    return RestfulOperation(path, action,
                            {p['name']: ParameterInfo(ParameterInputType(p['in']), p.get('type')) for p in params},
                            cache_duration)


def get_swagger_operations(file_handle) -> Dict[str, RestfulOperation]:
    swagger = yaml.load(file_handle, Loader=yaml.FullLoader)
    return {swagger['paths'][path][action]['operationId']: get_operation_info(swagger, path, action) for path in
            swagger['paths'] for action in swagger['paths'][path] if 'operationId' in swagger['paths'][path][action]}
