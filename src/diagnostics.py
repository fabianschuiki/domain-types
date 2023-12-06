from src.source import *
from sys import exit, stderr
from termcolor import colored
from typing import *


def emit_error(loc: Optional[Loc], msg: str) -> NoReturn:
    emit_diagnostic("error", "red", loc, msg)
    exit(1)


def emit_warning(loc: Optional[Loc], msg: str):
    emit_diagnostic("warning", "yellow", loc, msg)


def emit_info(loc: Optional[Loc], msg: str):
    emit_diagnostic("info", "cyan", loc, msg)


def emit_diagnostic(severity: str, color: str, loc: Optional[Loc], msg: str):
    text = colored(severity + ":", color, attrs=["bold"])
    text += " "
    text += colored(msg, attrs=["bold"])
    print(text, file=stderr)

    if loc:
        print(f"{loc}:", file=stderr)

        src_before = loc.file.contents[:loc.offset].split("\n")[-1]
        src_within = loc.file.contents[loc.offset:loc.offset + loc.length]
        src_after = loc.file.contents[loc.offset + loc.length:].split("\n")[0]

        text = "  | " + src_before
        text += colored(src_within, color, attrs=["bold"])
        text += src_after
        print(text, file=stderr)

        text = "  | " + " " * len(src_before)
        text += colored("^" * max(len(src_within), 1), color, attrs=["bold"])
        print(text, file=stderr)
