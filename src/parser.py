from __future__ import annotations
from dataclasses import dataclass
from src import ast
from src.diagnostics import *
from src.source import *
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

        # Parse optional type variables.
        type_vars: List[ast.ModTypeVar] = []
        if p.consume_if(TokenKind.LT):
            while p.not_delim(TokenKind.GT):
                tv_name = p.require(TokenKind.IDENT, "type variable name")
                type_vars.append(ast.ModTypeVar(loc=tv_name.loc, name=tv_name))
                if not p.consume_if(TokenKind.COMMA):
                    break
            p.require(TokenKind.GT)

        # Parse argument list.
        args: List[ast.ModArg] = []
        p.require(TokenKind.LPAREN)
        while p.not_delim(TokenKind.RPAREN):
            arg_name = p.require(TokenKind.IDENT, "argument name")
            p.require(TokenKind.COLON)
            ty = parse_type(p)
            args.append(
                ast.ModArg(loc=arg_name.loc,
                           full_loc=arg_name.loc | p.last_loc,
                           name=arg_name,
                           ty=ty))
            if not p.consume_if(TokenKind.COMMA):
                break
        p.require(TokenKind.RPAREN)

        # Parse module body.
        p.require(TokenKind.LCURLY)
        stmts: List[ast.Stmt] = []
        while p.not_delim(TokenKind.RCURLY):
            stmts.append(parse_stmt(p))
        p.require(TokenKind.RCURLY)

        return ast.ModItem(
            loc=name.loc,
            full_loc=kw.loc | p.last_loc,
            name=name,
            type_vars=type_vars,
            args=args,
            stmts=stmts,
        )

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

    # Parse type variable declarations.
    if kw := p.consume_if(TokenKind.KW_TYPEVAR):
        name = p.require(TokenKind.IDENT, "type variable name")
        p.require(TokenKind.SEMICOLON)
        return ast.TypeVarStmt(loc=name.loc,
                               full_loc=loc | p.last_loc,
                               name=name)

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

    p.require(TokenKind.SEMICOLON)
    return ast.ExprStmt(loc=expr.loc, expr=expr)


def parse_type(p: Parser) -> ast.Type:
    ty = parse_primary_type(p)

    # Parse an domain association after the primary type.
    if at := p.consume_if(TokenKind.AT):
        name = p.require(TokenKind.IDENT, "domain name")
        ty.domain = ast.DomainIdent(loc=name.loc,
                                    name=name,
                                    binding=ast.Binding())

    return ty


def parse_primary_type(p: Parser) -> ast.Type:
    if p.isa(TokenKind.IDENT):
        token = p.tokens[0]
        if token.spelling() == "u32":
            p.consume()
            return ast.U32Type(loc=token.loc, domain=None)

    emit_error(p.loc(), f"expected type, found {p.tokens[0].kind.name}")


def parse_expr(p: Parser) -> ast.Expr:
    return parse_primary_expr(p)


def parse_primary_expr(p: Parser) -> ast.Expr:
    if token := p.consume_if(TokenKind.IDENT):
        ident = ast.IdentExpr(loc=token.loc, name=token, binding=ast.Binding())

        # Parse calls.
        if p.consume_if(TokenKind.LPAREN):
            args: List[ast.Expr] = []
            while p.not_delim(TokenKind.RPAREN):
                args.append(parse_expr(p))
                if not p.consume_if(TokenKind.COMMA):
                    break
            p.require(TokenKind.RPAREN)
            return ast.CallExpr(loc=ident.loc | p.last_loc,
                                ident=ident,
                                args=args)

        return ident

    emit_error(p.loc(), f"expected expression, found {p.tokens[0].kind.name}")
