import sqlite3

import pytest

from .support import (
    CYRILLIC,
    LANGUAGE_ERROR,
    LATIN,
)


def test_function_over_rows(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        WITH languages(language) AS (
          VALUES ('en'), ('ru')
        )
        SELECT language, length(alpha_string(language))
        FROM languages
        ORDER BY language
        """
    ).fetchall()

    assert rows == [("en", len(LATIN)), ("ru", len(CYRILLIC))]


def test_invalid_row_aborts_statement(connection: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.OperationalError) as error:
        connection.execute(
            """
            WITH languages(language) AS (
              VALUES ('en'), ('invalid'), ('ru')
            )
            SELECT alpha_string(language)
            FROM languages
            """
        ).fetchall()

    assert str(error.value) == LANGUAGE_ERROR


def test_deterministic_function_in_expression_index(
    connection: sqlite3.Connection,
) -> None:
    connection.executescript(
        """
        CREATE TABLE language_data(
          language TEXT NOT NULL
        );

        CREATE INDEX language_data_initial
        ON language_data(
          alpha_string(language, 0, 1)
        );
        """
    )


def test_innocuous_function_with_untrusted_schema(
    connection: sqlite3.Connection,
) -> None:
    connection.executescript(
        """
        PRAGMA trusted_schema = OFF;

        CREATE TABLE language_data(
          language TEXT NOT NULL,
          initial TEXT GENERATED ALWAYS AS (
            alpha_string(language, 0, 1)
          ) STORED
        );

        INSERT INTO language_data(language)
        VALUES ('en');
        """
    )

    assert connection.execute("SELECT initial FROM language_data").fetchone() == ("A",)
