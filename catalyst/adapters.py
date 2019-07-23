__author__ = 'kamyar'

from sqlalchemy import func, or_, and_, not_, inspect, Column, bindparam
from sqlalchemy.orm import joinedload, Query, RelationshipProperty, contains_eager, aliased, load_only
from sqlalchemy.ext import baked
from abc import abstractmethod
import re
import pyparsing as pp
from urllib.parse import parse_qs, unquote_plus
import functools
from sqlalchemy_utils.functions import get_type
from datetime import datetime
import operator
import collections
from typing import Callable, NamedTuple, Tuple, Optional
from logging import Logger
from sqlalchemy.sql.elements import ColumnElement, BinaryExpression

bakery = baked.bakery()


class PartConstants:
    """
    OData Query String parts
    """
    Filter = '$filter'
    OrderBy = '$orderby'
    Top = '$top'
    Skip = '$skip'
    Select = '$select'
    Expand = '$expand'


class ParsingException(Exception):
    pass


class FilterExpression(NamedTuple):
    filter_list: Tuple[BinaryExpression, ...]
    join_list: Tuple[str, ...]


class QueryAdapter:

    def __init__(self, cls,
                 fields=None,
                 expand=None,
                 join=None,
                 filter_x=None,
                 order_by=None,
                 bound_params=False,
                 extra_columns=(),
                 **kwargs):

        self.cls = cls
        self.fields = fields or ()
        self.expand = expand or ()
        self.join = join or ()
        self.filter = filter_x or ()
        self.order_by = order_by or ()
        self.start = kwargs.pop('start', 0)
        self.limit = kwargs.pop('limit', None)
        self.count = kwargs.pop('count', None)
        self.count_only = False
        self.entity_map = {}
        self.column_map = {}
        self.get_inner_entities(cls)
        self.reserved_identifiers = {}
        self.extra_columns = extra_columns
        self.aliases = {}
        self.logger: Optional[Logger] = None
        self.bound_params = bound_params
        self.param_list = []
        self.use_row_number = False
        self.filter_aliases = {}

    def __hash__(self):
        return id(self.cls) ^ hash(self.fields) ^ hash(self.expand) ^ hash(self.join) ^ hash(self.filter) ^ hash(
            self.order_by) ^ hash(self.start) ^ hash(self.limit) ^ hash(self.count)

    def set_reserved_identifier(self, **kwargs):
        self.reserved_identifiers.update(kwargs)

    @abstractmethod
    def parse(self, **kwargs):
        pass

    def get_inner_entities(self, entity: type, path: tuple = ()):
        """
        Drills down the entity and collects all the related entities recursively.
        :param entity: SqlAlchemy entity type
        :param path: OData entity path as like '/province/city'
        :return:
        """
        if self.entity_map.get(entity.__name__):
            self.entity_map[entity.__name__] += 1
        else:
            self.entity_map[entity.__name__] = 1

        for attr in inspect(entity).attrs:
            if type(attr) is RelationshipProperty:
                if not attr.uselist and attr.mapper.entity != entity:
                    if attr.mapper.entity not in map(operator.attrgetter('mapper.entity'), path):
                        self.get_inner_entities(attr.mapper.entity, path + (attr,))

            else:

                if entity == self.cls:
                    self.column_map['.'.join(tuple(map(operator.attrgetter('key'), path)) + (attr.key,))] = \
                        '{}_{}'.format(entity.__name__, attr.key).lower()

                else:
                    self.column_map['.'.join(tuple(map(operator.attrgetter('key'), path)) + (attr.key,))] = \
                        '{}_{}_{}'.format(entity.__name__, self.entity_map[entity.__name__], attr.key).lower()

    def get_order_by_field(self, field: str) -> Column:
        """
        Parses sorting expression, which may be a column name, aggregate or nested entity name
        :param field: OData entity name, may be nested as like province.city
        :return: SQlAlchemy Column for sorting query
        """
        if '.' in field:
            m = re.match(r'(.+)\.(.+)', field)
            if m.group(1) in self.aliases:
                return getattr(self.aliases[m.group(1)], m.group(2))
            else:
                return Column(self.column_map[field])
        else:
            if hasattr(self.cls, field):
                return getattr(self.cls, field)
            else:
                return Column(field)

    def create_count_func(self, session, use_baked_queries=False, opt=None) -> Callable:
        """
        Creates counting function which may be run for getting query item count
        :param session: SqlAlchemy Session
        :param use_baked_queries: Whether the cached query (if any) must be used
        :param opt: Options to apply before counting
        :return:
        """
        if use_baked_queries:
            _query = self.create_baked_count_query(session, opt)
        else:
            _query = self.create_count_query(session, opt)
        return _query.scalar

    def create_count_query(self, session, opt=None) -> Query:
        """
        Creates a count query.
        :param session: SqlAlchemy Session object
        :param opt: Options to apply before counting
        :return: SqlAlchemy Query object
        """
        pk = inspect(self.cls).primary_key[0]
        _query = session.query(func.count(func.distinct(getattr(self.cls, pk.key))))

        entities = {k: functools.reduce(lambda a, b: get_type(getattr(a, b)), k.split('/'), self.cls) for k in
                    self.join}

        self.filter += tuple(r for e in entities.values() if hasattr(e, 'restrictions') for r in e.restrictions)

        if self.join:
            inner_or_outer = {}
            for item in self.join:
                chain = item.split('/')
                inner_or_outer[item] = inspect(
                    functools.reduce(lambda a, b: get_type(getattr(a, b)), chain[:-1], self.cls)
                ).attrs[chain[-1]].innerjoin

            _query = functools.reduce(lambda q, j:
                                      q.join(*j.split('/'),
                                             isouter=not inner_or_outer.get(j)),
                                      self.join, _query)

        if opt:
            _query = opt(_query).order_by(None)

        if self.filter:
            _query = _query.filter(*self.filter)

        if self.logger:
            query_statement = str(_query.statement)
            query_params = _query.statement.compile().params
            self.logger.debug(re.sub(r'\s+:(\w+)\s*', r" '{\1}' ", query_statement).format(**query_params))

        return _query

    def create_baked_count_query(self, session, opt=None) -> baked.Result:
        """
        Creates a cached count query.
        :param session: SqlAlchemy Session object
        :param opt: Options to apply before counting
        :return: SqlAlchemy Query object
        """
        pk = inspect(self.cls).primary_key[0]

        _baked_query = bakery(lambda s: s.query(func.count(func.distinct(getattr(self.cls, pk.key)))))

        if self.join:
            inner_or_outer = {}
            for item in self.join:
                chain = item.split('/')
                inner_or_outer[item] = inspect(
                    functools.reduce(lambda a, b: get_type(getattr(a, b)), chain[:-1], self.cls)
                ).attrs[chain[-1]].innerjoin

            _baked_query += lambda bq: functools.reduce(lambda q, j:
                                                        q.join(*j.split('/')) if inner_or_outer.get(j) else q.outerjoin(
                                                            *j.split('/')),
                                                        self.join, bq)

        if opt:
            _baked_query += lambda bq: opt(bq).order_by(None)

        if self.filter:
            _baked_query += lambda bq: bq.filter(*self.filter)

        return _baked_query(session).params(**{f'param_{k}': v for k, v in enumerate(self.param_list)})

    def create_query(self, session, opt=None) -> Query:
        """
        Creates SqlAlchemy query according to OData filters and joins
        :param session: SqlAlchemy Session object
        :param opt: Options to apply before counting
        :return: SqlAlchemy Query Object
        """

        if self.fields:
            pk = inspect(self.cls).primary_key[0].key
            if getattr(self.cls, pk) not in self.fields:
                self.fields += (getattr(self.cls, pk),)
            _query = session.query(self.cls).options(load_only(*self.fields))
        else:
            _query = session.query(self.cls)

        if self.extra_columns:
            _query = _query.add_columns(*self.extra_columns)

        entities = {k: functools.reduce(lambda a, b: get_type(getattr(a, b)), k.split('/'), self.cls) for k in
                    self.join}

        self.filter += tuple(r for e in entities.values() if hasattr(e, 'restrictions') for r in e.restrictions)

        if self.join:
            inner_or_outer = {}
            for item in self.join:
                chain = item.split('/')
                inner_or_outer[item] = inspect(
                    functools.reduce(lambda a, b: get_type(getattr(a, b)), chain[:-1], self.cls)
                ).attrs[chain[-1]].innerjoin

            _query = functools.reduce(lambda q, j:
                                      q.join(*j.split('/'),
                                             isouter=not inner_or_outer.get(j)),
                                      self.join, _query)

        if self.filter:
            _query = _query.filter(*self.filter)

        eager = frozenset(self.expand) & frozenset(self.join)
        self.expand = frozenset(self.expand) - frozenset(self.join)

        if eager:
            _query = _query.options(
                *map(lambda x: functools.reduce(lambda a, b: a.contains_eager(b) if a else contains_eager(b),
                                                x.split('/'), None), eager))

        if self.expand:
            _query = _query.options(
                *map(lambda x: functools.reduce(lambda a, b: a.joinedload(b) if a else joinedload(b),
                                                x.split('/'), None), self.expand))

        if self.order_by:
            entity = self.cls
            for field, order in self.order_by:

                if '.' in field:

                    m = re.match(r'(.+)\.(.+)', field)

                    if m.group(1) not in self.aliases:

                        for item in m.group(1).split('.'):

                            cls = inspect(entity)
                            attr = cls.attrs[item]
                            entity = get_type(attr)

                            if attr.innerjoin:
                                aliased_entity = aliased(entity)
                                self.aliases[m.group(1)] = aliased_entity
                                _query = _query.join(aliased_entity, item).options(
                                    contains_eager(item, alias=aliased_entity))
                            else:
                                aliased_entity = aliased(entity)
                                self.aliases[m.group(1)] = aliased_entity
                                _query = _query.outerjoin(aliased_entity, item).options(
                                    contains_eager(item, alias=aliased_entity))

                if order == "desc":
                    _query = _query.order_by(self.get_order_by_field(field).desc())
                else:
                    _query = _query.order_by(self.get_order_by_field(field).asc())

        if opt:
            _query = opt(_query)

        if self.use_row_number:
            pk = inspect(self.cls).primary_key[0].key
            if self.start or self.limit:
                row_number_column = func.dense_rank().over(order_by=getattr(self.cls, pk)).label('row_number')
                _query = _query.add_columns(row_number_column).from_self(self.cls, *self.extra_columns)
                if self.start:
                    _query = _query.filter(row_number_column > self.start)
                if self.limit:
                    _query = _query.filter(row_number_column <= self.start + self.limit)

        else:
            if self.start:
                _query = _query.offset(self.start)
            if self.limit:
                _query = _query.limit(self.limit)

        if self.logger:
            query_statement = str(_query.statement)
            query_params = _query.statement.compile().params
            self.logger.debug(re.sub(r'\s?:(\w+)\s*', r" '{\1}' ", query_statement).format(**query_params))

        return _query

    def create_func(self, session, use_baked_queries=False, opt=None) -> Callable:
        if use_baked_queries:
            return self.create_baked_query(session, opt).all
        else:
            return self.create_query(session, opt).all

    def create_baked_query(self, session, opt=None) -> baked.Result:
        """
        Creates SqlAlchemy cached query according to OData filters and joins
        :param session: SqlAlchemy Session object
        :param opt: Options to apply before counting
        :return: SqlAlchemy Query Object
        """
        _baked_query = bakery(lambda s: s.query(self.cls))

        if self.fields:
            pk = inspect(self.cls).primary_key[0].key
            if getattr(self.cls, pk) not in self.fields:
                self.fields += (getattr(self.cls, pk),)
            _baked_query += lambda bq: bq.options(load_only(*self.fields))

        if self.extra_columns:
            _baked_query += lambda bq: bq.add_columns(*self.extra_columns)

        entities = (functools.reduce(lambda a, b: get_type(getattr(a, b)), x.split('/'), self.cls) for x in self.join)
        self.filter += tuple(r for e in entities if hasattr(e, 'restrictions') for r in e.restrictions)

        if self.join:
            inner_or_outer = {}
            for item in self.join:
                chain = item.split('/')
                inner_or_outer[item] = inspect(
                    functools.reduce(lambda a, b: get_type(getattr(a, b)), chain[:-1], self.cls)
                ).attrs[chain[-1]].innerjoin

            _baked_query += lambda bq: functools.reduce(lambda q, j:
                                                        q.join(*j.split('/')) if inner_or_outer.get(
                                                            j) else q.outerjoin(*j.split('/')),
                                                        self.join, bq)

        if self.filter:
            _baked_query += lambda bq: bq.filter(*self.filter)

        eager = frozenset(self.expand) & frozenset(self.join)
        self.expand = frozenset(self.expand) - frozenset(self.join)

        if eager:
            _baked_query += lambda bq: bq.options(
                *map(lambda x: functools.reduce(lambda a, b: a.contains_eager(b) if a else contains_eager(b),
                                                x.split('/'), None), eager))

        if self.expand:
            _baked_query += lambda bq: bq.options(
                *map(lambda x: functools.reduce(lambda a, b: a.joinedload(b) if a else joinedload(b),
                                                x.split('/'), None), self.expand))

        if self.order_by:
            entity = self.cls
            for field, order in self.order_by:

                if '.' in field:

                    m = re.match(r'(.+)\.(.+)', field)

                    if m.group(1) not in self.aliases:

                        for item in m.group(1).split('.'):

                            cls = inspect(entity)
                            attr = cls.attrs[item]
                            entity = get_type(attr)

                            if attr.innerjoin:
                                aliased_entity = aliased(entity)
                                self.aliases[m.group(1)] = aliased_entity
                                _baked_query += lambda bq: bq.join(aliased_entity, item).options(
                                    contains_eager(item, alias=aliased_entity))
                            else:
                                aliased_entity = aliased(entity)
                                self.aliases[m.group(1)] = aliased_entity
                                _baked_query += lambda bq: bq.outerjoin(aliased_entity, item).options(
                                    contains_eager(item, alias=aliased_entity))

                if order == "desc":
                    _baked_query += lambda bq: bq.order_by(self.get_order_by_field(field).desc())
                else:
                    _baked_query += lambda bq: bq.order_by(self.get_order_by_field(field).asc())

        if opt:
            _baked_query += lambda bq: opt(bq)

        if self.use_row_number:
            pk = inspect(self.cls).primary_key[0].key
            if self.start or self.limit:
                row_number_column = func.dense_rank().over(order_by=getattr(self.cls, pk)).label('row_number')
                _baked_query += lambda bq: bq.add_columns(row_number_column).from_self(self.cls, *self.extra_columns)
                if self.start:
                    _baked_query += lambda bq: bq.filter(row_number_column > self.start)
                if self.limit:
                    _baked_query += lambda bq: bq.filter(row_number_column <= self.start + self.limit)
        else:
            if self.start:
                _baked_query += lambda bq: bq.offset(self.start)
            if self.limit:
                _baked_query += lambda bq: bq.limit(self.limit)

        # if self.logger:
        #     self.logger.debug('%s with params: %s', _baked_query.statement, _baked_query.statement.compile().params)

        return _baked_query(session).params(**{f'param_{k}': v for k, v in enumerate(self.param_list)})

    def perform_convenience(self, max_items_per_page, default_items_per_page):
        if not self.limit or self.limit > max_items_per_page:
            self.limit = default_items_per_page


class ODataQueryAdapter(QueryAdapter):
    filter_pattern = re.compile(fr'{PartConstants.Filter}=(?P<filter>[^&]+)')
    sort_pattern = re.compile(fr'{PartConstants.OrderBy}=(?P<sort>[^$]+)')
    top_pattern = re.compile(fr'{PartConstants.Top}=(?P<top>\d+)')
    skip_pattern = re.compile(fr'{PartConstants.Skip}=(?P<skip>\d+)')
    select_pattern = re.compile(fr'{PartConstants.Select}=(?P<select>\w+)')

    def __init__(self, cls):
        super().__init__(cls)

    def parse_filter(self, *filters: str, extra_columns=()) -> FilterExpression:

        def date_part_func(part: str):
            def date_part_reverse(part_rev: str, val):
                return func.date_part(val, part_rev)

            return functools.partial(date_part_reverse, part)

        def containing(a, b: str):
            return a.in_(b.replace(' ', '').split(','))

        def excluding(a, b: str):
            return not_(a.in_(b.replace(' ', '').split(',')))

        def array_has(a, b):
            return a.any(b)

        def array_lacks(a, b):
            return not_(a.all(b))

        op_map = {
            'eq': operator.eq,
            'ne': operator.ne,
            'gt': operator.gt,
            'lt': operator.lt,
            'ge': operator.ge,
            'le': operator.le,
            'add': operator.add,
            'sub': operator.sub,
            'mul': operator.mul,
            'div': operator.truediv,
            'mod': operator.mod,
            'AND': and_,
            'OR': or_,
            'in': containing,
            'out': excluding,
            'has': array_has,
            'lacks': array_lacks
        }

        func_map = {'substringof': lambda a, b: b.ilike('%{0}%'.format(a)),
                    'endswith': lambda a, b: a.ilike('%{0}'.format(b)),
                    'startswith': lambda a, b: a.ilike('{0}%'.format(b)),
                    'length': func.length,
                    'indexof': func.position,
                    'replace': func.replace,
                    'substring': func.substring,
                    'tolower': func.lower,
                    'toupper': func.upper,
                    'trim': func.trim,
                    'round': func.round,
                    'floor': func.floor,
                    'ceiling': func.ceiling,
                    'year': date_part_func('year'),
                    'month': date_part_func('month'),
                    'day': date_part_func('day'),
                    'hour': date_part_func('hour'),
                    'minute': date_part_func('minute'),
                    'second': date_part_func('second'),
                    }

        operator_ = pp.Regex('|'.join(op_map.keys())).setName('operator')
        number = pp.Regex(r'[\d\.]+')
        identifier = pp.Regex(r'[a-z][\w\.]*')
        str_value = pp.QuotedString("'", unquoteResults=False, escChar='\\')
        date_value = pp.Regex(r'\d{4}-\d{1,2}-\d{1,2}')
        collection_value = pp.Suppress('[') + pp.delimitedList(pp.Regex(r'[\w_]+'), combine=True) + pp.Suppress(']')
        l_par = pp.Suppress('(')
        r_par = pp.Suppress(')')
        function_call = pp.Forward()
        arg = function_call | identifier | date_value | number | collection_value | str_value
        function_call = pp.Group(identifier + l_par + pp.Optional(pp.delimitedList(arg)) + r_par)
        param = function_call | arg
        condition = pp.Group(param + operator_ + param)

        expr = pp.operatorPrecedence(condition, [
            (pp.CaselessLiteral("AND"), 2, pp.opAssoc.LEFT,),
            (pp.CaselessLiteral("OR"), 2, pp.opAssoc.LEFT,),
        ])

        try:
            if filters:

                filter_list = []
                join_list = []
                exists_expressions = []

                def parse_identifier(s):
                    if type(s) is not str and isinstance(s, collections.Sequence):
                        return parse_single_expression(s)
                    elif re.match(r"^'?\d+-\d+-\d+'?$", s):
                        return datetime.strptime(s.strip("'"), '%Y-%m-%d')
                    elif re.match(r'^\d+$', s):
                        return int(s.strip("'"))
                    elif re.match(r'^[\d.]+$', s):
                        return float(s.strip("'"))
                    elif re.match(r"^'.+'$", s) or ',' in s:
                        return s.strip("'")
                    else:
                        if s == 'true':
                            return True
                        elif s == 'false':
                            return False
                        elif s == 'null':
                            return
                        else:
                            if '.' in s:
                                inner_parts = s.split('.')

                                if inspect(self.cls).attrs[inner_parts[0]].uselist:
                                    if inner_parts[-2:-1] == ['any']:
                                        del inner_parts[-2:-1]
                                        exists_expressions.append(getattr(self.cls, inner_parts[0]))
                                    elif inner_parts[-2:-1] == ['all']:
                                        del inner_parts[-2:-1]
                                        join_item = '/'.join(inner_parts[:-1])
                                        if join_item not in join_list:
                                            join_list.append(join_item)
                                        self.use_row_number = True

                                    entity = functools.reduce(
                                        lambda c, p: get_type(getattr(c, p)),
                                        inner_parts[:-1],
                                        self.cls)

                                else:

                                    entity = functools.reduce(
                                        lambda c, p: get_type(getattr(c, p)),
                                        inner_parts[:-1],
                                        self.cls)

                                    join_item = '/'.join(inner_parts[:-1])
                                    if join_item not in join_list:
                                        join_list.append(join_item)
                                        self.filter_aliases[join_item] = aliased(entity)

                                return getattr(entity, inner_parts[-1:][0])

                            else:
                                if re.match(r'^[A-Z_]+$', s):
                                    if s in self.reserved_identifiers:
                                        return self.reserved_identifiers[s]
                                    else:
                                        raise NameError(f"Unrecognized identifier {s}")
                                elif hasattr(self.cls, s):
                                    return self.cls.__table__.columns[s]
                                elif s in extra_columns:
                                    return Column(s)
                                else:
                                    raise NameError(f"Field {s} not found in class {self.cls}")

                def parse_single_expression(e) -> ColumnElement:
                    if not isinstance(e, str) and isinstance(e, collections.Sequence):
                        if len(e) == 1:
                            return parse_single_expression(e[0])
                        else:
                            if len(e):
                                if isinstance(e[0], str) and e[0].lower() in func_map:
                                    arguments = tuple(map(parse_identifier, e[1:]))
                                    if exists_expressions:
                                        return exists_expressions.pop().any(func_map[e[0]](*arguments))
                                    else:
                                        return func_map[e[0].lower()](*arguments)
                                else:
                                    if e[1] in op_map:
                                        operands = tuple(map(parse_identifier, e[::2]))
                                        if exists_expressions:
                                            return exists_expressions.pop().any(op_map[e[1]](*operands))
                                        else:
                                            return op_map[e[1]](*operands)
                                    else:
                                        raise NotImplementedError(
                                            f"Invalid operator {e[1]} in OData expression")
                    else:
                        if self.bound_params:
                            self.param_list.append(e)
                            return bindparam(f'param_{len(self.param_list)}')
                        else:
                            return e

                for filter_item in filters:
                    parsed_filter = expr.parseString(filter_item)

                    parsed_expression = parse_single_expression(parsed_filter.asList())
                    filter_list.append(parsed_expression)

                return FilterExpression(tuple(filter_list), tuple(join_list))

        except pp.ParseException as ex:
            raise ParsingException(str(ex))

        except AttributeError:
            raise

    def parse(self, uri=None):
        """
        Parse OData Query String into Adapter properties, to be used when creating SqlAlchemy query afterwards.
        :param uri: Url of the RESTFul request to parse
        :return:
        """

        if uri:
            uri = unquote_plus(uri)
            parts = parse_qs(uri)

            if parts.get(PartConstants.Filter):
                self.filter, self.join = self.parse_filter(*parts[PartConstants.Filter],
                                                           extra_columns=tuple(x.name for x in self.extra_columns))

            if parts.get(PartConstants.OrderBy):
                sort = parts[PartConstants.OrderBy][0].split(',') if len(parts[PartConstants.OrderBy]) == 1 else \
                    parts[PartConstants.OrderBy]
                self.order_by = tuple(s.split(' ') if ' ' in s else (s, 'asc') for s in sort)

            if parts.get(PartConstants.Select):
                select = parts[PartConstants.Select][0].split(',') if len(parts[PartConstants.Select]) == 1 else \
                    parts[PartConstants.Select]
                self.fields = tuple(getattr(self.cls, n) for n in select)

            if parts.get(PartConstants.Expand):
                self.expand = parts[PartConstants.Expand][0].split(',') if len(
                    parts[PartConstants.Expand]) == 1 else parts[PartConstants.Expand]

            if parts.get(PartConstants.Top):
                top = parts[PartConstants.Top][0]
                self.limit = int(top)

            if parts.get(PartConstants.Skip):
                self.start = int(parts[PartConstants.Skip][0])

