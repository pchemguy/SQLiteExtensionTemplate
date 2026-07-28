"""Generate a Python ctypes declaration module from marked C definitions.

The tool parses one or more C implementation files with Python libclang,
selects explicitly marked function definitions, validates a deliberately
restricted C ABI, and emits a deterministic Python module that assigns
``argtypes`` and ``restype`` on an already-loaded ``ctypes.CDLL`` object.

Example:

python tool/generate_test_api.py ^
  --source src/alphabet.c ^
  --ctypes pytestenv/src/pytestenv/_native_generated.py ^
  --clang-arg=-x ^
  --clang-arg=c ^
  --clang-arg=-std=c11 ^
  --clang-arg=--target=x86_64-pc-windows-msvc ^
  --clang-arg=-fms-extensions ^
  --clang-arg=-fms-compatibility ^
  --clang-arg=-DPYTEST_C_API

https://chatgpt.com/c/6a683465-21cc-83eb-942f-54fe28dfe936
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, NoReturn, Sequence

from clang.cindex import (
    Config,
    Cursor,
    CursorKind,
    Diagnostic,
    Index,
    LinkageKind,
    TranslationUnit,
    Type,
    TypeKind,
)


PROGRAM_NAME = "generate_ctypes"
PROGRAM_VERSION = "1.0.0"
DEFAULT_MARKER = "PYTEST_API"

EXIT_SUCCESS = 0
EXIT_STALE = 1
EXIT_ERROR = 2

_C_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

_UNSUPPORTED_CALLING_CONVENTION_TOKENS = frozenset(
    {
        "__stdcall",
        "_stdcall",
        "__fastcall",
        "_fastcall",
        "__thiscall",
        "__vectorcall",
        "WINAPI",
        "CALLBACK",
        "APIENTRY",
    }
)

_DIRECT_KIND_MAP = {
    "BOOL":      "ctypes.c_bool",
    "CHAR_S":    "ctypes.c_char",
    "CHAR_U":    "ctypes.c_char",
    "SCHAR":     "ctypes.c_int8",
    "UCHAR":     "ctypes.c_uint8",
    "SHORT":     "ctypes.c_short",
    "USHORT":    "ctypes.c_ushort",
    "INT":       "ctypes.c_int",
    "UINT":      "ctypes.c_uint",
    "LONG":      "ctypes.c_long",
    "ULONG":     "ctypes.c_ulong",
    "LONGLONG":  "ctypes.c_longlong",
    "ULONGLONG": "ctypes.c_ulonglong",
    "FLOAT":     "ctypes.c_float",
    "DOUBLE":    "ctypes.c_double",
}

_TYPEDEF_MAP = {
    "int8_t":         "ctypes.c_int8",
    "uint8_t":        "ctypes.c_uint8",
    "int16_t":        "ctypes.c_int16",
    "uint16_t":       "ctypes.c_uint16",
    "int32_t":        "ctypes.c_int32",
    "uint32_t":       "ctypes.c_uint32",
    "int64_t":        "ctypes.c_int64",
    "uint64_t":       "ctypes.c_uint64",
    "intptr_t":       "ctypes.c_ssize_t",
    "uintptr_t":      "ctypes.c_size_t",
    "ptrdiff_t":      "ctypes.c_ssize_t",
    "size_t":         "ctypes.c_size_t",
    "sqlite3_int64":  "ctypes.c_int64",
    "sqlite3_uint64": "ctypes.c_uint64",
}

_ALLOWED_LEAF_EXPRESSIONS = frozenset(
    {
        "None",
        "ctypes.c_bool",
        "ctypes.c_char",
        "ctypes.c_int8",
        "ctypes.c_uint8",
        "ctypes.c_int16",
        "ctypes.c_uint16",
        "ctypes.c_int32",
        "ctypes.c_uint32",
        "ctypes.c_int64",
        "ctypes.c_uint64",
        "ctypes.c_short",
        "ctypes.c_ushort",
        "ctypes.c_int",
        "ctypes.c_uint",
        "ctypes.c_long",
        "ctypes.c_ulong",
        "ctypes.c_longlong",
        "ctypes.c_ulonglong",
        "ctypes.c_float",
        "ctypes.c_double",
        "ctypes.c_size_t",
        "ctypes.c_ssize_t",
        "ctypes.c_void_p",
    }
)


class GeneratorError(Exception):
    """Base class for expected generator failures."""


class ParseError(GeneratorError):
    """Raised when libclang cannot parse a translation unit."""


class DeclarationExtractionError(GeneratorError):
    """Raised when a literal C declaration cannot be extracted."""


class UnsupportedTypeError(GeneratorError):
    """Raised when a selected function uses an unsupported C type."""


class DuplicateSymbolError(GeneratorError):
    """Raised when multiple selected definitions have the same symbol name."""


@dataclass(frozen=True)
class SourceLocation:
    file: Path
    line: int
    column: int


@dataclass(frozen=True)
class CType:
    kind: str
    spelling: str
    canonical_spelling: str
    const: bool
    volatile: bool
    restrict: bool
    typedef_name: str | None = None
    pointee: "CType | None" = None
    canonical: "CType | None" = None


@dataclass(frozen=True)
class Parameter:
    name: str
    c_type: CType
    location: SourceLocation


@dataclass(frozen=True)
class Function:
    name: str
    result_type: CType
    parameters: tuple[Parameter, ...]
    variadic: bool
    declaration_text: str
    location: SourceLocation
    source_index: int
    declaration_tokens: tuple[str, ...]


@dataclass(frozen=True)
class Arguments:
    sources: tuple[Path, ...]
    ctypes_output: Path
    clang_args: tuple[str, ...]
    marker: str
    msvc_env: bool
    check: bool
    verbose: bool


def _display_path(path: Path) -> str:
    """Return a stable user-facing path without requiring it to be relative."""
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def _location_text(location: SourceLocation) -> str:
    return (
        f"{_display_path(location.file)}:"
        f"{location.line}:{location.column}"
    )


def _error(message: str) -> GeneratorError:
    return GeneratorError(message)


def parse_args(argv: Sequence[str] | None = None) -> Arguments:
    parser = argparse.ArgumentParser(
        prog=PROGRAM_NAME,
        description=(
            "Generate a ctypes declarations module from marked C function "
            "definitions using Python libclang."
        ),
    )
    parser.add_argument(
        "--source",
        action="append",
        required=True,
        metavar="FILE",
        help="C implementation file to parse; may be repeated",
    )
    parser.add_argument(
        "--ctypes",
        dest="ctypes_output",
        required=True,
        metavar="FILE",
        help="generated Python ctypes module",
    )
    parser.add_argument(
        "--clang-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="argument passed unchanged to every libclang parse",
    )
    parser.add_argument(
        "--marker",
        default=DEFAULT_MARKER,
        metavar="NAME",
        help=f"function marker identifier (default: {DEFAULT_MARKER})",
    )
    parser.add_argument(
        "--msvc-env",
        action="store_true",
        help=(
            "append MSVC system include directories from the active "
            "INCLUDE environment variable as -imsvc arguments"
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="check whether the output is current without modifying it",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print informational diagnostics",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {PROGRAM_VERSION}",
    )

    namespace = parser.parse_args(argv)

    if not _C_IDENTIFIER_RE.fullmatch(namespace.marker):
        parser.error(
            f"--marker must be a valid C identifier, got "
            f"{namespace.marker!r}"
        )

    sources = normalize_source_paths(namespace.source)
    output = Path(namespace.ctypes_output).expanduser().resolve()

    if not output.parent.exists():
        parser.error(f"output parent directory does not exist: {output.parent}")
    if not output.parent.is_dir():
        parser.error(f"output parent path is not a directory: {output.parent}")

    return Arguments(
        sources=sources,
        ctypes_output=output,
        clang_args=tuple(namespace.clang_arg),
        marker=namespace.marker,
        msvc_env=bool(namespace.msvc_env),
        check=bool(namespace.check),
        verbose=bool(namespace.verbose),
    )


def get_msvc_include_args() -> tuple[str, ...]:
    """Return active MSVC INCLUDE directories as Clang -imsvc arguments."""
    if os.name != "nt":
        raise GeneratorError(
            "--msvc-env is supported only on Windows"
        )

    include_value = os.environ.get("INCLUDE")
    if not include_value:
        raise GeneratorError(
            "--msvc-env was specified, but the INCLUDE environment "
            "variable is not defined or is empty"
        )

    arguments: list[str] = []
    seen: set[str] = set()

    for raw_entry in include_value.split(os.pathsep):
        entry = raw_entry.strip().strip('"')
        if not entry:
            continue

        path = Path(entry).expanduser().resolve()
        if not path.is_dir():
            raise GeneratorError(
                f"MSVC INCLUDE directory does not exist or is not a "
                f"directory: {path}"
            )

        key = os.path.normcase(str(path))
        if key in seen:
            continue

        seen.add(key)
        arguments.extend(("-imsvc", str(path)))

    if not arguments:
        raise GeneratorError(
            "--msvc-env did not find any usable directories in INCLUDE"
        )

    return tuple(arguments)


def build_effective_clang_args(arguments: Arguments) -> tuple[str, ...]:
    """Combine user-supplied parser arguments with optional MSVC includes."""
    result = list(arguments.clang_args)

    if arguments.msvc_env:
        result.extend(get_msvc_include_args())

    return tuple(result)


def normalize_source_paths(values: Iterable[str]) -> tuple[Path, ...]:
    result: list[Path] = []
    seen: dict[str, Path] = {}

    for value in values:
        path = Path(value).expanduser().resolve()
        if not path.exists():
            raise argparse.ArgumentTypeError(
                f"source file does not exist: {path}"
            )
        if not path.is_file():
            raise argparse.ArgumentTypeError(
                f"source path is not a regular file: {path}"
            )

        key = os.path.normcase(str(path))
        previous = seen.get(key)
        if previous is not None:
            raise argparse.ArgumentTypeError(
                f"duplicate source path: {path}"
            )

        seen[key] = path
        result.append(path)

    return tuple(result)


def _diagnostic_severity_name(severity: int) -> str:
    names = {
        Diagnostic.Ignored: "ignored",
        Diagnostic.Note: "note",
        Diagnostic.Warning: "warning",
        Diagnostic.Error: "error",
        Diagnostic.Fatal: "fatal",
    }
    return names.get(severity, f"severity-{severity}")


def _diagnostic_sort_key(diagnostic: Diagnostic) -> tuple[str, int, int, int, str]:
    location = diagnostic.location
    filename = location.file.name if location.file is not None else ""
    return (
        os.path.normcase(filename),
        int(location.line),
        int(location.column),
        int(diagnostic.severity),
        str(diagnostic.spelling),
    )


def collect_translation_unit_diagnostics(
    translation_unit: TranslationUnit,
) -> tuple[Diagnostic, ...]:
    return tuple(
        sorted(
            translation_unit.diagnostics,
            key=_diagnostic_sort_key,
        )
    )


def _format_clang_diagnostic(diagnostic: Diagnostic) -> str:
    location = diagnostic.location
    severity = _diagnostic_severity_name(diagnostic.severity)
    if location.file is None:
        return f"{severity}: {diagnostic.spelling}"

    path = _display_path(Path(location.file.name))
    return (
        f"{path}:{location.line}:{location.column}: "
        f"{severity}: {diagnostic.spelling}"
    )


def parse_translation_unit(
    index: Index,
    source: Path,
    clang_args: Sequence[str],
) -> TranslationUnit:
    try:
        translation_unit = index.parse(
            str(source),
            args=list(clang_args),
            options=TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
        )
    except Exception as exc:
        raise ParseError(
            f"failed to parse {_display_path(source)}: {exc}"
        ) from exc

    diagnostics = collect_translation_unit_diagnostics(translation_unit)
    fatal = tuple(
        item
        for item in diagnostics
        if item.severity >= Diagnostic.Error
    )
    if fatal:
        rendered = "\n".join(
            f"  {_format_clang_diagnostic(item)}"
            for item in fatal
        )
        raise ParseError(
            f"libclang reported errors while parsing "
            f"{_display_path(source)}:\n{rendered}"
        )

    return translation_unit


def walk_cursors(cursor: Cursor) -> Iterable[Cursor]:
    yield cursor
    for child in cursor.get_children():
        yield from walk_cursors(child)


def _same_path(left: Path, right: Path) -> bool:
    return os.path.normcase(str(left.resolve())) == os.path.normcase(
        str(right.resolve())
    )


def cursor_is_in_source(cursor: Cursor, source: Path) -> bool:
    if cursor.location.file is None:
        return False
    return _same_path(Path(cursor.location.file.name), source)


def _source_location(cursor: Cursor) -> SourceLocation:
    if cursor.location.file is None:
        raise DeclarationExtractionError(
            f'cursor "{cursor.spelling}" has no source file'
        )
    return SourceLocation(
        file=Path(cursor.location.file.name).resolve(),
        line=int(cursor.location.line),
        column=int(cursor.location.column),
    )


def _find_function_body(cursor: Cursor) -> Cursor:
    bodies = [
        child
        for child in cursor.get_children()
        if child.kind == CursorKind.COMPOUND_STMT
    ]
    if len(bodies) != 1:
        location = _source_location(cursor)
        raise DeclarationExtractionError(
            f'{_location_text(location)}: function "{cursor.spelling}" '
            f"does not have exactly one compound-statement body"
        )
    return bodies[0]


def _source_bytes(path: Path, cache: dict[Path, bytes]) -> bytes:
    resolved = path.resolve()
    try:
        return cache[resolved]
    except KeyError:
        try:
            data = resolved.read_bytes()
        except OSError as exc:
            raise DeclarationExtractionError(
                f"cannot read source file {_display_path(resolved)}: {exc}"
            ) from exc
        cache[resolved] = data
        return data


def _declaration_tokens(
    cursor: Cursor,
    declaration_start_offset: int,
    body_start_offset: int,
) -> tuple[str, ...]:
    tokens: list[str] = []

    for token in cursor.get_tokens():
        try:
            token_start = int(token.extent.start.offset)
        except Exception:
            token_start = int(token.location.offset)

        if token_start < declaration_start_offset:
            continue
        if token_start >= body_start_offset:
            break

        tokens.append(token.spelling)

    return tuple(tokens)


def extract_literal_declaration(
    cursor: Cursor,
    source_cache: dict[Path, bytes],
) -> tuple[str, tuple[str, ...]]:
    location = _source_location(cursor)
    body = _find_function_body(cursor)

    start_offset = int(cursor.extent.start.offset)
    body_start_offset = int(body.extent.start.offset)
    if body_start_offset <= start_offset:
        raise DeclarationExtractionError(
            f'{_location_text(location)}: invalid declaration extent for '
            f'"{cursor.spelling}"'
        )

    data = _source_bytes(location.file, source_cache)
    if start_offset < 0 or body_start_offset > len(data):
        raise DeclarationExtractionError(
            f'{_location_text(location)}: declaration byte range for '
            f'"{cursor.spelling}" is outside the source file'
        )

    raw = data[start_offset:body_start_offset]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise DeclarationExtractionError(
            f'{_location_text(location)}: declaration for '
            f'"{cursor.spelling}" is not valid UTF-8: {exc}'
        ) from exc

    normalized_lines = [
        line.rstrip()
        for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    ]
    while normalized_lines and normalized_lines[0] == "":
        normalized_lines.pop(0)
    while normalized_lines and normalized_lines[-1] == "":
        normalized_lines.pop()

    declaration = "\n".join(normalized_lines)
    if not declaration.strip():
        raise DeclarationExtractionError(
            f'{_location_text(location)}: empty declaration extracted for '
            f'"{cursor.spelling}"'
        )

    return declaration, _declaration_tokens(
        cursor,
        start_offset,
        body_start_offset,
    )


def _typedef_name(c_type: Type) -> str | None:
    if c_type.kind != TypeKind.TYPEDEF:
        return None
    declaration = c_type.get_declaration()
    name = declaration.spelling.strip()
    return name or None


def normalize_clang_type(c_type: Type, depth: int = 0) -> CType:
    if depth > 64:
        raise UnsupportedTypeError(
            f"type nesting exceeds the supported depth: {c_type.spelling!r}"
        )

    kind_name = c_type.kind.name
    canonical = c_type.get_canonical()
    pointee = None
    if c_type.kind == TypeKind.POINTER:
        pointee = normalize_clang_type(c_type.get_pointee(), depth + 1)

    canonical_model = None
    if c_type.kind == TypeKind.TYPEDEF:
        canonical_key = (
            canonical.kind.name,
            " ".join(canonical.spelling.split()),
        )
        source_key = (
            c_type.kind.name,
            " ".join(c_type.spelling.split()),
        )
        if canonical_key != source_key:
            canonical_model = normalize_clang_type(
                canonical,
                depth + 1,
            )

    return CType(
        kind=kind_name,
        spelling=" ".join(c_type.spelling.split()),
        canonical_spelling=" ".join(canonical.spelling.split()),
        const=bool(c_type.is_const_qualified()),
        volatile=bool(c_type.is_volatile_qualified()),
        restrict=bool(c_type.is_restrict_qualified()),
        typedef_name=_typedef_name(c_type),
        pointee=pointee,
        canonical=canonical_model,
    )


def _calling_convention_tokens(function: Function) -> tuple[str, ...]:
    return tuple(
        token
        for token in function.declaration_tokens
        if token in _UNSUPPORTED_CALLING_CONVENTION_TOKENS
    )


def extract_function_model(
    cursor: Cursor,
    source_index: int,
    source_cache: dict[Path, bytes],
) -> Function:
    declaration_text, declaration_tokens = extract_literal_declaration(
        cursor,
        source_cache,
    )

    parameters: list[Parameter] = []
    for argument in cursor.get_arguments():
        parameters.append(
            Parameter(
                name=argument.spelling,
                c_type=normalize_clang_type(argument.type),
                location=_source_location(argument),
            )
        )

    return Function(
        name=cursor.spelling,
        result_type=normalize_clang_type(cursor.result_type),
        parameters=tuple(parameters),
        variadic=bool(cursor.type.is_function_variadic()),
        declaration_text=declaration_text,
        location=_source_location(cursor),
        source_index=source_index,
        declaration_tokens=declaration_tokens,
    )


def _linkage_is_external(cursor: Cursor) -> bool:
    return cursor.linkage in {
        LinkageKind.EXTERNAL,
        getattr(LinkageKind, "UNIQUE_EXTERNAL", LinkageKind.EXTERNAL),
    }


def find_selected_functions(
    translation_unit: TranslationUnit,
    source: Path,
    source_index: int,
    marker: str,
    source_cache: dict[Path, bytes],
    verbose: bool,
) -> list[Function]:
    result: list[Function] = []

    for cursor in walk_cursors(translation_unit.cursor):
        if cursor.kind != CursorKind.FUNCTION_DECL:
            continue
        if not cursor.is_definition():
            continue
        if not cursor_is_in_source(cursor, source):
            continue
        if not cursor.spelling:
            location = _source_location(cursor)
            raise GeneratorError(
                f"{_location_text(location)}: selected function has no name"
            )

        declaration, tokens = extract_literal_declaration(cursor, source_cache)
        marker_count = sum(1 for token in tokens if token == marker)
        if marker_count == 0:
            continue

        if marker_count > 1 and verbose:
            print(
                f'WARNING: {_location_text(_source_location(cursor))}: '
                f'function "{cursor.spelling}" contains marker '
                f'"{marker}" {marker_count} times',
                file=sys.stderr,
            )

        if not _linkage_is_external(cursor):
            location = _source_location(cursor)
            raise GeneratorError(
                f'{_location_text(location)}: marked function '
                f'"{cursor.spelling}" does not have external linkage under '
                f"the effective Clang arguments"
            )

        function = extract_function_model(
            cursor,
            source_index,
            source_cache,
        )
        # Reuse the extraction already performed above.
        function = Function(
            name=function.name,
            result_type=function.result_type,
            parameters=function.parameters,
            variadic=function.variadic,
            declaration_text=declaration,
            location=function.location,
            source_index=function.source_index,
            declaration_tokens=tokens,
        )
        result.append(function)

    return result


def _type_details(c_type: CType) -> str:
    return (
        f"source spelling={c_type.spelling!r}, "
        f"canonical spelling={c_type.canonical_spelling!r}, "
        f"libclang kind={c_type.kind}"
    )


def _unsupported_type(
    function: Function,
    c_type: CType,
    position: str,
) -> UnsupportedTypeError:
    return UnsupportedTypeError(
        f'{_location_text(function.location)}: {position} of '
        f'"{function.name}" uses unsupported type '
        f"{c_type.spelling!r} ({_type_details(c_type)})"
    )


def _canonical_kind_name(c_type: CType) -> str:
    # Canonical spelling is diagnostic only in the normalized model. For
    # typedefs, the underlying TypeKind must be captured by libclang before
    # normalization. A supported typedef is mapped explicitly; any other
    # typedef is rejected rather than guessed from spelling.
    return c_type.kind


def map_ctypes_type(
    c_type: CType,
    *,
    for_result: bool,
    function: Function,
    position: str,
) -> str:
    if c_type.kind == "VOID":
        if for_result:
            return "None"
        raise _unsupported_type(function, c_type, position)

    if c_type.kind == "POINTER":
        if c_type.pointee is None:
            raise _unsupported_type(function, c_type, position)

        if c_type.pointee.kind == "VOID":
            return "ctypes.c_void_p"

        inner = map_ctypes_type(
            c_type.pointee,
            for_result=False,
            function=function,
            position=position,
        )
        return f"ctypes.POINTER({inner})"

    if c_type.kind == "TYPEDEF":
        typedef_name = c_type.typedef_name
        if typedef_name in _TYPEDEF_MAP:
            return _TYPEDEF_MAP[typedef_name]

        # Standard C bool is frequently expanded to _Bool before reaching the
        # AST, but accommodate a surviving bool typedef spelling.
        if typedef_name == "bool":
            return "ctypes.c_bool"

        if c_type.canonical is not None:
            return map_ctypes_type(
                c_type.canonical,
                for_result=for_result,
                function=function,
                position=position,
            )

        raise _unsupported_type(function, c_type, position)

    direct = _DIRECT_KIND_MAP.get(_canonical_kind_name(c_type))
    if direct is not None:
        return direct

    raise _unsupported_type(function, c_type, position)


def _validate_expression(expression: str) -> bool:
    if expression in _ALLOWED_LEAF_EXPRESSIONS:
        return True

    prefix = "ctypes.POINTER("
    if not expression.startswith(prefix) or not expression.endswith(")"):
        return False

    inner = expression[len(prefix):-1]
    return bool(inner) and _validate_expression(inner)


def validate_function(function: Function) -> tuple[tuple[str, ...], str]:
    if function.variadic:
        raise GeneratorError(
            f'{_location_text(function.location)}: selected function '
            f'"{function.name}" is variadic'
        )

    unsupported_conventions = _calling_convention_tokens(function)
    if unsupported_conventions:
        rendered = ", ".join(sorted(set(unsupported_conventions)))
        raise GeneratorError(
            f'{_location_text(function.location)}: selected function '
            f'"{function.name}" uses unsupported calling-convention '
            f"token(s): {rendered}"
        )

    argument_expressions: list[str] = []
    for index, parameter in enumerate(function.parameters):
        expression = map_ctypes_type(
            parameter.c_type,
            for_result=False,
            function=function,
            position=f"parameter {index}",
        )
        if not _validate_expression(expression):
            raise GeneratorError(
                f'{_location_text(parameter.location)}: internal type mapping '
                f'error for parameter {index} of "{function.name}"'
            )
        argument_expressions.append(expression)

    result_expression = map_ctypes_type(
        function.result_type,
        for_result=True,
        function=function,
        position="return type",
    )
    if not _validate_expression(result_expression):
        raise GeneratorError(
            f'{_location_text(function.location)}: internal type mapping '
            f'error for return type of "{function.name}"'
        )

    return tuple(argument_expressions), result_expression


def validate_unique_functions(functions: Sequence[Function]) -> None:
    by_name: dict[str, Function] = {}
    for function in functions:
        previous = by_name.get(function.name)
        if previous is not None:
            raise DuplicateSymbolError(
                f'duplicate selected function "{function.name}":\n'
                f"  {_location_text(previous.location)}\n"
                f"  {_location_text(function.location)}"
            )
        by_name[function.name] = function


def render_declaration_comment(declaration: str) -> list[str]:
    lines = ["    # C declaration:"]
    for line in declaration.split("\n"):
        lines.append(f"    # {line}" if line else "    #")
    return lines


def render_function_binding(
    function: Function,
    argument_expressions: Sequence[str],
    result_expression: str,
) -> list[str]:
    lines = render_declaration_comment(function.declaration_text)
    lines.append("")
    lines.append(f"    dll.{function.name}.argtypes = [")
    for expression in argument_expressions:
        lines.append(f"        {expression},")
    lines.append("    ]")
    lines.append(
        f"    dll.{function.name}.restype = {result_expression}"
    )
    return lines


def render_module(functions: Sequence[Function]) -> str:
    ordered = sorted(
        functions,
        key=lambda item: (
            item.source_index,
            item.location.line,
            item.location.column,
            item.name,
        ),
    )
    generated_names = sorted(function.name for function in functions)

    mapped: dict[str, tuple[tuple[str, ...], str]] = {}
    for function in ordered:
        mapped[function.name] = validate_function(function)

    lines = [
        '"""Generated ctypes declarations.',
        "",
        "This file is generated. Do not edit manually.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import ctypes",
        "",
        "",
        "__all__ = (",
        '    "GENERATED_FUNCTIONS",',
        '    "bind",',
        ")",
        "",
        "",
        "GENERATED_FUNCTIONS = (",
    ]

    for name in generated_names:
        lines.append(f'    "{name}",')
    lines.extend(
        [
            ")",
            "",
            "",
            "def bind(dll: ctypes.CDLL) -> ctypes.CDLL:",
        ]
    )

    for index, function in enumerate(ordered):
        if index:
            lines.append("")
        argument_expressions, result_expression = mapped[function.name]
        lines.extend(
            render_function_binding(
                function,
                argument_expressions,
                result_expression,
            )
        )

    lines.extend(
        [
            "",
            "    return dll",
            "",
        ]
    )

    return "\n".join(lines)


def validate_generated_module(
    generated_text: str,
    output_path: Path,
    functions: Sequence[Function],
) -> None:
    if not functions:
        raise GeneratorError(
            "no marked function definitions were found"
        )

    try:
        compile(generated_text, str(output_path), "exec")
    except SyntaxError as exc:
        raise GeneratorError(
            f"generated Python module is invalid: {exc}"
        ) from exc

    names = [function.name for function in functions]
    if len(names) != len(set(names)):
        raise GeneratorError(
            "internal consistency failure: generated function names "
            "are not unique"
        )


def write_output_atomically(path: Path, text: str) -> bool:
    encoded = text.encode("utf-8")

    if path.exists():
        if not path.is_file():
            raise GeneratorError(
                f"output path exists but is not a regular file: {path}"
            )
        try:
            if path.read_bytes() == encoded:
                return False
        except OSError as exc:
            raise GeneratorError(
                f"cannot read existing output {path}: {exc}"
            ) from exc

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(encoded)
            handle.flush()

        os.replace(temp_path, path)
        temp_path = None
    except OSError as exc:
        raise GeneratorError(
            f"cannot write output {path}: {exc}"
        ) from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass

    return True


def check_output(path: Path, text: str) -> bool:
    if not path.is_file():
        return False
    try:
        return path.read_bytes() == text.encode("utf-8")
    except OSError as exc:
        raise GeneratorError(
            f"cannot read output {path}: {exc}"
        ) from exc


def generate(arguments: Arguments) -> tuple[str, tuple[Function, ...]]:
    effective_clang_args = build_effective_clang_args(arguments)

    if arguments.verbose:
        print(
            "clang arguments:",
            " ".join(effective_clang_args)
            if effective_clang_args
            else "(none)",
        )

    index = Index.create()
    source_cache: dict[Path, bytes] = {}
    functions: list[Function] = []

    for source_index, source in enumerate(arguments.sources):
        if arguments.verbose:
            print(f"parsing: {_display_path(source)}")

        translation_unit = parse_translation_unit(
            index,
            source,
            effective_clang_args,
        )
        selected = find_selected_functions(
            translation_unit,
            source,
            source_index,
            arguments.marker,
            source_cache,
            arguments.verbose,
        )
        functions.extend(selected)

    if not functions:
        raise GeneratorError(
            f'no function definitions marked with '
            f'"{arguments.marker}" were found'
        )

    validate_unique_functions(functions)
    generated_text = render_module(functions)
    validate_generated_module(
        generated_text,
        arguments.ctypes_output,
        functions,
    )

    if arguments.verbose:
        print(f"selected functions: {len(functions)}")
        for name in sorted(function.name for function in functions):
            print(f"  {name}")

    return generated_text, tuple(functions)


def _print_error(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        arguments = parse_args(argv)
        generated_text, _ = generate(arguments)

        if arguments.check:
            current = check_output(
                arguments.ctypes_output,
                generated_text,
            )
            if arguments.verbose:
                print(
                    "output status:",
                    "current" if current else "missing or stale",
                )
            return EXIT_SUCCESS if current else EXIT_STALE

        changed = write_output_atomically(
            arguments.ctypes_output,
            generated_text,
        )
        if arguments.verbose:
            print(
                "output status:",
                "updated" if changed else "unchanged",
            )
            print(f"output: {arguments.ctypes_output}")
        return EXIT_SUCCESS

    except argparse.ArgumentTypeError as exc:
        _print_error(str(exc))
        return EXIT_ERROR
    except GeneratorError as exc:
        _print_error(str(exc))
        return EXIT_ERROR
    except Exception as exc:  # defensive top-level conversion
        _print_error(f"unexpected failure: {exc}")
        return EXIT_ERROR


if __name__ == "__main__":
    raise SystemExit(main())
