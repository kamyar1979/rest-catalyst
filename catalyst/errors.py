from dataclasses import dataclass
from enum import IntEnum
from http import HTTPStatus
from typing import Tuple, Any, Optional


class ErrorSeverity(IntEnum):
    Warning = 1
    Error = 2
    Fatal = 3


@dataclass
class ErrorDTO:
    Code: Optional[int] = None
    Message: Optional[str] = None
    Uri: Optional[str] = None
    severity: Optional[ErrorSeverity] = None


class ApiError(Exception):

    def __init__(self, message: str,
                 code: int,
                 params: Optional[Tuple[Any, ...]] = None,
                 uri: str = None,
                 http_status_code: int = HTTPStatus.EXPECTATION_FAILED,
                 severity: ErrorSeverity = ErrorSeverity.Error):
        if params:
            super().__init__((_(message)).format(*params))
        else:
            super().__init__(_(message))
        self.code = code
        self.uri = uri
        self.http_status_code = http_status_code
        self.severity = severity

    def purified(self):
        return ErrorDTO(Code=self.code, Message=str(self), Uri=self.uri, severity=self.severity)
