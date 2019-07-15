from typing import Any

import rapidjson
import umsgpack

from catalyst.constants import MimeTypes
from catalyst.dispatcher import deserialization_handler


@deserialization_handler(MimeTypes.JSON)
def rapid_json_deserializer(data: str) -> Any:
    return rapidjson.loads(data, datetime_mode=rapidjson.DM_ISO8601) if data else {}


@deserialization_handler(MimeTypes.MessagePack)
def message_pacK_deserializer(data: str) -> Any:
    return umsgpack.loads(data) if data else {}

