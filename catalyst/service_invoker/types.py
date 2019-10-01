from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, Optional, Dict


class ParameterInputType(Enum):
    Query = 'query'
    Path = 'path'
    Body = 'body'
    Header = 'header'


class ParameterInfo(NamedTuple):
    In: ParameterInputType
    Type: Optional[str]


class RestfulOperation(NamedTuple):
    EndPoint: str
    Method: str
    Parameters: Optional[Dict[str, ParameterInfo]]


@dataclass
class ErrorDTO:
    Code: Optional[int] = None
    Message: Optional[str] = None
    Url: Optional[str] = None
