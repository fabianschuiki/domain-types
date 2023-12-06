from __future__ import annotations
from typing import Optional, Dict
from dataclasses import dataclass, field
from src import ast
from src.source import *
from src.diagnostics import *


def resolve_names(root: ast.AstNode):
    resolve_node(root, Scope(parent=None))
    # print(f"resolving names")

    # for node in root.walk(ast.WalkOrder.PostOrder):
    #     print(f"- {node.__class__.__name__}")

    # pass


def resolve_node(node: ast.AstNode, scope: Scope):
    if isinstance(node, ast.Root):
        subscope = Scope(parent=scope)
        for item in node.items:
            declare_item(item, subscope)
        for child in node.children():
            resolve_node(child, subscope)
        return

    if isinstance(node, ast.ModItem):
        subscope = Scope(parent=scope)
        for child in node.children():
            resolve_node(child, subscope)
        return

    for child in node.children():
        resolve_node(child, scope)

    if isinstance(node, ast.IdentExpr):
        node.binding = resolve(scope, node.name.spelling(), node.name.loc)
    if isinstance(node, ast.LetStmt):
        declare(scope, node.name.spelling(), node.name.loc, node)


def resolve(scope: Scope, name: str, name_loc: Loc) -> ast.Binding:
    current_scope: Optional[Scope] = scope
    while current_scope:
        if node := current_scope.names.get(name):
            return ast.Binding(node)
        current_scope = current_scope.parent
    emit_error(name_loc, f"unknown name `{name}`")


@dataclass
class Scope:
    parent: Optional[Scope]
    names: Dict[str, ast.AstNode] = field(default_factory=dict)


def declare(scope: Scope, name: str, name_loc: Loc, node: ast.AstNode):
    if name in scope.names:
        emit_info(scope.names[name].loc,
                  f"previous definition of `{name}` was here")
        emit_error(name_loc, f"name `{name}` already defined")

    scope.names[name] = node


def declare_item(item: ast.Item, scope: Scope):
    if isinstance(item, ast.ModItem):
        declare(scope, item.name.spelling(), item.name.loc, item)
