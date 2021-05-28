from catalyst.dsl.sexp_json import to_json, from_json
from sqlalchemy.sql.type_api import UserDefinedType


class SExpression(UserDefinedType):

    def get_col_spec(self):
        return "S-Expression"

    def bind_processor(self, dialect):
        def process(value):
            return to_json(value)

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return from_json(value)

        return process
