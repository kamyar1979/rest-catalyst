import logging
from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker, Session, Query
from sqlalchemy import func, Column
from typing import Callable, Tuple, Union, AnyStr, TypeVar, List
from toolz import compose

from lib.model import db
from lib.adapters import ODataQueryAdapter
from lib.main import app
from lib.constants import ConfigKeys, DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE

logger = logging.getLogger('rdbms')

session_factory = sessionmaker(bind=db.engine)

T = TypeVar('T')

@contextmanager
def session_context(must_expunge=False, use_local_context=False) -> Session:
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


def search_using_OData(db_session: Session, data: AnyStr, cls: type, content_type: str = 'uri', adapter_type=ODataQueryAdapter, *,
                       opt: Union[Callable[[Query], Query], Tuple[Callable[[Query], Query], ...]] = None,
                       opt2: Union[Callable[[Query], Query], Tuple[Callable[[Query], Query], ...]] = None,
                       extra_columns: Tuple[Column, ...] = (),
                       expunge_after_all=True,
                       use_baked_queries=False,
                       convenient=True) -> Tuple[List[T], int]:
    """
    Parses OData input and returns list of model object
    :param data: OData input data, currently QueryString
    :param cls: Main entity type for query
    :param content_type: Teh format of OData input
    :param adapter_type: Adapter type which can be OData or else
    :param opt: Query Options (extra filters, join...) for main query
    :param opt2: Query Options for count query
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

        options = compose(*opt) if isinstance(opt, Tuple) else opt

        if opt2:
            count_options = compose(*opt2) if isinstance(opt2, Tuple) else opt2
        else:
            count_options = options

        if adapter.fields:
            adapter.fields += extra_columns
        return (adapter.create_func(db_session, use_baked_queries=use_baked_queries, opt=options)(),
                adapter.create_count_func(db_session, use_baked_queries=use_baked_queries,
                                          opt=count_options)())
    finally:
        if expunge_after_all:
            db_session.expunge_all()

def get_by_slug(cls: type, session: Session, slug: str):
    return session.query(cls).filter(cls.slug == slug).one_or_none()


def create_schema():
    db.create_all()
