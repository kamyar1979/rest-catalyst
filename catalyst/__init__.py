import gettext
import logging
import logging.config
import os
from importlib import import_module
from typing import Optional, Tuple, Callable, Dict

import sentry_sdk
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sentry_sdk.integrations.flask import FlaskIntegration
from sqlalchemy.exc import SQLAlchemyError

from catalyst.constants import ConfigKeys, DEFAULT_LOCALE, DEFAULT_CHARSET, ErrorMessages
from catalyst.errors import ApiError, ErrorDTO
from catalyst.extensions import serialize

logger = logging.getLogger('Catalyst')

db: Optional[SQLAlchemy] = None
app: Optional[Flask] = None
signals: Dict[type, Callable[[object, str], None]] = {}
DefaultLocale: str = ''
DefaultCharset: str = ''
default_directory_exclude: Tuple[str, ...] = ('__pycache__', 'node_modules')


def register_application(flask_application: Flask,
                         database: SQLAlchemy):
    global app, db
    app = flask_application
    db = database


def register_handlers(exclude_directories: Tuple[str, ...] = ()):
    """
    Walking through the directories recursively and registering handlers. When importing a handler,
    all its required modules including repository and model would be registered.
    :return:
    """
    for f, g, h in os.walk(os.getcwd()):
        [g.remove(d) for d in g if d in (default_directory_exclude + exclude_directories) or d.startswith('.')]
        if 'handler.py' in h:
            import_module('.handler', os.path.relpath(f, os.getcwd()).replace('/', '.'))

    module = import_module('catalyst.data_abstraction')

    module.create_schema()

    register_error_handlers()


def database_error_handler(e):
    logger.error(e)
    if db.session.is_active:
        db.session.rollback()
    return serialize(ErrorDTO(Code=100500, Message=ErrorMessages.DatabaseError))


def handle_error(e: ApiError):
    if db.session.is_active:
        db.session.rollback()
    return serialize(e.purified()), e.http_status_code


def register_error_handlers():

    app.register_error_handler(ApiError, handle_error)
    if app.config['FLASK_ENV'].casefold() != 'Development'.casefold():
        app.register_error_handler(SQLAlchemyError,
                                   lambda e: serialize(ErrorDTO(Code=100500, Message=ErrorMessages.DatabaseError)))
    # app.register_error_handler(Exception,
    #                            lambda e: serialize(ErrorDTO(Code=100500, Message=str(e))))


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


def init_sentry_logging(enable_flask_integration: bool = True):
    sentry_sdk.init(
        dsn=app.config[ConfigKeys.SentryDSN],
        integrations=[FlaskIntegration(), ] if enable_flask_integration else [],
    )
