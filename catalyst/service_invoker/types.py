from enum import Enum
from typing import NamedTuple, Optional, Dict, Tuple


class SwaggerInfo(NamedTuple):
    Host: str
    Tags: Tuple[Dict[str, str], ...]
    Timeout: int = 0
    RetryOnFailure: int = 0


class ParameterInputType(Enum):
    Query = 'query'
    Path = 'path'
    Body = 'body'
    Header = 'header'
    FormData = 'formData'


class ParameterInfo(NamedTuple):
    In: ParameterInputType
    Type: Optional[str]


class RestfulOperation(NamedTuple):
    EndPoint: str
    Method: str
    Parameters: Optional[Dict[str, ParameterInfo]]
    CacheDuration: int = 0
    Timeout: int = 0
    RetryOnFailure: int = 0
