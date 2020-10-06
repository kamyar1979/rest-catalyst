from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional, Dict, Tuple, Any


@dataclass
class SwaggerInfo:
    Host: str
    Schemes: Tuple[str, ...]
    Tags: Tuple[Dict[str, str], ...]
    Timeout: int = 0
    RetryOnFailure: Optional[Dict[str, Any]] = None


class ParameterInputType(Enum):
    Query = 'query'
    Path = 'path'
    Body = 'body'
    Header = 'header'
    FormData = 'formData'


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
