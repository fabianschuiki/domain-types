import argparse
import sys
from src.ast import dump_ast
from src.diagnostics import *
from src.lexer import tokenize
from src.parser import parse
from src.source import *
from src.names import resolve_names
from src.typeck import type_check


def main():
    # Parse command line arguments.
    parser = argparse.ArgumentParser()

    parser.add_argument("input",
                        metavar="INPUT",
                        help="Source file to compile")

    parser.add_argument("--dump-tokens",
                        action="store_true",
                        help="Dump lexed tokens and exit")

    parser.add_argument("--dump-ast",
                        action="store_true",
                        help="Dump parsed syntax and exit")

    parser.add_argument("--dump-resolved",
                        action="store_true",
                        help="Dump syntax with resolved names and exit")

    args = parser.parse_args()

    # Tokenize the input.
    file = openSourceFile(args.input)
    tokens = tokenize(file)
    if args.dump_tokens:
        for token in tokens:
            print(f"- {token.kind.name}: `{token.loc.spelling()}`")
        return

    # Parse the tokens into an AST.
    root = parse(tokens)
    if args.dump_ast:
        print(dump_ast(root))
        return

    # Resolve names in the AST.
    resolve_names(root)
    if args.dump_resolved:
        print(dump_ast(root))
        return

    # Type-check the AST.
    type_check(root)


def openSourceFile(path: str) -> SourceFile:
    try:
        with open(path, "r") as f:
            return SourceFile(path, f.read())
    except Exception as e:
        emit_error(None, f"unable to open file: {e}")
