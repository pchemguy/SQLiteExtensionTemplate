from collections.abc import Callable, Iterator
import sqlite3
from typing import Any

import pytest


@pytest.fixture
def connection() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(":memory:")
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def scalar(
    connection: sqlite3.Connection,
) -> Callable[[str, tuple[Any, ...]], Any]:
    def execute(
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> Any:
        row = connection.execute(sql, parameters).fetchone()
        assert row is not None
        return row[0]

    return execute


@pytest.fixture
def assert_sql_error(
    connection: sqlite3.Connection,
) -> Callable[[str, str, tuple[Any, ...]], None]:
    def execute(
        expected: str,
        sql: str,
        parameters: tuple[Any, ...] = (),
    ) -> None:
        with pytest.raises(sqlite3.OperationalError) as error:
            connection.execute(sql, parameters).fetchall()

        assert str(error.value) == expected

    return execute
