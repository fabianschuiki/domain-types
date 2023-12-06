from __future__ import annotations
from dataclasses import dataclass
from typing import List, Generator, Optional, Dict
from enum import Enum, auto
from src.lexer import Token
from src.source import Loc


class WalkOrder(Enum):
    PreOrder = auto()
    PostOrder = auto()


@dataclass
class Binding:
    node: AstNode


@dataclass
class AstNode:
    loc: Loc

    def walk(self, order: WalkOrder) -> Generator[AstNode, None, None]:
        if order == WalkOrder.PreOrder:
            yield self
        for child in self.children():
            yield from child.walk(order)
        if order == WalkOrder.PostOrder:
            yield self

    def children(self) -> Generator[AstNode, None, None]:

        def walk_inner(value) -> Generator[AstNode, None, None]:
            if isinstance(value, AstNode):
                yield value
            elif isinstance(value, list):
                for v in value:
                    yield from walk_inner(v)

        for value in self.__dict__.values():
            yield from walk_inner(value)


@dataclass
class Root(AstNode):
    items: List[Item]


#===------------------------------------------------------------------------===#
# Items
#===------------------------------------------------------------------------===#


@dataclass
class Item(AstNode):
    pass


@dataclass
class ModItem(Item):
    full_loc: Loc
    name: Token
    stmts: List[Stmt]


#===------------------------------------------------------------------------===#
# Statements
#===------------------------------------------------------------------------===#


@dataclass
class Stmt(AstNode):
    pass


@dataclass
class LetStmt(Stmt):
    full_loc: Loc
    name: Token
    ty: Type


@dataclass
class ExprStmt(Stmt):
    expr: Expr


@dataclass
class AssignStmt(Stmt):
    full_loc: Loc
    lhs: Expr
    rhs: Expr


#===------------------------------------------------------------------------===#
# Types
#===------------------------------------------------------------------------===#


@dataclass
class Type(AstNode):
    pass


@dataclass
class U32Type(Type):
    pass


#===------------------------------------------------------------------------===#
# Expressions
#===------------------------------------------------------------------------===#


@dataclass
class Expr(AstNode):
    pass


@dataclass
class IdentExpr(Expr):
    name: Token
    binding: Optional[Binding]


#===------------------------------------------------------------------------===#
# Dumping
#===------------------------------------------------------------------------===#


def dump_ast(node: AstNode) -> str:
    ids: Dict[int, int] = {}

    def get_id(node: AstNode) -> int:
        if id(node) not in ids:
            ids[id(node)] = len(ids)
        return ids[id(node)]

    def dump_field(name: str, value) -> List[str]:
        if isinstance(value, AstNode):
            return [dump_inner(value, name)]
        elif isinstance(value, list):
            fields = []
            for i, v in enumerate(value):
                fields += dump_field(f"{name}[{i}]", v)
            return fields
        return []

    def dump_inner(node: AstNode, field_prefix: str) -> str:
        line = ""
        if field_prefix:
            line += f"{field_prefix}: "
        line += f"{node.__class__.__name__} @{get_id(node)}"
        for name, value in node.__dict__.items():
            if isinstance(value, str):
                line += f" {name}=\"{value}\""
            elif isinstance(value, int):
                line += f" {name}={value}"
            elif isinstance(value, Token):
                line += f" \"{value.spelling()}\""
            elif isinstance(value, Binding):
                line += f" {name}={value.node.__class__.__name__}(@{get_id(value.node)})"
        fields = []
        for name, value in node.__dict__.items():
            fields += dump_field(name, value)
        for i, field in enumerate(fields):
            is_last = (i + 1 == len(fields))
            sep_first = "`-" if is_last else "|-"
            sep_rest = "  " if is_last else "| "
            line += "\n" + sep_first + field.replace("\n", "\n" + sep_rest)
        return line

    return dump_inner(node, "")
