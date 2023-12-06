from __future__ import annotations
from dataclasses import dataclass


# A source file and its contents.
@dataclass
class SourceFile:
    path: str
    contents: str

    def __repr__(self) -> str:
        return f"SourceFile(\"{self.path}\")"


# A location within a source file, given as a span of bytes.
@dataclass
class Loc:
    file: SourceFile
    offset: int
    length: int

    def __repr__(self) -> str:
        return f"\"{self.file.path}\"[{self.offset};{self.length}]"

    def __str__(self) -> str:
        lines = self.file.contents[:self.offset].split("\n")
        line_num = len(lines)
        col_num = len(lines[-1]) + 1
        return f"{self.file.path}:{line_num}:{col_num}"

    def spelling(self) -> str:
        return self.file.contents[self.offset:self.offset + self.length]

    def __or__(self, other: Loc) -> Loc:
        assert self.file == other.file, f"union of locations with different files ({self.file.path} and {other.file.path})"
        offset = min(self.offset, other.offset)
        end = max(self.offset + self.length, other.offset + other.length)
        return Loc(file=self.file, offset=offset, length=end - offset)
