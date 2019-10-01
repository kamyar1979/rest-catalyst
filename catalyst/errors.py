from dataclasses import dataclass
from http import HTTPStatus
from typing import Tuple, Any, Union, Optional


@dataclass
class ErrorDTO:
    Code: Optional[int] = None
    Message: Optional[str] = None
    Uri: Optional[str] = None

class ApiError(Exception):

    def __init__(self, message: str,
                 code: int,
                 params: Union[Any, Tuple[Any, ...]] = None,
                 uri: str = None,
                 http_status_code: int = HTTPStatus.EXPECTATION_FAILED):
        if params:
            super().__init__((_(message)).format(*params))
        else:
            super().__init__(_(message))
        self.code = code
        self.uri = uri
        self.http_status_code = http_status_code

    def purified(self):
        return ErrorDTO(Code=self.code, Message=str(self), Uri=self.uri)

