# ruff: noqa: ANN001, ANN201
from __future__ import annotations

import pytest

from tests.cffi_types import CffiValue


def test_enum_values(lib: CffiValue) -> None:
    expected_values = {
        "CTD_OK": 0,
        "CTD_ERROR_NULL": 1,
        "CTD_ERROR_RANGE": 2,
        "CTD_ERROR_CAPACITY": 3,
        "CTD_ERROR_ALLOCATION": 4,
        "CTD_ERROR_DIVIDE_BY_ZERO": 5,
    }

    assert {name: getattr(lib, name) for name in expected_values} == expected_values


@pytest.mark.parametrize(
    ("constant", "expected"),
    [
        pytest.param("CTD_OK", b"CTD_OK", id="ok"),
        pytest.param("CTD_ERROR_NULL", b"CTD_ERROR_NULL", id="null"),
        pytest.param("CTD_ERROR_RANGE", b"CTD_ERROR_RANGE", id="range"),
        pytest.param("CTD_ERROR_CAPACITY", b"CTD_ERROR_CAPACITY", id="capacity"),
        pytest.param("CTD_ERROR_ALLOCATION", b"CTD_ERROR_ALLOCATION", id="allocation"),
        pytest.param(
            "CTD_ERROR_DIVIDE_BY_ZERO",
            b"CTD_ERROR_DIVIDE_BY_ZERO",
            id="divide-by-zero",
        ),
        pytest.param(None, b"CTD_ERROR_UNKNOWN", id="unknown"),
    ],
)
def test_status_names(
    ffi: CffiValue, lib: CffiValue, constant: str | None, expected: bytes
) -> None:
    status = 999 if constant is None else getattr(lib, constant)
    assert ffi.string(lib.ctd_status_name(status)) == expected


@pytest.mark.parametrize(
    ("operation", "arguments", "expected"),
    [
        pytest.param("ctd_add", (17, 25), 42, id="add-positive"),
        pytest.param("ctd_add", (-17, -25), -42, id="add-negative"),
        pytest.param("ctd_add", (0, 0), 0, id="add-zero"),
        pytest.param("ctd_add", (2**31 - 2, 1), 2**31 - 1, id="add-int-max-adjacent"),
        pytest.param(
            "ctd_add", (-(2**31) + 1, -1), -(2**31), id="add-int-min-adjacent"
        ),
        pytest.param("ctd_negate_i32", (-123,), 123, id="negate-negative"),
        pytest.param("ctd_negate_i32", (0,), 0, id="negate-zero"),
        pytest.param("ctd_negate_i32", (-(2**31),), 2**31 - 1, id="negate-int32-min"),
        pytest.param("ctd_add_u64", (2**64 - 2, 1), 2**64 - 1, id="u64-max-adjacent"),
        pytest.param("ctd_add_u64", (2**64 - 1, 1), 0, id="u64-wrap"),
    ],
)
def test_exact_scalar_operations(
    lib: CffiValue, operation: str, arguments: tuple[int, ...], expected: int
) -> None:
    assert getattr(lib, operation)(*arguments) == expected


@pytest.mark.parametrize(
    ("x", "y", "expected"),
    [(3.0, 4.0, 25.0), (-3.0, 4.0, 25.0), (0.0, 0.0, 0.0)],
    ids=["positive", "negative", "zero"],
)
def test_hypot_squared(lib: CffiValue, x: float, y: float, expected: float) -> None:
    assert lib.ctd_hypot_squared(x, y) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected_status", "expected", "output_changes"),
    [
        pytest.param(22.0, 7.0, "CTD_OK", 22.0 / 7.0, True, id="fractional"),
        pytest.param(-9.0, 3.0, "CTD_OK", -3.0, True, id="negative"),
    ],
)
def test_divide_success_changes_output(
    ffi: CffiValue,
    lib: CffiValue,
    numerator: float,
    denominator: float,
    expected_status: str,
    expected: float,
    output_changes: bool,
) -> None:
    sentinel = 987.25
    result = ffi.new("double *", sentinel)
    assert lib.ctd_divide(numerator, denominator, result) == getattr(
        lib, expected_status
    )
    assert result[0] == pytest.approx(expected)
    assert (result[0] != sentinel) is output_changes


@pytest.mark.parametrize(
    ("numerator", "denominator", "expected_status", "expected", "output_changes"),
    [
        pytest.param(
            1.0,
            0.0,
            "CTD_ERROR_DIVIDE_BY_ZERO",
            987.25,
            False,
            id="divide-by-zero",
        ),
    ],
)
def test_divide_failure_preserves_output(
    ffi: CffiValue,
    lib: CffiValue,
    numerator: float,
    denominator: float,
    expected_status: str,
    expected: float,
    output_changes: bool,
) -> None:
    sentinel = 987.25
    result = ffi.new("double *", sentinel)
    status = lib.ctd_divide(numerator, denominator, result)
    assert status == getattr(lib, expected_status)
    assert result[0] == pytest.approx(expected)
    assert (result[0] != sentinel) is output_changes


@pytest.mark.parametrize(
    "mode",
    [
        pytest.param("direct-assignment", id="direct-assignment"),
        pytest.param("library-mutation", id="library-mutation"),
    ],
)
def test_mutable_global_counter_is_isolated(
    lib: CffiValue, reset_globals: CffiValue, mode: str
) -> None:
    assert lib.ctd_global_counter == 0
    if mode == "direct-assignment":
        lib.ctd_global_counter = 41
        assert lib.ctd_global_counter == 41
    else:
        assert lib.ctd_global_counter_increment() == 1
        assert lib.ctd_global_counter == 1


def test_constants(ffi: CffiValue, lib: CffiValue) -> None:
    assert lib.ctd_max_supported_point_count == 1024
    assert lib.ctd_numeric_epsilon == pytest.approx(1.0e-12)
    assert ffi.string(lib.ctd_library_name) == b"CTD"
    assert lib.ctd_origin_point.x == pytest.approx(0.0)
    assert lib.ctd_origin_point.y == pytest.approx(0.0)


def test_globals_reset_restores_all_defaults(lib: CffiValue) -> None:
    lib.ctd_global_counter = 41
    lib.ctd_global_last_status = lib.CTD_ERROR_RANGE
    lib.ctd_global_scale = 2.5

    lib.ctd_globals_reset()

    assert lib.ctd_global_counter == 0
    assert lib.ctd_global_last_status == lib.CTD_OK
    assert lib.ctd_global_scale == pytest.approx(1.0)
