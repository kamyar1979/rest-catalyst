from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
import os
import gettext
from importlib import import_module
from lib.constants import ConfigKeys, DEFAULT_LOCALE, DEFAULT_CHARSET
import logging.config

from lib.errors import ApiError
from lib.extensions import serialize

load_dotenv()

app = Flask(__name__)
CORS(app)

app.config.update({key: int(os.getenv(key)) if os.getenv(key).isdecimal() else os.getenv(key) for key in os.environ})


def register_handlers():
    """
    Walking through the directories recursively and registering handlers. When importing a handler,
    all its required modules including repository and model would be registered.
    :return:
    """
    for f, g, h in os.walk(os.getcwd()):
        if 'handler.py' in h:
            import_module('.handler', os.path.relpath(f, os.getcwd()).replace('/', '.'))

    module = import_module('infrastructure.data_abstraction')
    module.create_schema()


def register_error_handlers():
    app.register_error_handler(ApiError, lambda e: (serialize(e.purified()), e.http_status_code))


def init_i18n():
    """
    Initialize localization and translation files
    :return:
    """
    global DefaultLocale, DefaultCharset

    DefaultLocale = os.getenv(ConfigKeys.DefaultLocale) or DEFAULT_LOCALE
    DefaultCharset = os.getenv(ConfigKeys.DefaultCharset) or DEFAULT_CHARSET

    fa = gettext.translation(DefaultLocale.replace('-', '_'), localedir='locale', languages=['fa'])
    fa.install()


def init_logging():
    logging.config.fileConfig(app.config[ConfigKeys.LoggingConfig])


init_logging()
init_i18n()
register_handlers()
register_error_handlers()