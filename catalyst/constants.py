import os

SRID = 4326
DEFAULT_LOCALE = 'fa-IR'
DEFAULT_TIMEZONE = 'Asia/Tehran'
DEFAULT_CHARSET = 'utf-8'
ODATA_COUNT = 'odata.count'
ODATA_VALUE = 'value'
BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DEBUG = os.getenv('FLASK_ENV', 'development') == 'development'

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 10
MICRO_SERVICE_NAME = "ProductService"


class PostGreSQL:
    EPOCH = 'epoch'
    AtTimeZone = 'AT TIME ZONE'


class ConfigKeys:
    LoggingConfig = "LOGGING_CONFIG"
    NTPServer = "TIME_SERVER"
    DefaultPageSize = "DEFAULT_PAGE_SIZE"
    MaxPageSize = "MAX_PAGE_SIZE"
    DefaultLocale = "DEFAULT_LOCALE"
    DefaultCharset = "DEFAULT_CHARSET"
    BaseUri = "BASE_URI"
    ServiceDiscoveryUrl = "SERVICE_DISCOVERY_URL"
    SwaggerUrl = "SWAGGER_URL"
    SentryDSN = 'SENTRY_DSN'


class RegExPatterns:
    Email = r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,4}'
    Url = r'(\w+\://)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)'
    CellNumber = r'(0|\+98)?([ ]|,|-|[()]){0,2}9[0-9]([ ]|,|-|[()]){0,2}(?:[0-9]([ ]|,|-|[()]){0,2}){8}'
    PhoneNumber = r'[+]*[(]{0,1}[۰-۹|0-9]{4,}[)]{0,1}[-\s\./0-9]*'
    Locale = '[a-z]{2}-[A-Z]{2}'


class HeaderKeys:
    ContentType = 'Content-Type'
    Accept = 'Accept'
    AcceptLanguage = 'Accept-Language'
    ContentLanguage = 'Content-Language'
    Serialization = 'X-Serialization'


class MimeTypes:
    JSON = 'application/json'
    MessagePack = 'application/msgpack'
    CBOR = 'application/cbor'
    URLEncoded = 'application/x-www-form-urlencoded'
    Html = 'text/html'


class SerializerFlagString:
    IncludeNulls = 'IncludeNulls'
    ReplaceNullsWithEmpty = 'ReplaceNullsWithEmpty'
    IgnoreLocaleCalendar = "IgnoreLocaleCalendar"
    IgnoreLocaleTimeZone = "IgnoreLocaleTimeZone"


class ErrorMessages:
    ServiceUnavailable = "Service temporarily unavailable. Please try again later."
    DatabaseError = "Database error occurred."
