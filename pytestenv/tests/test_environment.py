import sqlite3


def test_sqlite_runtime_is_available(connection: sqlite3.Connection) -> None:
    version, source_id = connection.execute(
        "SELECT sqlite_version(), sqlite_source_id()"
    ).fetchone()

    assert version
    assert source_id


def test_alpha_string_is_available(connection: sqlite3.Connection) -> None:
    assert connection.execute("SELECT alpha_string('en', 0, 1)").fetchone() == ("A",)
