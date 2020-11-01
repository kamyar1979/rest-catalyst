from enum import Enum
from uuid import UUID

import rapidjson
from dataclasses import asdict, is_dataclass, dataclass

from flask import request, make_response, g, Response
from typing import Iterable, Any, get_type_hints, TypeVar, Dict, Union, Type, Mapping, Generator, Optional
import collections
from datetime import datetime, date, time
from decimal import Decimal

from inflector import Inflector
from shapely.geometry import mapping
from shapely.geometry.base import BaseGeometry

from catalyst.constants import RegExPatterns, MimeTypes, HeaderKeys, SerializerFlagString, ODATA_COUNT, ODATA_VALUE, \
    DEFAULT_LOCALE, DEFAULT_CHARSET
from khayyam import JalaliDatetime, JalaliDate
from pytz import country_timezones, timezone
import re
from . import serializers

from catalyst.dispatcher import registered_serializers


@dataclass
class SerializationFlags:
    """
    Flags read from http header and changes serialization
    """
    IncludeNulls: bool = False
    ReplaceNoneWithEmptyString: bool = False
    IgnoreLocaleCalendar: bool = False
    IgnoreLocaleTimeZone: bool = False

    def __init__(self, flags: str):
        if flags:
            self.IncludeNulls = SerializerFlagString.IncludeNulls in flags
            self.ReplaceNoneWithEmptyString = SerializerFlagString.ReplaceNullsWithEmpty in flags
            self.IgnoreLocaleCalendar = SerializerFlagString.IgnoreLocaleCalendar in flags
            self.IgnoreLocaleTimeZone = SerializerFlagString.IgnoreLocaleTimeZone in flags


def get_request_locale() -> str:
    return request.headers.get(HeaderKeys.AcceptLanguage) or DEFAULT_LOCALE


def get_request_timezone() -> timezone:
    if 'timezone' not in g:
        m = re.match(RegExPatterns.Locale, get_request_locale())
        if m:
            locale = m.group()
        else:
            locale = DEFAULT_LOCALE
        country: str = locale[-2:]
        g.timezone = timezone(country_timezones[country][0])

    return g.timezone


T = TypeVar('T')


def to_dict(obj: T, *,
            flags: SerializationFlags = SerializationFlags(''),
            locale: str = DEFAULT_LOCALE,
            depth: int = 3,
            uuid_hex: bool = True,
            inflection: bool = False,
            datetime_formatter: Optional[str] = None) -> Union[T, Dict[str, Any], Iterable[Dict[str, Any]], None]:
    """
    Converts a Python object to dictionary, with recursion over the inner objects
    :param obj: Input Python object
    :param flags: Flags applicable for converting, as like allow nulls
    :param locale: Localization info as like time-zone, calendar and date/time format
    :return: Python dictionary
    """

    inflector = Inflector()
    if obj is None:
        if flags.ReplaceNoneWithEmptyString:
            return ''
        else:
            return

    if depth == 0:
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

        return {inflector.underscore(k) if inflection else k: to_dict(res[k], flags=flags,
                                                                      locale=locale,
                                                                      depth=depth,
                                                                      inflection=inflection,
                                                                      datetime_formatter=datetime_formatter)
                for k in res
                if res[k] is not None
                or flags.IncludeNulls
                or (flags.ReplaceNoneWithEmptyString and annotations[k]) == str}
    elif issubclass(t, BaseGeometry):
        return mapping(obj)
    elif t in (int, str, bytes, float, bool):
        return obj
    elif issubclass(t, Enum):
        return obj.value
    elif t is Decimal:
        return float(obj)
    elif t is UUID:
        if uuid_hex:
            return obj.hex
        else:
            return obj
    elif t in (datetime, date, time):
        country: str = locale[-2:]
        tz = timezone(country_timezones[country][0])
        if locale == 'fa-IR':
            if t is datetime:
                if flags.IgnoreLocaleCalendar:
                    if flags.IgnoreLocaleTimeZone:
                        return obj.isoformat()
                    if obj.tzinfo is None:
                        return tz.fromutc(obj).isoformat()
                    else:
                        return obj.astimezone(tz)
                else:
                    if datetime_formatter:
                        formatter = lambda d: '{{:{}}}'.format(datetime_formatter).format(d)
                    else:
                        formatter = JalaliDatetime.isoformat

                    if flags.IgnoreLocaleTimeZone:
                        return formatter(JalaliDatetime(obj))
                    if obj.tzinfo is None:
                        return formatter(JalaliDatetime(tz.fromutc(obj)))
                    else:
                        return formatter(JalaliDatetime(obj.astimezone(tz)))
            elif t is date:
                if flags.IgnoreLocaleCalendar:
                    return obj.isoformat()
                else:
                    return JalaliDate(obj).isoformat()
            elif t is time:
                return obj.isoformat()
        else:
            return obj.isoformat()
    elif isinstance(obj, collections.Mapping):
        return {inflector.underscore(k) if inflection else k: to_dict(obj[k],
                                                                      flags=flags,
                                                                      locale=locale,
                                                                      depth=depth - 1,
                                                                      inflection=inflection,
                                                                      datetime_formatter=datetime_formatter)
                for k in obj
                if obj[k] is not None
                or flags.IncludeNulls}

    elif isinstance(obj, Iterable) or isinstance(obj, collections.Sequence):

        gen = (to_dict(item,
                       flags=flags,
                       locale=locale,
                       depth=depth - 1,
                       inflection=inflection,
                       datetime_formatter=datetime_formatter)
               for item in obj
               if item is not None
               or flags.IncludeNulls)

        return t(gen) if isinstance(obj, collections.Sequence) else tuple(gen)
    else:
        return {attr: to_dict(getattr(obj, attr),
                              flags=flags,
                              locale=locale,
                              depth=depth - 1,
                              inflection=inflection,
                              datetime_formatter=datetime_formatter)
                for attr in vars(obj) if not attr.startswith('_')}


def raw_serialize(data: Any, mime_type: str, depth: int = 5, inflection: bool = False):
    if issubclass(type(data), Mapping):
        return registered_serializers[mime_type](data)
    else:
        return registered_serializers[mime_type](to_dict(data,
                                                         flags=SerializationFlags('IgnoreLocaleCalendar'),
                                                         depth=depth,
                                                         inflection=inflection))


def serialize(result: object, depth: int = 5, inflection: bool = False) -> Response:
    """
    Serialize Python object to string or byte-string data adding required headers
    :param result: Flask response
    :return: Python object or dictionary
    """
    flags = SerializationFlags(request.headers.get(HeaderKeys.Serialization))

    data = to_dict(result,
                   flags=flags,
                   locale=request.headers.get(HeaderKeys.AcceptLanguage) or DEFAULT_LOCALE,
                   depth=depth,
                   inflection=inflection)

    accept_header = request.headers.get(HeaderKeys.Accept).split(';') \
        if request.headers.get(HeaderKeys.Accept) else DEFAULT_LOCALE
    if not accept_header:
        accept_content_type, charset = MimeTypes.JSON, DEFAULT_CHARSET
    elif len(accept_header) == 1:
        accept_content_type, charset = accept_header[0], DEFAULT_CHARSET
    else:
        accept_content_type, *_ = accept_header

    # TODO: Try to get charset from accept header
    resp = ''
    for key in registered_serializers:
        if key in accept_content_type:
            resp = make_response(registered_serializers[key](data))
            resp.headers[HeaderKeys.ContentType] = f'{key}; charset={DEFAULT_CHARSET}'

    if not resp:
        resp = make_response(rapidjson.dumps(data, ensure_ascii=False, sort_keys=True))
        resp.headers[HeaderKeys.ContentType] = f'{MimeTypes.JSON}; charset={DEFAULT_CHARSET}'
    return resp


U = TypeVar('U')


def odata(count: int, items: Generator[Type[U], None, None]) -> Dict[str, Union[int, Iterable[Type[U]]]]:
    return {ODATA_COUNT: count,
            ODATA_VALUE: items}


def get_header_cache_key():
    return hash(frozenset(filter(lambda h: h[0].startswith('Accept') or h[0].startswith('X-'), request.headers)))
