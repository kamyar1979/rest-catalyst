import pyparsing as pp
import json

LP = pp.Literal("(").suppress()
RP = pp.Literal(")").suppress()
String = pp.Word(pp.alphanums + '_,.#@<>=+=/*%[]')
SingleQuoteString = pp.QuotedString(quoteChar="'", unquoteResults=False)
DoubleQuoteString = pp.QuotedString(quoteChar='"', unquoteResults=False)
QuotedString = SingleQuoteString | DoubleQuoteString
Atom = String | QuotedString
SExpr = pp.Forward()
SExprList = pp.Group(pp.ZeroOrMore(SExpr | Atom))
SExpr << (LP + SExprList + RP)


def to_json(expr: str) -> str:
    parsed = SExpr.parseString(expr).asList()
    if parsed:
        return json.dumps(parsed[0])


def from_json(val: str) -> str:
    if isinstance(val, list):
        return f"({' '.join(from_json(e) for e in val)})"
    else:
        return str(val)
