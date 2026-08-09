from __future__ import annotations

import sqlite3
import sys
from collections.abc import Callable, Iterator
from importlib import import_module
from pathlib import Path
from types import ModuleType
from typing import Any

from tests.cffi_types import CffiValue

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = REPO_ROOT / "src"
MODULE_ROOT = SOURCE_ROOT / "alphabet"

sys.path[:0] = [str(SOURCE_ROOT), str(MODULE_ROOT)]


@pytest.fixture(scope="session")
def wrapper_module() -> ModuleType:
    """Import the freshly built CFFI wrapper for the alphabet helpers."""
    return import_module("_cffi_wrapper")


@pytest.fixture
def ffi(wrapper_module: ModuleType) -> Any:
    return wrapper_module.ffi


@pytest.fixture
def lib(wrapper_module: ModuleType) -> Any:
    return wrapper_module.lib


@pytest.fixture
def db() -> Iterator[sqlite3.Connection]:
    """Provide an isolated SQLite connection using the test SQLite build."""
    connection = sqlite3.connect(":memory:")
    try:
        yield connection
    finally:
        connection.close()


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


########## CTD ##########

@pytest.fixture
def reset_globals(lib: CffiValue) -> Iterator[None]:
    """Expose mutable-global isolation explicitly to tests that need it."""
    lib.ctd_globals_reset()
    yield
    lib.ctd_globals_reset()


@pytest.fixture
def counter_handle(ffi: CffiValue, lib: CffiValue) -> Iterator[object]:
    """Provide one owned opaque counter and release it after the test."""
    handle = lib.ctd_counter_create(10)
    assert handle != ffi.NULL
    yield handle
    lib.ctd_free(handle)


@pytest.fixture
def allocated_sequence(ffi: CffiValue, lib: CffiValue) -> Iterator[tuple[object, int]]:
    """Provide a CTD-owned array to tests that do not exercise deallocation."""
    count = 4
    values = lib.ctd_alloc_sequence_i32(-2, count)
    assert values != ffi.NULL
    yield values, count
    lib.ctd_free(values)
