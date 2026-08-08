import pytest

from .support import (
    CYRILLIC,
    LATIN,
    START_RANGE_ERROR,
    START_TYPE_ERROR,
)


@pytest.mark.parametrize(
    ("language", "alphabet"),
    [
        ("en", LATIN),
        ("ru", CYRILLIC),
    ],
)
@pytest.mark.parametrize(
    "start",
    [
        0,
        1,
        2,
        -1,
        -2,
    ],
)
def test_valid_start(scalar, language: str, alphabet: str, start: int) -> None:
    assert scalar("SELECT alpha_string(?, ?)", (language, start)) == alphabet[start:]


@pytest.mark.parametrize(
    ("language", "alphabet"),
    [
        ("en", LATIN),
        ("ru", CYRILLIC),
    ],
)
def test_start_at_end_returns_empty(scalar, language: str, alphabet: str) -> None:
    assert scalar("SELECT alpha_string(?, ?)", (language, len(alphabet))) == ""


@pytest.mark.parametrize(
    ("language", "alphabet"),
    [
        ("en", LATIN),
        ("ru", CYRILLIC),
    ],
)
def test_negative_full_length_returns_full_alphabet(
    scalar,
    language: str,
    alphabet: str,
) -> None:
    assert scalar("SELECT alpha_string(?, ?)", (language, -len(alphabet))) == alphabet


@pytest.mark.parametrize(
    ("language", "start"),
    [
        ("en", len(LATIN) + 1),
        ("en", -len(LATIN) - 1),
        ("ru", len(CYRILLIC) + 1),
        ("ru", -len(CYRILLIC) - 1),
        ("en", 2**63 - 1),
        ("en", -(2**63)),
    ],
)
def test_start_out_of_range(assert_sql_error, language: str, start: int) -> None:
    assert_sql_error(START_RANGE_ERROR, "SELECT alpha_string(?, ?)", (language, start))


@pytest.mark.parametrize(
    "start",
    [
        1.0,
        "1",
        b"1",
    ],
)
def test_start_must_be_integer(assert_sql_error, start) -> None:
    assert_sql_error(START_TYPE_ERROR, "SELECT alpha_string('en', ?)", (start,))
