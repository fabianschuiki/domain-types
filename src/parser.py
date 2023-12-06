from __future__ import annotations
from src import ast
from src.diagnostics import *
from src.lexer import Token, TokenKind
from typing import *


def parse(tokens: List[Token]) -> ast.Root:
    p = Parser(tokens=tokens, last_loc=tokens[0].loc)
    return parse_root(p)


@dataclass
class Parser:
    tokens: List[Token]
    last_loc: Loc

    def loc(self) -> Loc:
        return self.tokens[0].loc

    def consume(self) -> Token:
        t = self.tokens[0]
        self.tokens = self.tokens[1:]
        self.last_loc = t.loc
        return t

    def consume_if(self, kind: TokenKind) -> Optional[Token]:
        if self.tokens[0].kind == kind:
            return self.consume()
        return None

    def require(self, kind: TokenKind, msg: Optional[str] = None) -> Token:
        if token := self.consume_if(kind):
            return token
        msg = msg or kind.name
        emit_error(self.loc(),
                   f"expected {msg}, found {self.tokens[0].kind.name}")

    def isa(self, kind: TokenKind) -> bool:
        return self.tokens[0].kind == kind

    def not_delim(self, *args: TokenKind) -> bool:
        return self.tokens[0].kind not in (TokenKind.EOF, *args)


def parse_root(p: Parser) -> ast.Root:
    loc = p.loc()
    items: List[ast.Item] = []
    while not p.isa(TokenKind.EOF):
        items.append(parse_item(p))
    return ast.Root(loc=loc | p.last_loc, items=items)


def parse_item(p: Parser) -> ast.Item:
    # Parse modules.
    if kw := p.consume_if(TokenKind.KW_MOD):
        name = p.require(TokenKind.IDENT, "module name")
        p.require(TokenKind.LPAREN)
        p.require(TokenKind.RPAREN)
        p.require(TokenKind.LCURLY)
        stmts: List[ast.Stmt] = []
        while p.not_delim(TokenKind.RCURLY):
            stmts.append(parse_stmt(p))
        p.require(TokenKind.RCURLY)
        return ast.ModItem(loc=name.loc,
                           full_loc=kw.loc | p.last_loc,
                           name=name,
                           stmts=stmts)

    emit_error(p.loc(), f"expected item, found {p.tokens[0].kind.name}")


def parse_stmt(p: Parser) -> ast.Stmt:
    loc = p.loc()

    # Parse let bindings.
    if kw := p.consume_if(TokenKind.KW_LET):
        name = p.require(TokenKind.IDENT, "let binding name")
        p.require(TokenKind.COLON)
        ty = parse_type(p)
        p.require(TokenKind.SEMICOLON)
        return ast.LetStmt(loc=name.loc,
                           full_loc=loc | p.last_loc,
                           name=name,
                           ty=ty)

    # Otherwise this is a statement that starts with an expression.
    expr = parse_expr(p)

    # Parse assignments.
    if op := p.consume_if(TokenKind.ASSIGN):
        rhs = parse_expr(p)
        p.require(TokenKind.SEMICOLON)
        return ast.AssignStmt(loc=op.loc,
                              full_loc=loc | p.last_loc,
                              lhs=expr,
                              rhs=rhs)

    return ast.ExprStmt(loc=expr.loc, expr=expr)


def parse_type(p: Parser) -> ast.Type:
    return parse_primary_type(p)


def parse_primary_type(p: Parser) -> ast.Type:
    if p.isa(TokenKind.IDENT):
        token = p.tokens[0]
        if token.spelling() == "u32":
            p.consume()
            return ast.U32Type(loc=token.loc)

    emit_error(p.loc(), f"expected type, found {p.tokens[0].kind.name}")


def parse_expr(p: Parser) -> ast.Expr:
    return parse_primary_expr(p)


def parse_primary_expr(p: Parser) -> ast.Expr:
    if token := p.consume_if(TokenKind.IDENT):
        return ast.IdentExpr(loc=token.loc, name=token, binding=None)

    emit_error(p.loc(), f"expected expression, found {p.tokens[0].kind.name}")
