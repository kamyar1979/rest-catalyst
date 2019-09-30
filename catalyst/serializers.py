from typing import Any
import rapidjson
import umsgpack
from cbor import cbor
from json2html import json2html

from catalyst.constants import MimeTypes
from catalyst.dispatcher import serialization_handler


@serialization_handler(MimeTypes.MessagePack)
def serilize_MsgPack(data: Any) -> bytes:
    return umsgpack.dumps(data)


@serialization_handler(MimeTypes.JSON)
def serilize_Json(data: Any) -> str:
    return rapidjson.dumps(data, ensure_ascii=False, sort_keys=True)


@serialization_handler(MimeTypes.CBOR)
def serilize_Cbor(data: Any) -> bytes:
    return cbor.dumps(data)


@serialization_handler(MimeTypes.Html)
def serilize_Html(data: Any) -> str:
    return json2html.convert(json = rapidjson.dumps(data, ensure_ascii=False, sort_keys=True))
