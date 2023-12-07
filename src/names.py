from __future__ import annotations
from typing import Optional, Dict
from dataclasses import dataclass, field
from src import ast
from src.source import *
from src.diagnostics import *


def resolve_names(root: ast.AstNode):
    resolve_node(root, Scope(parent=None))

    for child in root.walk(ast.WalkOrder.PreOrder):
        for name, value in child.__dict__.items():
            if isinstance(value, ast.Binding) and value.node is None:
                emit_error(child.loc,
                           f"unresolved {name} in {child.__class__.__name__}")


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
        node.binding.node = resolve(scope, node.name.spelling(), node.name.loc)
    elif isinstance(node, ast.DomainIdent):
        node.binding.node = resolve(scope, node.name.spelling(), node.name.loc)
    elif isinstance(node, ast.LetStmt):
        declare(scope, node.name.spelling(), node.name.loc, node)
    elif isinstance(node, ast.TypeVarStmt):
        declare(scope, node.name.spelling(), node.name.loc, node)
    elif isinstance(node, ast.ModTypeVar):
        declare(scope, node.name.spelling(), node.name.loc, node)
    elif isinstance(node, ast.ModArg):
        declare(scope, node.name.spelling(), node.name.loc, node)


def resolve(scope: Scope, name: str, name_loc: Loc) -> ast.AstNode:
    current_scope: Optional[Scope] = scope
    while current_scope:
        if node := current_scope.names.get(name):
            return node
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
