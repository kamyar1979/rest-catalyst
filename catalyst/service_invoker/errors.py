from http import HTTPStatus
from typing import Union, Any, Tuple

from catalyst import ApiError


class InterServiceError(ApiError):
    pass