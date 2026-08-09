from __future__ import annotations

from itertools import product
from typing import Any

import pytest


LATIN = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CYRILLIC = "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"

MIXED_WIDTH = "Aé€😀Z"


def _case_variants(text: str) -> list[str]:
    """Return all ASCII upper/lower-case permutations of text."""
    choices = [
        (ch.lower(), ch.upper()) if ch.lower() != ch.upper() else (ch,)
        for ch in text
    ]
    return ["".join(chars) for chars in product(*choices)]


def _offset_cases() -> list[Any]:
    cases: list[Any] = []
    corpora = [
        ("empty", ""),
        ("ascii", "ABCxyz"),
        ("two-byte", "éЯ"),
        ("three-byte", "€漢"),
        ("four-byte", "😀𐍈"),
        ("mixed", MIXED_WIDTH),
        ("latin-alphabet", LATIN),
        ("cyrillic-alphabet", CYRILLIC),
    ]
    for label, text in corpora:
        for index in range(len(text) + 1):
            expected = len(text[:index].encode("utf-8"))
            cases.append(
                pytest.param(text, index, expected, id=f"{label}-index-{index}")
            )
    return cases


def _selected_alphabet_cases() -> list[Any]:
    cases: list[Any] = []
    for canonical, expected, label in [
        ("en", LATIN, "en"),
        ("English", LATIN, "English"),
        ("ru", CYRILLIC, "ru"),
        ("Russian", CYRILLIC, "Russian"),
    ]:
        for variant in _case_variants(canonical):
            cases.append(
                pytest.param(
                    variant,
                    expected,
                    id=f"{label}-case-{variant}",
                )
            )
    return cases


# ---------------------------------------------------------------------------
# Exported API / CFFI declaration contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "result_type", "argument_types"),
    [
        pytest.param(
            "ab_utf8_byte_count",
            "int",
            ("const char *",),
            id="utf8-byte-count",
        ),
        pytest.param(
            "ab_utf8_length",
            "int64_t",
            ("const char *",),
            id="utf8-length",
        ),
        pytest.param(
            "ab_utf8_byte_offset",
            "int",
            ("const char *", "int64_t"),
            id="utf8-byte-offset",
        ),
        pytest.param(
            "ab_alphabet_select",
            "const char *",
            ("const char *",),
            id="alphabet-select",
        ),
    ],
)
def test_exported_function_signatures(
    ffi: Any,
    lib: Any,
    name: str,
    result_type: str,
    argument_types: tuple[str, ...],
) -> None:
    function = getattr(lib, name)
    ctype = ffi.typeof(function)

    assert ctype.kind == "function"
    assert ctype.result == ffi.typeof(result_type)
    assert ctype.args == tuple(ffi.typeof(arg) for arg in argument_types)
    assert ctype.ellipsis is False


# ---------------------------------------------------------------------------
# ab_utf8_byte_count()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("\x01", 1, id="u0001-one-byte"),
        pytest.param("A", 1, id="ascii-letter-one-byte"),
        pytest.param("\x7f", 1, id="u007f-one-byte-upper-boundary"),
        pytest.param("\u0080", 2, id="u0080-two-byte-lower-boundary"),
        pytest.param("é", 2, id="u00e9-two-byte"),
        pytest.param("\u07ff", 2, id="u07ff-two-byte-upper-boundary"),
        pytest.param("\u0800", 3, id="u0800-three-byte-lower-boundary"),
        pytest.param("€", 3, id="u20ac-three-byte"),
        pytest.param("\ufffd", 3, id="ufffd-three-byte"),
        pytest.param("\U00010000", 4, id="u10000-four-byte-lower-boundary"),
        pytest.param("😀", 4, id="u1f600-four-byte"),
        pytest.param("\U0010ffff", 4, id="u10ffff-four-byte-upper-boundary"),
    ],
)
def test_utf8_byte_count_width_boundaries(
    ffi: Any, lib: Any, text: str, expected: int
) -> None:
    encoded = text.encode("utf-8")
    storage = ffi.new("char[]", encoded)

    assert len(encoded) == expected
    assert lib.ab_utf8_byte_count(storage) == expected


@pytest.mark.parametrize(
    "text",
    [
        pytest.param(LATIN, id="latin"),
        pytest.param(CYRILLIC, id="cyrillic"),
        pytest.param(MIXED_WIDTH, id="mixed-width"),
    ],
)
def test_utf8_byte_count_every_code_point(
    ffi: Any, lib: Any, text: str
) -> None:
    for index, character in enumerate(text):
        encoded = text[index:].encode("utf-8")
        storage = ffi.new("char[]", encoded)
        assert lib.ab_utf8_byte_count(storage) == len(character.encode("utf-8"))


def test_utf8_byte_count_nul_byte_is_one_byte(ffi: Any, lib: Any) -> None:
    storage = ffi.new("char[]", b"")
    assert lib.ab_utf8_byte_count(storage) == 1


# ---------------------------------------------------------------------------
# ab_utf8_length()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", 0, id="empty"),
        pytest.param("A", 1, id="single-ascii"),
        pytest.param("é", 1, id="single-two-byte"),
        pytest.param("€", 1, id="single-three-byte"),
        pytest.param("😀", 1, id="single-four-byte"),
        pytest.param("ASCII", 5, id="ascii"),
        pytest.param(MIXED_WIDTH, 5, id="mixed-width"),
        pytest.param(LATIN, 52, id="latin-alphabet"),
        pytest.param(CYRILLIC, 66, id="cyrillic-alphabet"),
        pytest.param("AЯ€😀" * 64, 256, id="repeated-mixed-width"),
    ],
)
def test_utf8_length_counts_code_points(
    ffi: Any, lib: Any, text: str, expected: int
) -> None:
    storage = ffi.new("char[]", text.encode("utf-8"))
    assert lib.ab_utf8_length(storage) == expected
    assert expected == len(text)


def test_utf8_length_stops_at_first_nul(ffi: Any, lib: Any) -> None:
    storage = ffi.new("char[]", b"A\xc3\xa9\x00ignored")
    assert lib.ab_utf8_length(storage) == 2


@pytest.mark.parametrize(
    ("language", "expected_length"),
    [
        pytest.param(b"en", 52, id="selected-latin"),
        pytest.param(b"ru", 66, id="selected-cyrillic"),
    ],
)
def test_utf8_length_accepts_borrowed_alphabet_storage(
    ffi: Any, lib: Any, language: bytes, expected_length: int
) -> None:
    alphabet = lib.ab_alphabet_select(language)
    assert alphabet != ffi.NULL
    assert lib.ab_utf8_length(alphabet) == expected_length


# ---------------------------------------------------------------------------
# ab_utf8_byte_offset()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "index", "expected"),
    _offset_cases(),
)
def test_utf8_byte_offset_matches_encoded_prefix_length(
    ffi: Any,
    lib: Any,
    text: str,
    index: int,
    expected: int,
) -> None:
    storage = ffi.new("char[]", text.encode("utf-8"))
    assert lib.ab_utf8_byte_offset(storage, index) == expected


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("", id="empty"),
        pytest.param("ASCII", id="ascii"),
        pytest.param(MIXED_WIDTH, id="mixed-width"),
        pytest.param(LATIN, id="latin"),
        pytest.param(CYRILLIC, id="cyrillic"),
    ],
)
def test_utf8_byte_offset_end_is_encoded_byte_length(
    ffi: Any, lib: Any, text: str
) -> None:
    storage = ffi.new("char[]", text.encode("utf-8"))
    assert lib.ab_utf8_byte_offset(storage, len(text)) == len(text.encode("utf-8"))


@pytest.mark.parametrize(
    ("text", "index"),
    [
        pytest.param(MIXED_WIDTH, 0, id="mixed-start"),
        pytest.param(MIXED_WIDTH, 1, id="mixed-after-ascii"),
        pytest.param(MIXED_WIDTH, 2, id="mixed-after-two-byte"),
        pytest.param(MIXED_WIDTH, 3, id="mixed-after-three-byte"),
        pytest.param(MIXED_WIDTH, 4, id="mixed-after-four-byte"),
        pytest.param(MIXED_WIDTH, 5, id="mixed-end"),
        pytest.param(CYRILLIC, 1, id="cyrillic-first"),
        pytest.param(CYRILLIC, 33, id="cyrillic-case-boundary"),
        pytest.param(CYRILLIC, 66, id="cyrillic-end"),
    ],
)
def test_utf8_byte_offset_points_to_expected_suffix(
    ffi: Any, lib: Any, text: str, index: int
) -> None:
    storage = ffi.new("char[]", text.encode("utf-8"))
    offset = lib.ab_utf8_byte_offset(storage, index)

    assert ffi.string(storage + offset) == text[index:].encode("utf-8")


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        pytest.param(b"en", LATIN, id="latin"),
        pytest.param(b"ru", CYRILLIC, id="cyrillic"),
    ],
)
def test_utf8_byte_offset_operates_on_borrowed_selected_alphabet(
    ffi: Any, lib: Any, language: bytes, expected: str
) -> None:
    alphabet = lib.ab_alphabet_select(language)
    assert alphabet != ffi.NULL

    for index in range(len(expected) + 1):
        expected_offset = len(expected[:index].encode("utf-8"))
        assert lib.ab_utf8_byte_offset(alphabet, index) == expected_offset


# ---------------------------------------------------------------------------
# ab_alphabet_select()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("language", "expected"),
    _selected_alphabet_cases(),
)
def test_alphabet_select_all_ascii_case_permutations(
    ffi: Any, lib: Any, language: str, expected: str
) -> None:
    result = lib.ab_alphabet_select(language.encode("ascii"))

    assert result != ffi.NULL
    assert ffi.string(result) == expected.encode("utf-8")


@pytest.mark.parametrize(
    "language",
    [
        pytest.param("", id="empty"),
        pytest.param("e", id="en-prefix"),
        pytest.param("eng", id="en-near-abbreviation"),
        pytest.param("Englishx", id="english-suffix"),
        pytest.param(" English", id="english-leading-space"),
        pytest.param("English ", id="english-trailing-space"),
        pytest.param("en-US", id="locale-form"),
        pytest.param("r", id="ru-prefix"),
        pytest.param("rus", id="ru-near-abbreviation"),
        pytest.param("Russianx", id="russian-suffix"),
        pytest.param(" Russian", id="russian-leading-space"),
        pytest.param("Russian ", id="russian-trailing-space"),
        pytest.param("de", id="unsupported-ascii-language"),
        pytest.param("русский", id="unsupported-non-ascii-language"),
        pytest.param("английский", id="unsupported-cyrillic-english-name"),
        pytest.param("é", id="unsupported-utf8-name"),
    ],
)
def test_alphabet_select_unsupported_names_return_null(
    ffi: Any, lib: Any, language: str
) -> None:
    result = lib.ab_alphabet_select(language.encode("utf-8"))
    assert result == ffi.NULL


@pytest.mark.parametrize(
    ("storage_bytes", "expected"),
    [
        pytest.param(b"en\x00ignored", LATIN, id="en-terminated-before-suffix"),
        pytest.param(
            b"English\x00ignored",
            LATIN,
            id="english-terminated-before-suffix",
        ),
        pytest.param(b"ru\x00ignored", CYRILLIC, id="ru-terminated-before-suffix"),
        pytest.param(
            b"Russian\x00ignored",
            CYRILLIC,
            id="russian-terminated-before-suffix",
        ),
    ],
)
def test_alphabet_select_uses_c_nul_terminated_string_semantics(
    ffi: Any,
    lib: Any,
    storage_bytes: bytes,
    expected: str,
) -> None:
    storage = ffi.new("char[]", storage_bytes)
    result = lib.ab_alphabet_select(storage)

    assert result != ffi.NULL
    assert ffi.string(result) == expected.encode("utf-8")


def test_alphabet_select_aliases_return_same_borrowed_static_pointer(
    ffi: Any, lib: Any
) -> None:
    latin_en = lib.ab_alphabet_select(b"en")
    latin_english = lib.ab_alphabet_select(b"English")
    russian_ru = lib.ab_alphabet_select(b"ru")
    russian_russian = lib.ab_alphabet_select(b"Russian")

    assert latin_en != ffi.NULL
    assert russian_ru != ffi.NULL

    assert latin_en == latin_english
    assert russian_ru == russian_russian
    assert latin_en != russian_ru


def test_alphabet_select_pointer_is_stable_across_calls(ffi: Any, lib: Any) -> None:
    first_latin = lib.ab_alphabet_select(b"en")
    first_russian = lib.ab_alphabet_select(b"ru")

    for _ in range(10):
        assert lib.ab_alphabet_select(b"English") == first_latin
        assert lib.ab_alphabet_select(b"Russian") == first_russian


# ---------------------------------------------------------------------------
# Cross-API invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("language", "expected"),
    [
        pytest.param(b"en", LATIN, id="latin"),
        pytest.param(b"English", LATIN, id="latin-long-name"),
        pytest.param(b"ru", CYRILLIC, id="cyrillic"),
        pytest.param(b"Russian", CYRILLIC, id="cyrillic-long-name"),
    ],
)
def test_selected_alphabet_cross_api_contract(
    ffi: Any, lib: Any, language: bytes, expected: str
) -> None:
    alphabet = lib.ab_alphabet_select(language)
    assert alphabet != ffi.NULL
    assert ffi.string(alphabet) == expected.encode("utf-8")

    count = lib.ab_utf8_length(alphabet)
    assert count == len(expected)

    assert lib.ab_utf8_byte_offset(alphabet, 0) == 0
    assert lib.ab_utf8_byte_offset(alphabet, count) == len(expected.encode("utf-8"))

    for index, character in enumerate(expected):
        offset = lib.ab_utf8_byte_offset(alphabet, index)
        assert lib.ab_utf8_byte_count(alphabet + offset) == len(
            character.encode("utf-8")
        )


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("ASCII", id="ascii"),
        pytest.param("éЯ", id="two-byte"),
        pytest.param("€漢", id="three-byte"),
        pytest.param("😀𐍈", id="four-byte"),
        pytest.param(MIXED_WIDTH, id="mixed-width"),
        pytest.param(LATIN, id="latin"),
        pytest.param(CYRILLIC, id="cyrillic"),
    ],
)
def test_utf8_helpers_are_mutually_consistent(
    ffi: Any, lib: Any, text: str
) -> None:
    encoded = text.encode("utf-8")
    storage = ffi.new("char[]", encoded)

    count = lib.ab_utf8_length(storage)
    assert count == len(text)

    offset = 0
    for index in range(count):
        assert lib.ab_utf8_byte_offset(storage, index) == offset
        width = lib.ab_utf8_byte_count(storage + offset)
        assert width == len(text[index].encode("utf-8"))
        offset += width

    assert offset == len(encoded)
    assert lib.ab_utf8_byte_offset(storage, count) == offset
