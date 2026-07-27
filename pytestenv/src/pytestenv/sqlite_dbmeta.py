"""
Report SQLite engine metadata from a blank in-memory database.

The program executes a fixed set of SQLite metadata queries and prints a
deterministic aligned plain-text report.

Usage:
    python sqlite_dbmeta.py
"""

from __future__ import annotations

import sqlite3
import sys
from dataclasses import dataclass


SQL_RUNTIME = """
SELECT sqlite_version(), sqlite_source_id();
"""

SQL_MODULES = """
SELECT name
FROM pragma_module_list()
ORDER BY name;
"""

SQL_COLLATIONS = """
SELECT seq, name
FROM pragma_collation_list()
ORDER BY name;
"""

SQL_FUNCTIONS = """
SELECT name, builtin, type, enc, narg
FROM pragma_function_list()
ORDER BY name, builtin, narg;
"""

SQL_PRAGMAS = """
SELECT name
FROM pragma_pragma_list()
ORDER BY name;
"""

SQL_COMPILE_OPTIONS = """
SELECT compile_options
FROM pragma_compile_options()
ORDER BY compile_options;
"""


class DbMetaError(RuntimeError):
    """Raised when SQLite metadata collection, validation, or rendering fails."""


@dataclass(frozen=True)
class QueryResult:
    """Immutable materialized result of one SQLite query."""

    columns: tuple[str, ...]
    rows: tuple[tuple[object, ...], ...]


@dataclass(frozen=True)
class MetadataReport:
    """All SQLite metadata result sets required by the report."""

    runtime: QueryResult
    modules: QueryResult
    collations: QueryResult
    functions: QueryResult
    pragmas: QueryResult
    compile_options: QueryResult


def execute_query(
    connection: sqlite3.Connection,
    sql: str,
    description: str,
) -> QueryResult:
    """Execute one metadata query and fully materialize its result."""

    cursor = connection.cursor()
    try:
        try:
            cursor.execute(sql)
        except sqlite3.Error as exc:
            raise DbMetaError(f"failed to query {description}: {exc}") from exc

        if cursor.description is None:
            raise DbMetaError(
                f"{description} query did not produce a result set"
            )

        columns = tuple(
            column_description[0]
            for column_description in cursor.description
        )
        rows = tuple(tuple(row) for row in cursor.fetchall())
    finally:
        cursor.close()

    expected_width = len(columns)
    for row_number, row in enumerate(rows, start=1):
        if len(row) != expected_width:
            raise DbMetaError(
                f"invalid {description} result at row {row_number}: "
                f"expected {expected_width} columns, received {len(row)}"
            )

    return QueryResult(columns=columns, rows=rows)


def require_column_count(
    result: QueryResult,
    expected: int,
    description: str,
) -> None:
    """Require a result to contain the specified number of columns."""

    actual = len(result.columns)
    if actual != expected:
        raise DbMetaError(
            f"invalid {description} result: "
            f"expected {expected} columns, received {actual}"
        )


def validate_runtime_result(result: QueryResult) -> None:
    """Validate the shape and values returned by the runtime query."""

    require_column_count(result, 2, "SQLite runtime")

    if len(result.rows) != 1:
        raise DbMetaError(
            f"invalid SQLite runtime result: "
            f"expected 1 row, received {len(result.rows)}"
        )

    sqlite_version, sqlite_source_id = result.rows[0]

    if sqlite_version is None:
        raise DbMetaError(
            "invalid SQLite runtime result: SQLite version is NULL"
        )
    if sqlite_source_id is None:
        raise DbMetaError(
            "invalid SQLite runtime result: SQLite source ID is NULL"
        )
    if not isinstance(sqlite_version, str):
        raise DbMetaError(
            "invalid SQLite runtime result: SQLite version is not text"
        )
    if not isinstance(sqlite_source_id, str):
        raise DbMetaError(
            "invalid SQLite runtime result: SQLite source ID is not text"
        )


def collect_metadata(connection: sqlite3.Connection) -> MetadataReport:
    """Execute and validate the six approved SQLite metadata queries."""

    runtime = execute_query(
        connection,
        SQL_RUNTIME,
        "SQLite runtime metadata",
    )
    modules = execute_query(
        connection,
        SQL_MODULES,
        "module list",
    )
    collations = execute_query(
        connection,
        SQL_COLLATIONS,
        "collation list",
    )
    functions = execute_query(
        connection,
        SQL_FUNCTIONS,
        "function list",
    )
    pragmas = execute_query(
        connection,
        SQL_PRAGMAS,
        "pragma list",
    )
    compile_options = execute_query(
        connection,
        SQL_COMPILE_OPTIONS,
        "compile-option list",
    )

    validate_runtime_result(runtime)
    require_column_count(modules, 1, "module list")
    require_column_count(collations, 2, "collation list")
    require_column_count(functions, 5, "function list")
    require_column_count(pragmas, 1, "pragma list")
    require_column_count(compile_options, 1, "compile-option list")

    return MetadataReport(
        runtime=runtime,
        modules=modules,
        collations=collations,
        functions=functions,
        pragmas=pragmas,
        compile_options=compile_options,
    )


def count_distinct_non_null(
    result: QueryResult,
    column_name: str,
) -> int:
    """Count distinct non-NULL values in one named result column."""

    try:
        column_index = result.columns.index(column_name)
    except ValueError as exc:
        raise DbMetaError(
            f"required column {column_name!r} is missing"
        ) from exc

    return len(
        {
            row[column_index]
            for row in result.rows
            if row[column_index] is not None
        }
    )


def build_summary(report: MetadataReport) -> QueryResult:
    """Build the derived Summary table from collected query results."""

    sqlite_version, sqlite_source_id = report.runtime.rows[0]

    return QueryResult(
        columns=("item", "value"),
        rows=(
            ("SQLite version", sqlite_version),
            ("SQLite source ID", sqlite_source_id),
            (
                "Module names",
                count_distinct_non_null(report.modules, "name"),
            ),
            ("Collations", len(report.collations.rows)),
            (
                "Function names",
                count_distinct_non_null(report.functions, "name"),
            ),
            (
                "Function registrations",
                len(report.functions.rows),
            ),
            ("Pragmas", len(report.pragmas.rows)),
            ("Compile options", len(report.compile_options.rows)),
        ),
    )


def render_value(value: object) -> str:
    """Render one SQLite metadata value as deterministic plain text."""

    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float, str)):
        return str(value)
    if isinstance(value, bytes):
        raise DbMetaError(
            "unexpected BLOB value in SQLite metadata result"
        )

    raise DbMetaError(
        "unexpected SQLite metadata value type: "
        f"{type(value).__name__}"
    )


def numeric_columns(result: QueryResult) -> tuple[bool, ...]:
    """Return one flag per column indicating integer-only alignment."""

    flags: list[bool] = []

    for column_index in range(len(result.columns)):
        values = [
            row[column_index]
            for row in result.rows
            if row[column_index] is not None
        ]
        flags.append(
            bool(values)
            and all(isinstance(value, int) for value in values)
        )

    return tuple(flags)


def render_table(
    result: QueryResult,
    *,
    force_left_align: bool = False,
) -> list[str]:
    """Render a query result as an aligned ASCII table."""

    column_count = len(result.columns)
    if column_count == 0:
        raise DbMetaError("cannot render a table without columns")

    rendered_rows = tuple(
        tuple(render_value(value) for value in row)
        for row in result.rows
    )

    widths: list[int] = []
    for column_index, column_name in enumerate(result.columns):
        width = len(column_name)
        for row in rendered_rows:
            width = max(width, len(row[column_index]))
        widths.append(width)

    align_right = (
        (False,) * column_count
        if force_left_align
        else numeric_columns(result)
    )

    lines: list[str] = []

    header_cells = [
        column_name.ljust(widths[index])
        if index < column_count - 1
        else column_name
        for index, column_name in enumerate(result.columns)
    ]
    lines.append("  ".join(header_cells))

    separator_cells = [
        "-" * width
        for width in widths
    ]
    lines.append("  ".join(separator_cells))

    for row in rendered_rows:
        cells: list[str] = []
        for column_index, value in enumerate(row):
            is_last = column_index == column_count - 1

            if align_right[column_index]:
                cell = value.rjust(widths[column_index])
            elif is_last:
                cell = value
            else:
                cell = value.ljust(widths[column_index])

            cells.append(cell)

        lines.append("  ".join(cells))

    return lines


def render_section(
    title: str,
    result: QueryResult,
    *,
    force_left_align: bool = False,
) -> list[str]:
    """Render one titled report section."""

    return [
        title,
        "=" * len(title),
        "",
        *render_table(
            result,
            force_left_align=force_left_align,
        ),
    ]


def render_report(report: MetadataReport) -> str:
    """Render the complete report in the required section order."""

    sections = (
        render_section(
            "Summary",
            build_summary(report),
            force_left_align=True,
        ),
        render_section("Modules", report.modules),
        render_section("Collations", report.collations),
        render_section("Functions", report.functions),
        render_section("Pragmas", report.pragmas),
        render_section(
            "Compile Options",
            report.compile_options,
        ),
    )

    return "\n\n".join(
        "\n".join(section)
        for section in sections
    ) + "\n"


def generate_report() -> str:
    """Open the in-memory database, collect metadata, and render the report."""

    try:
        connection = sqlite3.connect(":memory:")
    except sqlite3.Error as exc:
        raise DbMetaError(
            f"failed to open in-memory SQLite database: {exc}"
        ) from exc

    try:
        metadata = collect_metadata(connection)
        return render_report(metadata)
    finally:
        connection.close()


def main() -> int:
    """Run the command-line program."""

    if len(sys.argv) != 1:
        sys.stderr.write("usage: sqlite_dbmeta.py\n")
        return 2

    try:
        report_text = generate_report()
        sys.stdout.write(report_text)
    except DbMetaError as exc:
        sys.stderr.write(f"sqlite_dbmeta: {exc}\n")
        return 1
    except OSError as exc:
        sys.stderr.write(
            f"sqlite_dbmeta: failed to write output: {exc}\n"
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
