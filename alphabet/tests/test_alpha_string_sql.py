from __future__ import annotations

import sqlite3

import pytest

LATIN = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CYRILLIC = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"
INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


def scalar(db: sqlite3.Connection, sql: str, parameters: tuple[object, ...] = ()) -> object:
    row = db.execute(sql, parameters).fetchone()
    assert row is not None
    return row[0]


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        pytest.param("en", LATIN, id="en"),
        pytest.param("English", LATIN, id="English"),
        pytest.param("EN", LATIN, id="EN-case-insensitive"),
        pytest.param("eNgLiSh", LATIN, id="English-mixed-case"),
        pytest.param("ru", CYRILLIC, id="ru"),
        pytest.param("Russian", CYRILLIC, id="Russian"),
        pytest.param("RU", CYRILLIC, id="RU-case-insensitive"),
        pytest.param("rUsSiAn", CYRILLIC, id="Russian-mixed-case"),
    ],
)
def test_alpha_string_one_argument_aliases(
    db: sqlite3.Connection, language: str, expected: str
) -> None:
    assert scalar(db, "SELECT alpha_string(?)", (language,)) == expected


def test_alpha_string_documented_examples(db: sqlite3.Connection) -> None:
    assert scalar(db, "SELECT alpha_string('en')") == LATIN
    assert scalar(db, "SELECT alpha_string('English', 3)") == LATIN[3:]
    assert scalar(db, "SELECT alpha_string('ru', -5)") == CYRILLIC[-5:]
    assert scalar(db, "SELECT alpha_string('Russian', 2, 4)") == CYRILLIC[2:6]


@pytest.mark.parametrize(
    ("language", "alphabet", "start"),
    [
        pytest.param("en", LATIN, 0, id="latin-start-zero"),
        pytest.param("en", LATIN, 1, id="latin-start-one"),
        pytest.param("en", LATIN, 51, id="latin-last-code-point"),
        pytest.param("en", LATIN, 52, id="latin-one-past-last"),
        pytest.param("en", LATIN, -1, id="latin-negative-one"),
        pytest.param("en", LATIN, -52, id="latin-negative-full-length"),
        pytest.param("ru", CYRILLIC, 0, id="cyrillic-start-zero"),
        pytest.param("ru", CYRILLIC, 1, id="cyrillic-start-one"),
        pytest.param("ru", CYRILLIC, 65, id="cyrillic-last-code-point"),
        pytest.param("ru", CYRILLIC, 66, id="cyrillic-one-past-last"),
        pytest.param("ru", CYRILLIC, -1, id="cyrillic-negative-one"),
        pytest.param("ru", CYRILLIC, -66, id="cyrillic-negative-full-length"),
    ],
)
def test_alpha_string_start_boundaries(
    db: sqlite3.Connection, language: str, alphabet: str, start: int
) -> None:
    expected_start = start if start >= 0 else len(alphabet) + start
    assert scalar(db, "SELECT alpha_string(?, ?)", (language, start)) == alphabet[
        expected_start:
    ]


@pytest.mark.parametrize(
    ("language", "start"),
    [
        pytest.param("en", -53, id="latin-below-negative-bound"),
        pytest.param("en", 53, id="latin-above-positive-bound"),
        pytest.param("ru", -67, id="cyrillic-below-negative-bound"),
        pytest.param("ru", 67, id="cyrillic-above-positive-bound"),
        pytest.param("en", INT64_MIN, id="int64-min"),
        pytest.param("en", INT64_MAX, id="int64-max"),
    ],
)
def test_alpha_string_start_out_of_range(
    db: sqlite3.Connection, language: str, start: int
) -> None:
    with pytest.raises(sqlite3.OperationalError, match="start index is out of range"):
        db.execute("SELECT alpha_string(?, ?)", (language, start)).fetchone()


@pytest.mark.parametrize(
    ("language", "alphabet", "start", "length"),
    [
        pytest.param("en", LATIN, 0, 0, id="latin-zero-length"),
        pytest.param("en", LATIN, 0, 1, id="latin-one-code-point"),
        pytest.param("en", LATIN, 3, 4, id="latin-interior-slice"),
        pytest.param("en", LATIN, -5, 4, id="latin-negative-start"),
        pytest.param("en", LATIN, 50, 2, id="latin-exact-remainder"),
        pytest.param("en", LATIN, 50, 99, id="latin-truncate-to-remainder"),
        pytest.param("en", LATIN, 52, 1, id="latin-end-start"),
        pytest.param("en", LATIN, 0, INT64_MAX, id="latin-int64-max-length"),
        pytest.param("ru", CYRILLIC, 2, 4, id="cyrillic-interior-slice"),
        pytest.param("ru", CYRILLIC, -5, 4, id="cyrillic-negative-start"),
        pytest.param("ru", CYRILLIC, 64, 99, id="cyrillic-truncate-to-remainder"),
        pytest.param("ru", CYRILLIC, 66, 0, id="cyrillic-end-zero-length"),
    ],
)
def test_alpha_string_length_contract(
    db: sqlite3.Connection,
    language: str,
    alphabet: str,
    start: int,
    length: int,
) -> None:
    expected_start = start if start >= 0 else len(alphabet) + start
    expected = alphabet[expected_start : expected_start + length]
    assert scalar(db, "SELECT alpha_string(?, ?, ?)", (language, start, length)) == expected


@pytest.mark.parametrize(
    "length",
    [
        pytest.param(-1, id="negative-one"),
        pytest.param(INT64_MIN, id="int64-min"),
    ],
)
def test_alpha_string_negative_length_is_rejected(
    db: sqlite3.Connection, length: int
) -> None:
    with pytest.raises(sqlite3.OperationalError, match="length must not be negative"):
        db.execute("SELECT alpha_string('en', 0, ?)", (length,)).fetchone()


@pytest.mark.parametrize(
    ("sql", "parameters"),
    [
        pytest.param("SELECT alpha_string(?)", (None,), id="language-null"),
        pytest.param("SELECT alpha_string('en', ?)", (None,), id="start-null"),
        pytest.param(
            "SELECT alpha_string('en', 0, ?)", (None,), id="length-null"
        ),
    ],
)
def test_alpha_string_null_propagates(
    db: sqlite3.Connection, sql: str, parameters: tuple[object, ...]
) -> None:
    assert scalar(db, sql, parameters) is None


@pytest.mark.parametrize(
    "language",
    [
        pytest.param("", id="empty"),
        pytest.param("de", id="unsupported"),
        pytest.param("Englishx", id="near-match"),
        pytest.param("русский", id="non-ascii-name"),
    ],
)
def test_alpha_string_unsupported_language_is_rejected(
    db: sqlite3.Connection, language: str
) -> None:
    with pytest.raises(
        sqlite3.OperationalError,
        match="language must be en, English, ru, or Russian",
    ):
        db.execute("SELECT alpha_string(?)", (language,)).fetchone()


@pytest.mark.parametrize(
    "value",
    [
        pytest.param(1, id="integer"),
        pytest.param(1.5, id="real"),
        pytest.param(b"en", id="blob"),
    ],
)
def test_alpha_string_language_requires_sql_text(
    db: sqlite3.Connection, value: object
) -> None:
    with pytest.raises(sqlite3.OperationalError, match="language must be text"):
        db.execute("SELECT alpha_string(?)", (value,)).fetchone()


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("1", id="text"),
        pytest.param(1.0, id="real"),
        pytest.param(b"1", id="blob"),
    ],
)
def test_alpha_string_start_requires_sql_integer(
    db: sqlite3.Connection, value: object
) -> None:
    with pytest.raises(sqlite3.OperationalError, match="start must be an integer"):
        db.execute("SELECT alpha_string('en', ?)", (value,)).fetchone()


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("1", id="text"),
        pytest.param(1.0, id="real"),
        pytest.param(b"1", id="blob"),
    ],
)
def test_alpha_string_length_requires_sql_integer(
    db: sqlite3.Connection, value: object
) -> None:
    with pytest.raises(sqlite3.OperationalError, match="length must be an integer"):
        db.execute("SELECT alpha_string('en', 0, ?)", (value,)).fetchone()


@pytest.mark.parametrize(
    "sql",
    [
        pytest.param("SELECT alpha_string()", id="zero-arguments"),
        pytest.param("SELECT alpha_string('en', 0, 1, 2)", id="four-arguments"),
    ],
)
def test_alpha_string_rejects_unsupported_arities(
    db: sqlite3.Connection, sql: str
) -> None:
    with pytest.raises(sqlite3.OperationalError, match="wrong number of arguments"):
        db.execute(sql).fetchone()
