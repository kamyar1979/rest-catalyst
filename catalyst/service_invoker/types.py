from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional, Dict, Tuple, Any


class SecurityType(Enum):
    Basic = 'basic'
    ApiKey = 'apiKey'
    OAuth = 'oauth2'


class ParameterInputType(Enum):
    Query = 'query'
    Path = 'path'
    Body = 'body'
    Header = 'header'
    FormData = 'formData'


@dataclass
class ApiSecurity:
    Type: SecurityType
    In: ParameterInputType
    Name: str


@dataclass
class SwaggerInfo:
    Host: str
    Schemes: Tuple[str, ...]
    Tags: Tuple[Dict[str, str], ...]
    Timeout: int = 0
    RetryOnFailure: Optional[Dict[str, Any]] = None
    BasePath: Optional[str] = None
    SecurityDefinitions: Optional[Dict[str, ApiSecurity]] = None
    Security: Optional[str] = None
    Proxy: Optional[str] = None


class ParameterInfo(NamedTuple):
    In: ParameterInputType
    Type: Optional[str]


@dataclass
class RestfulOperation:
    EndPoint: str
    Method: str
    Parameters: Optional[Dict[str, ParameterInfo]]
    CacheDuration: int = 0
    Timeout: int = 0
    RetryOnFailure: Optional[Dict[str, Any]] = None


@dataclass
class OpenAPI:
    Info: SwaggerInfo
    Operations: Dict[str, RestfulOperation]
