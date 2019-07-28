import logging
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker, Session, Query
from sqlalchemy import func, Column
from typing import Callable, Tuple, Union, AnyStr, TypeVar, List, Type, Optional, Generator
from toolz import compose

from catalyst.adapters import ODataQueryAdapter
from catalyst.constants import ConfigKeys, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from . import db, app

logger = logging.getLogger('orm')

session_factory = sessionmaker(bind=db.engine)

T = TypeVar('T')


@contextmanager
def session_context(must_expunge=False, use_local_context=False) -> Generator[Session, None, None]:
    db_session: Session = db.session
    logger.debug('Initiated session %d', id(db_session))
    yield db_session
    if must_expunge:
        db_session.expunge_all()
    if use_local_context:
        db_session.commit()
    logger.debug('Closed session %d', id(db_session))


def call_db_func(db_session: Session):
    """
    Runs an RDBMS function getting arguments and returning the result
    You can call function named MyFunc using the syntax repo.func.MyFunc(arg1, arg2)
    :return: Teh result of the RDBMS function
    """

    class FunctionWrapper(object):

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
                       count_only=False) -> Union[Tuple[List[T], int], int]:
    """
    Parses OData input and returns list of model object
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
    :return:
    """
    try:

        adapter: ODataQueryAdapter = adapter_type(cls)
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


def get_by_slug(cls: Type[T], session: Session, slug: str, natural_key: str = 'slug') -> T:
    return session.query(cls).filter(getattr(cls, natural_key) == slug).one_or_none()


def check_slug_exists(cls: Type[T], session: Session, slug: str, natural_key: str = 'slug') -> bool:
    return session.query(cls.query.filter(getattr(cls, natural_key) == slug).exists()).scalar()


def create_schema():
    db.create_all()
