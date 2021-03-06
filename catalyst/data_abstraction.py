import inspect
import logging
from contextlib import contextmanager

from flask_sqlalchemy import models_committed
from sqlalchemy.orm import Session, Query
from sqlalchemy import func, Column
from typing import Callable, Tuple, Union, AnyStr, TypeVar, List, Type, Optional, Generator, Any
from toolz import compose

from catalyst.adapters import ODataQueryAdapter
from catalyst.constants import ConfigKeys, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from . import db, app, signals

logger = logging.getLogger('orm')

T = TypeVar('T')


@contextmanager
def session_context(must_expunge=False,
                    use_local_context=False,
                    use_scoped_session=True) -> Generator[Session, None, None]:
    if use_scoped_session:
        db_session: Session = db.session
    else:
        session_factory = db.session.session_factory
        db_session: Session = session_factory()

    logger.debug('Initiated session %d', id(db_session))
    yield db_session
    if must_expunge:
        db_session.expunge_all()
    if use_local_context:
        db_session.commit()
    if not use_scoped_session:
        db_session.close()
    logger.debug('Closed session %d', id(db_session))


def call_db_func(db_session: Session):
    """
    Runs an RDBMS function getting arguments and returning the result
    You can call function named MyFunc using the syntax repo.func.MyFunc(arg1, arg2)
    :return: Teh result of the RDBMS function
    """

    class FunctionWrapper:

        def __init__(self, func_name=None):
            if func_name:
                self.func_name = func_name

        def __getattr__(self, item):
            return FunctionWrapper(item)

        def __call__(self, *args, **kwargs):
            return db_session.query(getattr(func, self.func_name)(**kwargs))

    return FunctionWrapper()


def search_using_OData(db_session: Session, data: AnyStr, cls: type, content_type: str = 'uri',
                       adapter_type=ODataQueryAdapter, *,
                       query_options: Optional[Union[Callable[[Query], Query],
                                                     Tuple[Callable[[Query], Query], ...]]] = None,
                       count_options: Optional[Union[Callable[[Query], Query],
                                                     Tuple[Callable[[Query], Query], ...]]] = None,
                       extra_columns: Tuple[Column, ...] = (),
                       expunge_after_all=True,
                       use_baked_queries=False,
                       convenient=True,
                       count_only=False,
                       use_row_number=False) -> Union[Tuple[List[T], int], int]:
    """
    Parses OData input and returns list of model object
    :param db_session: SQLAlchemy session to use for query
    :param data: OData input data, currently QueryString
    :param cls: Main entity type for query
    :param content_type: Teh format of OData input
    :param adapter_type: Adapter type which can be OData or else
    :param query_options: Query Options (extra filters, join...) for main query
    :param count_options: Query Options for count query
    :param extra_columns: Add more column output
    :param expunge_after_all: Kill ORM session after getting the result
    :param use_baked_queries: Use bakery for caching ORm queries
    :param convenient: Use security conveniences when trying to query database
    :param count_only: Just return the count not the results
    :param use_row_number: Uses SQL row_number window function for pagination (not limit/offset)
    :return:
    """
    try:

        adapter: ODataQueryAdapter = adapter_type(cls)
        adapter.use_row_number = use_row_number
        adapter.extra_columns = extra_columns
        adapter.logger = logger
        adapter.parse(**{content_type: data})
        if convenient:
            adapter.perform_convenience(app.config.get(ConfigKeys.MaxPageSize) or MAX_PAGE_SIZE,
                                        app.config.get(ConfigKeys.DefaultPageSize) or DEFAULT_PAGE_SIZE)

        options = compose(*query_options) if isinstance(query_options, Tuple) else query_options

        if count_options:
            count_options = compose(*count_options) if isinstance(count_options, Tuple) else count_options
        else:
            count_options = options

        if adapter.fields:
            adapter.fields += extra_columns

        if count_only:
            return adapter.create_count_func(db_session, use_baked_queries=use_baked_queries,
                                             opt=count_options)()
        else:
            return (adapter.create_func(db_session, use_baked_queries=use_baked_queries, opt=options)(),
                    adapter.create_count_func(db_session, use_baked_queries=use_baked_queries,
                                              opt=count_options)())
    finally:
        if expunge_after_all:
            db_session.expunge_all()


def get_by_slug(cls: Type[T],
                session: Session,
                slug: str,
                natural_key: str = 'slug',
                query_options: Optional[Callable[[Query], Query]] = None) -> T:
    if query_options:
        return query_options(session.query(cls).filter(getattr(cls, natural_key) == slug)).one_or_none()
    else:
        return session.query(cls).filter(getattr(cls, natural_key) == slug).one_or_none()


def check_slug_exists(cls: Type[T],
                      session: Session,
                      slug: str,
                      natural_key: str = 'slug',
                      query_options: Optional[Callable[[Query], Query]] = None) -> bool:
    if query_options:
        return query_options(session.query(cls.query.filter(getattr(cls, natural_key) == slug))).exists().scalar()
    else:
        return session.query(cls.query.filter(getattr(cls, natural_key) == slug).exists()).scalar()


def create_schema():
    db.create_all()


def register_signal(callback: Callable[[Any, str], None]):
    sig = inspect.signature(callback)
    func_args = sig.parameters
    param_names = tuple(func_args.keys())
    model_type = func_args[param_names[0]].annotation

    signals[model_type] = callback


def notify_subscribers(_app, changes):
    unregister : List[type] = []
    for target, op in changes:
        for t in signals:
            if isinstance(target, t):
                if not signals[t](target, op):
                   unregister.append(t)
    for t in unregister:
        del signals[t]


models_committed.connect(notify_subscribers, app)
