import pytest


@pytest.mark.parametrize(
    ("sql", "parameters"),
    [
        ("SELECT alpha_string(?)", (None,)),
        ("SELECT alpha_string(?, ?)", ("en", None)),
        ("SELECT alpha_string(?, ?, ?)", ("en", 0, None)),
        ("SELECT alpha_string(?, ?, ?)", (None, 0, 1)),
        ("SELECT alpha_string(?, ?, ?)", ("en", None, 1)),
    ],
)
def test_null_propagation(scalar, sql: str, parameters: tuple) -> None:
    assert scalar(sql, parameters) is None
