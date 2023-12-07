from __future__ import annotations
from dataclasses import dataclass, field
from src import ast
from src.diagnostics import *
from src.source import *
from typing import Dict, Optional


def type_check(node: ast.AstNode):
    if isinstance(node, ast.ModItem):
        typeck_module(Context(root=RootContext()), node)
    else:
        for child in node.children():
            type_check(child)


@dataclass
class RootContext:
    free_var_id: int = 0
    inferrable_var_id: int = 0

    def get_free_variable(self, name: Optional[str]) -> FreeDomainVar:
        var = FreeDomainVar(num=self.free_var_id, name=name)
        self.free_var_id += 1
        return var

    def get_inferrable_variable(self) -> InferrableDomainVar:
        var = InferrableDomainVar(num=self.inferrable_var_id)
        self.inferrable_var_id += 1
        return var


@dataclass
class Context:
    root: RootContext
    types: Dict[int, Type] = field(default_factory=dict)
    domains: Dict[int, Domain] = field(default_factory=dict)


def typeck_module(ctx: Context, mod: ast.ModItem):
    print(f"typeck module {mod.name.spelling()}")

    # Predefine type variables.
    for type_var in mod.type_vars:
        ctx.domains[id(type_var)] = ctx.root.get_free_variable(
            type_var.name.spelling())

    for arg in mod.args:
        type_of(ctx, arg)
    for result in mod.results:
        type_of(ctx, result)

    for stmt in mod.stmts:
        typeck_stmt(ctx, stmt)

    # Print final types.
    for stmt in mod.stmts:
        if isinstance(stmt, ast.LetStmt):
            print(f"- final {stmt.name.spelling()} = {type_of(ctx, stmt)}")


def typeck_stmt(ctx: Context, stmt: ast.Stmt):
    print(f"typeck statement {stmt.__class__.__name__}")

    if isinstance(stmt, ast.AssignStmt):
        ty_lhs = type_of(ctx, stmt.lhs)
        ty_rhs = type_of(ctx, stmt.rhs)
        unify_types(ctx, ty_lhs, ty_rhs, stmt.loc)

    elif isinstance(stmt, ast.ExprStmt):
        type_of(ctx, stmt.expr)

    elif isinstance(stmt, ast.LetStmt):
        ty = type_of(ctx, stmt)
        if stmt.ty and stmt.init:
            init_ty = type_of(ctx, stmt.init)
            unify_types(ctx, ty, init_ty, stmt.loc)


def type_of(ctx: Context, node: ast.AstNode) -> Type:
    if ty := ctx.types.get(id(node)):
        return ty

    ty = type_of_inner(ctx, node)
    # emit_info(node.loc, f"{node.__class__.__name__} has type `{ty}`")
    ctx.types[id(node)] = ty
    return ty


def type_of_inner(ctx: Context, node: ast.AstNode) -> Type:
    # print(f"computing type of {node.__class__.__name__}")

    if isinstance(node, ast.LetStmt):
        if node.ty is not None:
            return declare_ast_type(ctx, node.ty)
        if node.init is not None:
            return type_of(ctx, node.init)
        emit_error(
            node.loc,
            f"unknown type: let `{node.name.spelling()}` needs either a type or an initial value"
        )
    if isinstance(node, ast.ModArg):
        return declare_ast_type(ctx, node.ty)
    if isinstance(node, ast.ModResult):
        return declare_ast_type(ctx, node.ty)

    if isinstance(node, ast.IdentExpr):
        target = node.binding.get()
        if isinstance(target, ast.LetStmt):
            return type_of(ctx, target)
        if isinstance(target, ast.ModArg):
            return type_of(ctx, target)
        emit_error(
            node.loc,
            f"`{node.name.spelling()}` cannot be used in an expression")

    if isinstance(node, ast.CallExpr):
        callee = node.ident.binding.get()
        if isinstance(callee, ast.ModItem):
            return type_of_call(ctx, node, callee)
        emit_error(node.loc, f"`{node.ident.loc.spelling()}` cannot be called")

    emit_error(node.loc, "node has no type")


def type_of_call(ctx: Context, call: ast.CallExpr,
                 callee: ast.ModItem) -> Type:
    if len(call.args) != len(callee.args):
        emit_error(
            call.loc,
            f"invalid number of call arguments; `{callee.name.spelling()}` expects {len(callee.args)}, but call provides {len(call.args)}"
        )

    # Create a local context for the called module. Map each of the
    # module's type variables to an inferrable domain variable. Then
    # populate the context with the argument types.
    call_ctx = Context(root=ctx.root)

    for type_var in callee.type_vars:
        var = call_ctx.root.get_inferrable_variable()
        print(
            f"add {var} for type variable `{type_var.name.spelling()}` of call `{call.loc.spelling()}`"
        )
        call_ctx.domains[id(type_var)] = var

    for call_arg, mod_arg in zip(call.args, callee.args):
        call_ty = type_of(ctx, call_arg)
        mod_ty = type_of(call_ctx, mod_arg)
        unify_types(ctx, call_ty, mod_ty, call_arg.loc)

    if len(callee.results) == 0:
        return Type(primary=UnitType(),
                    domain=ctx.root.get_free_variable(None))

    if len(callee.results) == 1:
        return type_of(call_ctx, callee.results[0])

    fields: Dict[str, Type] = {}
    for mod_result in callee.results:
        mod_ty = type_of(call_ctx, mod_result)
        fields[mod_result.name.spelling()] = mod_ty
    return Type(primary=NamedTupleType(fields=fields),
                domain=ctx.root.get_free_variable(None))


def domain_of(ctx: Context, node: ast.AstNode) -> Domain:
    if dom := ctx.domains.get(id(node)):
        return dom

    dom = domain_of_inner(ctx, node)
    # emit_info(node.loc, f"{node.__class__.__name__} has domain `{dom}`")
    ctx.domains[id(node)] = dom
    return dom


def domain_of_inner(ctx: Context, node: ast.AstNode) -> Domain:
    # print(f"computing domain of {node.__class__.__name__}")

    if isinstance(node, ast.TypeVarStmt):
        return ctx.root.get_free_variable(node.name.spelling())

    if isinstance(node, ast.DomainIdent):
        target = node.binding.get()
        if isinstance(target, ast.TypeVarStmt):
            return domain_of(ctx, target)
        if isinstance(target, ast.ModTypeVar):
            return domain_of(ctx, target)
        emit_error(node.loc,
                   f"`{node.name.spelling()}` cannot be used as domain")

    emit_error(node.loc, "node has no domain")


def declare_ast_type(ctx: Context, aty: ast.Type) -> Type:
    domain: Domain
    if aty.domain is None:
        domain = ctx.root.get_inferrable_variable()
        print(f"add {domain} for implicit domain in `{aty.loc.spelling()}`")
    else:
        domain = domain_of(ctx, aty.domain)

    if isinstance(aty, ast.U32Type):
        return Type(primary=U32Type(), domain=domain)

    if isinstance(aty, ast.ClockType):
        return Type(
            primary=ClockType(clock_domain=domain_of(ctx, aty.clock_domain)),
            domain=domain)

    emit_error(aty.loc, f"invalid type")


def unify_types(ctx: Context, lhs: Type, rhs: Type, loc: Loc):
    unify_primary_types(ctx, lhs.primary, rhs.primary, loc)
    unify_domains(ctx, lhs.domain, rhs.domain, loc)


def unify_primary_types(ctx: Context, lhs: PrimaryType, rhs: PrimaryType,
                        loc: Loc):
    if lhs == rhs:
        return
    if isinstance(lhs, UnitType) and isinstance(rhs, UnitType):
        return
    if isinstance(lhs, U32Type) and isinstance(rhs, U32Type):
        return
    if isinstance(lhs, ClockType) and isinstance(rhs, ClockType):
        unify_domains(ctx, lhs.clock_domain, rhs.clock_domain, loc=loc)
        return

    emit_error(loc, f"incompatible types: `{lhs}` and `{rhs}`")


def unify_domains(ctx: Context, lhs: Domain, rhs: Domain, loc: Loc):
    lhs = simplify_domain(lhs)
    rhs = simplify_domain(rhs)

    if lhs == rhs:
        return

    # If both sides are inferrable variables, pick the variable with the lower
    # numeric ID and assign it as the replacement value of the other variable.
    if isinstance(lhs, InferrableDomainVar) and isinstance(
            rhs, InferrableDomainVar):
        assert lhs.assignment is None  # simplify_domain does this
        assert rhs.assignment is None  # simplify_domain does this
        if lhs.num > rhs.num:
            lhs, rhs = rhs, lhs
        print(f"marking inferrable vars equivalent: {rhs} = {lhs}")
        rhs.assignment = lhs
        return

    # If one of the sides is an inferrable variable, assign it the value of the
    # other side.
    if isinstance(lhs, InferrableDomainVar):
        assert lhs.assignment is None  # simplify_domain does this
        print(f"inferring {lhs} = {rhs}")
        lhs.assignment = rhs
        return
    if isinstance(rhs, InferrableDomainVar):
        assert rhs.assignment is None  # simplify_domain does this
        print(f"inferring {rhs} = {lhs}")
        rhs.assignment = lhs
        return

    emit_error(loc, f"incompatible domains: `{lhs}` and `{rhs}`")


# Look through assignments to inferrable variables.
def simplify_domain(domain: Domain) -> Domain:
    if isinstance(domain, InferrableDomainVar) and domain.assignment:
        domain.assignment = simplify_domain(domain.assignment)
        return domain.assignment
    return domain


@dataclass
class Type:
    primary: PrimaryType
    domain: Domain

    def __str__(self) -> str:
        return f"{self.primary} @{simplify_domain(self.domain)}"


@dataclass
class PrimaryType:
    pass


@dataclass
class UnitType(PrimaryType):

    def __str__(self) -> str:
        return "()"


@dataclass
class U32Type(PrimaryType):

    def __str__(self) -> str:
        return "u32"


@dataclass
class ClockType(PrimaryType):
    clock_domain: Domain

    def __str__(self) -> str:
        return f"Clock<{simplify_domain(self.clock_domain)}>"


@dataclass
class NamedTupleType(PrimaryType):
    fields: Dict[str, Type]

    def __str__(self) -> str:
        return "(" + ", ".join(f"{name}: {ty}"
                               for name, ty in self.fields.items()) + ")"


@dataclass
class Domain:
    pass


@dataclass
class FreeDomainVar(Domain):
    num: int
    name: Optional[str] = None

    def __str__(self) -> str:
        if self.name is not None:
            return self.name
        return f"${self.num}"


@dataclass
class InferrableDomainVar(Domain):
    num: int
    assignment: Optional[Domain] = None

    def __str__(self) -> str:
        return f"?{self.num}"
