import rapidjson
from dataclasses import asdict, is_dataclass, dataclass

from flask import request, make_response, g, Response
import umsgpack
from cbor import cbor
from typing import Iterable, Any, get_type_hints
import collections
from datetime import datetime, date, time
from decimal import Decimal
from catalyst.constants import RegExPatterns, MimeTypes, HeaderKeys, ODATA_COUNT, ODATA_VALUE, SerializerFlags, \
    DEFAULT_LOCALE, DEFAULT_CHARSET
from khayyam import JalaliDatetime, JalaliDate
from pytz import country_timezones, timezone
import re


@dataclass
class SerializationFlags:
    """
    Flags read from http header and changes serialization
    """
    IncludeNulls: bool = False
    ReplaceNoneWithEmptyString: bool = False

    def __init__(self, flags: str):
        if flags:
            self.IncludeNulls = SerializerFlags.IncludeNulls in flags
            self.ReplaceNoneWithEmptyString = SerializerFlags.ReplaceNullsWithEmpty in flags

    @property
    @classmethod
    def Default(cls):
        return cls.__new__(cls).__init__('')


def get_request_timezone() -> timezone:
    if 'timezone' not in g:
        m = re.match(RegExPatterns.Locale, request.headers.get(HeaderKeys.AcceptLanguage) or DEFAULT_LOCALE)
        if m:
            locale = m.group()
        else:
            locale = DEFAULT_LOCALE
        country: str = locale[-2:]
        g.timezone = timezone(country_timezones[country][0])

    return g.timezone


def to_dict(obj: Any,
            flags: SerializationFlags = SerializationFlags.Default,
            locale: str = DEFAULT_LOCALE) -> Any:
    """
    Converts a Python object to dictionary, with recursion over the inner objects
    :param obj: Input Python object
    :param flags: Flags applicable for converting, as like allow nulls
    :param locale: Localization info as like time-zone, calendar and date/time format
    :return: Python dictionary
    """

    if obj is None:
        if flags.ReplaceNoneWithEmptyString:
            return ''
        else:
            return

    m = re.match(RegExPatterns.Locale, locale)
    t = type(obj)
    if m:
        locale = m.group()
    else:
        locale = DEFAULT_LOCALE

    if is_dataclass(obj):
        annotations = get_type_hints(type(obj))
        res = asdict(obj)

        return {k: to_dict(res[k], flags=flags, locale=locale)
                for k in res
                if res[k] is not None
                or flags.IncludeNulls
                or (flags.ReplaceNoneWithEmptyString and annotations[k]) == str}

    elif t in (int, str, bytes, float, bool):
        return obj
    elif t is Decimal:
        return float(obj)
    elif t in (datetime, date, time):
        country: str = locale[-2:]
        tz = timezone(country_timezones[country][0])
        if locale == 'fa-IR':
            if t is datetime:
                if obj.tzinfo is None:
                    return JalaliDatetime(tz.fromutc(obj)).isoformat()
                else:
                    return JalaliDatetime(obj).isoformat()
            elif t is date:
                return JalaliDate(obj).isoformat()
            elif t is time:
                if obj.tzinfo is None:
                    return tz.fromutc(obj)
                else:
                    return obj
        else:
            return obj.isoformat()
    elif isinstance(obj, collections.Mapping):
        return {k: to_dict(obj[k], flags=flags, locale=locale)
                for k in obj
                if obj[k] is not None
                or flags.IncludeNulls}

    elif isinstance(obj, Iterable) or isinstance(obj, collections.Sequence):
        return t(to_dict(item, flags=flags, locale=locale)
                 for item in obj
                 if item is not None
                 or flags.IncludeNulls)
    else:
        attribute_list = tuple(k for k in vars(obj))
        result = {}
        for attr in attribute_list:
            if not attr.startswith('_'):
                result[attr] = to_dict(getattr(obj, attr), flags=flags, locale=locale)
        return result


def serialize(result: object) -> Response:
    """
    Serialize Python object to string or byte-string data adding required headers
    :param result: Flask response
    :return: Python object or dictionary
    """
    flags = SerializationFlags(request.headers.get(HeaderKeys.Serialization))

    data = to_dict(result, flags,
                   locale=request.headers.get(HeaderKeys.AcceptLanguage) or DEFAULT_LOCALE)

    accept_header = request.headers.get(HeaderKeys.Accept) or MimeTypes.JSON

    if MimeTypes.MessagePack in accept_header:
        resp = make_response(umsgpack.dumps(data))
        resp.headers[HeaderKeys.ContentType] = MimeTypes.MessagePack
        return resp
    elif MimeTypes.CBOR in accept_header:
        resp = make_response(cbor.dumps(data))
        resp.headers[HeaderKeys.ContentType] = MimeTypes.CBOR
        return resp
    else:
        resp = make_response(rapidjson.dumps(data, ensure_ascii=False, sort_keys=True))
        resp.headers[HeaderKeys.ContentType] = f'{MimeTypes.JSON}; charset={DEFAULT_CHARSET}'
        return resp


def odata(count: int, items: Iterable):
    return {ODATA_COUNT: count,
            ODATA_VALUE: items}


def get_header_cache_key():
    return hash(frozenset(filter(lambda h: h[0].startswith('Accept') or h[0].startswith('X-'), request.headers)))
