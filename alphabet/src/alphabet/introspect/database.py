from __future__ import annotations

import os
import json
import sqlite3
from collections.abc import Iterable, Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any, TypeAlias


__all__ = (
    "CFFIModelDB",
)


PathLike: TypeAlias = str | Path
CTypeRow: TypeAlias = Mapping[str, Any]
CTypeRows: TypeAlias = CTypeRow | Iterable[CTypeRow]


class CTypeAttributes(StrEnum):
    """Column names accepted by the ``ctypes`` table."""
    ID        = "id"
    NAME      = "name"
    CATEGORY  = "category"
    CNAME     = "cname"
    KIND      = "kind"
    GROUP     = "group"
    ITEM      = "item"
    LENGTH    = "length"
    FIELDS    = "fields"
    ARGS      = "args"
    RESULT    = "result"
    ELLIPSIS  = "ellipsis"
    ABI       = "abi"
    ELEMENTS  = "elements"
    RELEMENTS = "relements"


def _normalize_value(value: Any) -> Any:
    """Convert values unsupported by SQLite to JSON or plain strings.

    Values natively accepted by :mod:`sqlite3` are preserved. Other values are
    first serialized as JSON. If JSON serialization fails, they are converted
    by calling :class:`str`.
    """
    if value is None or isinstance(value, (str, int, float, bytes)):
        return value
    elif value is isinstance(value, set):
        return json.dumps(sorted(value))

    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(value)


def _coerce_rows(rows: CTypeRows) -> tuple[list[CTypeRow], bool]:
    """Normalize the input into a list of rows.

    Returns:
        A pair containing the normalized row list and a flag indicating whether
        the caller supplied one mapping rather than an iterable of mappings.

    Raises:
        TypeError:
            If ``rows`` is neither a mapping nor an iterable of mappings.
        ValueError:
            If an empty iterable is supplied.
    """
    if isinstance(rows, Mapping):
        return [rows], True

    if isinstance(rows, (str, bytes, bytearray)):
        raise TypeError(
            "ctypes must be a mapping or an iterable of mappings"
        )

    try:
        result = list(rows)
    except TypeError as error:
        raise TypeError(
            "ctypes must be a mapping or an iterable of mappings"
        ) from error

    if not result:
        raise ValueError("ctypes cannot be an empty iterable")

    return result, False


def _normalize_row(row: CTypeRow) -> dict[str, Any]:
    """Validate and normalize one ``ctypes`` row.

    Raises:
        TypeError:
            If ``row`` is not a mapping.
        ValueError:
            If the mapping is empty or contains an unknown column name.
    """
    if not isinstance(row, Mapping):
        raise TypeError(
            "Each ctypes row must be a mapping, "
            f"not {type(row).__name__}"
        )

    if not row:
        raise ValueError("A ctypes row cannot be empty")

    normalized = {
        str(key): _normalize_value(value)
        for key, value in row.items()
    }

    unknown_columns = normalized.keys() - frozenset(CTypeAttributes)
    if unknown_columns:
        columns = ", ".join(sorted(unknown_columns))
        raise ValueError(f"Unknown ctypes column(s): {columns}")

    return normalized


def _resolve_database_path(
    database: PathLike | None,
    filename: str = "cffi_model.db"
) -> Path:
    """Resolve a database file or database-directory argument.

    Existing paths are classified by their filesystem type. A nonexistent
    path is classified as a database file only when its final component has
    an extension and the supplied path does not end with a path separator.
    Directory arguments must identify existing directories.
    """
    module_directory = Path(__file__).resolve().parent

    if database is None:
        return module_directory / filename

    database_text = os.fspath(database)
    database_path = Path(database).expanduser()

    path_separators = tuple(
        separator
        for separator in (os.sep, os.altsep)
        if separator is not None
    )
    terminal_path_separator = database_text.endswith(path_separators)

    if database_path.exists():
        resolved = database_path.resolve()

        if resolved.is_dir():
            return resolved / filename

        if resolved.is_file():
            return resolved

        raise ValueError(
            "Database path must identify a regular file or directory: "
            f"{resolved}"
        )

    resolved = database_path.resolve()

    if terminal_path_separator or not database_path.suffix:
        raise FileNotFoundError(
            f"Database directory does not exist: {resolved}"
        )

    if not resolved.parent.is_dir():
        raise FileNotFoundError(
            "Database parent directory does not exist: "
            f"{resolved.parent}"
        )

    return resolved


class CFFIModelDB:
    """Manage the SQLite database containing the CFFI model.

    By default, the database and schema files are located beside this module:

    - ``cffi_model.db``
    - ``schema.sql``

    If the database file does not exist, it is created and initialized by
    executing the complete contents of ``schema.sql``.
    """

    db_path: Path
    schema_path: Path
    db: sqlite3.Connection

    def __init__(
        self,
        database: PathLike | None = None,
        schema: PathLike | None = None,
    ) -> None:
        """Open or create the CFFI model database.

        Args:
            database:
                Database path. The default is ``cffi_model.db`` beside this
                module.
            schema:
                Schema path. The default is ``schema.sql`` beside this module.
                The schema is used only when the database file does not exist.

        Raises:
            FileNotFoundError:
                If a new database must be initialized but the schema file does
                not exist.
            sqlite3.Error:
                If SQLite cannot open or initialize the database.
        """
        self.db_path = _resolve_database_path(database)

        self.schema_path = (
            Path(schema).expanduser().resolve()
            if schema is not None
            else Path(__file__).resolve().parent / "schema.sql"
        )

        database_exists = self.db_path.exists()

        if not database_exists and not self.schema_path.is_file():
            raise FileNotFoundError(
                f"Schema file not found: {self.schema_path}"
            )

        self.db = sqlite3.connect(self.db_path)

        try:
            self.db.execute("PRAGMA foreign_keys = ON")

            if not database_exists:
                self._initialize_schema()
        except Exception:
            self.db.close()

            if not database_exists:
                try:
                    self.db_path.unlink(missing_ok=True)
                except OSError:
                    pass

            raise

    def __enter__(self) -> CFFIModelDB:
        return self

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object | None,
    ) -> None:
        if exception_type is None:
            self.db.commit()
        else:
            self.db.rollback()

        self.close()

    def close(self) -> None:
        """Close the database connection."""
        self.db.close()

    def _initialize_schema(self) -> None:
        """Initialize a newly created database from ``schema.sql``."""
        schema_sql = self.schema_path.read_text(encoding="utf-8")

        try:
            self.db.executescript(schema_sql)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def ctypes_insert(
        self,
        ctypes: CTypeRows,
        db: sqlite3.Connection | None = None,
    ) -> int | list[int]:
        """Insert or update one or more rows in the ``ctypes`` table.

        A new row is inserted when neither its ``name`` nor its ``cname`` conflicts
        with an existing row. If a uniqueness conflict occurs, the existing row is
        updated with the values supplied by the input mapping.

        Only supplied columns are updated. The ``id`` primary key is never changed
        during an update.

        Args:
            ctypes:
                One mapping representing a row, or an iterable of mappings.
                Keys must correspond to columns declared by
                :class:`CTypeAttributes`. Values unsupported by SQLite are
                converted to strings.
            db:
                Optional SQLite connection. The instance connection is used when
                this argument is omitted.

        Returns:
            The affected row ID when one mapping is supplied. When an iterable is
            supplied, returns the affected row IDs in input order.

        Raises:
            TypeError:
                If the input or one of its rows is not a mapping.
            ValueError:
                If a row is empty, an iterable is empty, a row contains an unknown
                column, or a row contains no column that can be updated.
            sqlite3.Error:
                If SQLite rejects an insertion or update.
        """
        db = self.db if db is None else db

        rows, single_row = _coerce_rows(ctypes)
        normalized_rows = [_normalize_row(row) for row in rows]

        affected_ids: list[int] = []

        with db:
            for row in normalized_rows:
                columns = tuple(row)
                update_columns = tuple(
                    column
                    for column in columns
                    if column != CTypeAttributes.ID
                )

                if not update_columns:
                    raise ValueError(
                        'A ctypes row must contain a column other than "id"'
                    )

                column_sql = ", ".join(f'"{column}"' for column in columns)
                placeholders = ", ".join("?" for _ in columns)
                update_sql = ", ".join(
                    f'"{column}" = excluded."{column}"'
                    for column in update_columns
                )

                cursor = db.execute(
                    (
                        f'INSERT INTO "ctypes" ({column_sql}) '
                        f"VALUES ({placeholders}) "
                        f"ON CONFLICT DO UPDATE SET {update_sql} "
                        f'RETURNING "id"'
                    ),
                    tuple(row[column] for column in columns),
                )

                result = cursor.fetchone()
                if result is None:
                    raise sqlite3.DatabaseError(
                        "SQLite did not return the affected row ID"
                    )

                affected_ids.append(result[0])

        if single_row:
            return affected_ids[0]

        return affected_ids


def main() -> int:
    with CFFIModelDB():
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
