from io import StringIO

import yaml
from typing import Optional, Union, AnyStr, Dict, Any
from catalyst.service_invoker.types import RestfulOperation, ParameterInputType, ParameterInfo, SwaggerInfo, OpenAPI, \
    ApiSecurity
from durations import Duration

swagger_info: Optional[SwaggerInfo] = None


def parse_duration(value: Union[None, str, int]) -> int:
    if value:
        if type(value) == int:
            return value
        else:
            return int(Duration(value).to_seconds())
    else:
        return 0


def parse_security_definitions(security_definitions: Optional[Dict[str, Any]] = None) -> Dict[str, ApiSecurity]:
    if security_definitions:
        return {k: ApiSecurity(security_definitions[k]['type'],
                               ParameterInputType(security_definitions[k]['in']),
                               security_definitions[k]['name']) for k in security_definitions}

def get_swagger_info(swagger: Dict[str, Any]) -> SwaggerInfo:
    return SwaggerInfo(Host=swagger.get('host'),
                       Schemes=swagger.get('schemes'),
                       Tags=swagger.get('tags'),
                       Timeout=swagger.get('x-timeout') or 0,
                       RetryOnFailure=swagger.get('x-retry-on-failure'),
                       BasePath=swagger.get('basePath') or '',
                       SecurityDefinitions=parse_security_definitions(swagger.get('securityDefinitions')),
                       Security=swagger.get('security'))


def get_operation_info(swagger: dict, path: str, action: str) -> RestfulOperation:
    path_info = swagger['paths'][path]
    action_info = path_info[action]
    params = action_info.get('parameters') or {}
    alien_cache = parse_duration(action_info.get('x-alien-cache'))
    timeout = action_info.get('x-timeout') or swagger_info.Timeout
    retry_on_failure = action_info.get('x-retry-on-failure') or swagger_info.RetryOnFailure
    return RestfulOperation(path, action,
                            {p['name']: ParameterInfo(ParameterInputType(p['in']), p.get('type')) for p in params},
                            alien_cache,
                            timeout,
                            retry_on_failure)


def get_openAPI_info(file_handle: Union[StringIO, AnyStr]) -> OpenAPI:
    global swagger_info
    swagger = yaml.load(file_handle, Loader=yaml.FullLoader)
    swagger_info = get_swagger_info(swagger)
    return OpenAPI(swagger_info,
                   {swagger['paths'][path][action]['operationId']: get_operation_info(swagger, path, action) for path in
                    swagger['paths'] for action in swagger['paths'][path] if
                    'operationId' in swagger['paths'][path][action]})
