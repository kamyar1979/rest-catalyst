from catalyst.dsl.sexp_json import to_json, from_json
from sqlalchemy.sql.type_api import UserDefinedType
import hy
import rapidjson


class SExpression(UserDefinedType):

    cache_ok = True

    def get_col_spec(self):
        return "S-Expression"

    def bind_processor(self, dialect):
        return to_json

    def result_processor(self, dialect, coltype):
        return from_json

class HyLangExpression(UserDefinedType):

    def get_col_spec(self):
        return "Hy-Expression"

    def bind_processor(self, dialect):
        def process(value):

            def process_expr(expr_list):
                is_tag: bool = False
                for expr in expr_list:
                    if isinstance(expr, hy.models.HySymbol) or \
                            isinstance(expr, hy.models.HyString):
                        if str(expr) == 'dispatch-tag-macro':
                            is_tag = True
                        else:
                            if is_tag:
                                is_tag = False
                                yield f'#{expr}'
                            else:
                                yield str(expr)
                    elif isinstance(expr, hy.models.HyKeyword):
                        yield f':{expr}'
                    elif isinstance(expr, hy.models.HyExpression):
                        yield process_expr(expr)
                    else:
                        yield expr.real
            return rapidjson.dumps(process_expr(value))

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return hy.read_str(from_json(value))

        return process
