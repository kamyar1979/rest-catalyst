import gettext
import logging.config
import os
from importlib import import_module

from catalyst.constants import ConfigKeys, DEFAULT_LOCALE, DEFAULT_CHARSET
from catalyst.errors import ApiError
from catalyst.extensions import serialize

db = None
app = None


def register_application(flask_application, database):
    global app, db
    app = flask_application
    db = database


def register_handlers():
    """
    Walking through the directories recursively and registering handlers. When importing a handler,
    all its required modules including repository and model would be registered.
    :return:
    """
    for f, g, h in os.walk(os.getcwd()):
        if 'handler.py' in h:
            import_module('.handler', os.path.relpath(f, os.getcwd()).replace('/', '.'))

    module = import_module('catalyst.data_abstraction')
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
