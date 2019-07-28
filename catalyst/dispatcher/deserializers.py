from typing import Any

import rapidjson
import umsgpack
from cbor import cbor

from catalyst.constants import MimeTypes
from catalyst.dispatcher import deserialization_handler


@deserialization_handler(MimeTypes.JSON)
def deserialize_JSON(data: str) -> Any:
    return rapidjson.loads(data, datetime_mode=rapidjson.DM_ISO8601) if data else {}


@deserialization_handler(MimeTypes.MessagePack)
def deserialize_MsgPack(data: bytes) -> Any:
    return umsgpack.loads(data) if data else {}


@deserialization_handler(MimeTypes.CBOR)
def deserliaize_CBOR(data: bytes) -> Any:
    return cbor.loads(data) if data else {}
