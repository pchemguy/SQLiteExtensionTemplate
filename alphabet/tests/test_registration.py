import sqlite3

import pytest

from .support import LATIN


def test_one_argument_form(scalar) -> None:
    assert scalar("SELECT alpha_string('en')") == LATIN


def test_two_argument_form(scalar) -> None:
    assert scalar("SELECT alpha_string('en', 0)") == LATIN


def test_three_argument_form(scalar) -> None:
    assert scalar("SELECT alpha_string('en', 0, 1)") == "A"


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT alpha_string()",
        "SELECT alpha_string('en', 0, 1, 2)",
    ],
)
def test_invalid_arity(connection: sqlite3.Connection, sql: str) -> None:
    with pytest.raises(
        sqlite3.OperationalError,
        match=r"wrong number of arguments",
    ):
        connection.execute(sql).fetchall()

def test_registered_arities(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT narg
        FROM pragma_function_list
        WHERE name = 'alpha_string'
        ORDER BY narg
        """
    ).fetchall()

    assert rows == [(1,), (2,), (3,)]
