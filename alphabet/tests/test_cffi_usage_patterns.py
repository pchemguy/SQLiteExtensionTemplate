# ruff: noqa: ANN001, ANN201
from __future__ import annotations

import pytest

from tests.cffi_types import CffiValue


def test_callback_with_python_user_data(ffi: CffiValue, lib: CffiValue) -> None:
    """Pass a Python callback and Python-owned context through ``void *``."""
    context = {"weight": 10}
    user_data = ffi.new_handle(context)

    @ffi.callback("ctd_binary_callback")
    def weighted_add(left: int, right: int, opaque: CffiValue) -> int:
        callback_context = ffi.from_handle(opaque)
        return int(left + right * callback_context["weight"])

    result = ffi.new("int *", -999)

    status = lib.ctd_apply_callback(
        2,
        3,
        weighted_add,
        user_data,
        result,
    )

    assert status == lib.CTD_OK
    assert result[0] == 32


@pytest.mark.parametrize(
    ("operation_kind", "expected"),
    [
        pytest.param("CTD_BINARY_OPERATION_ADD", 13, id="add"),
        pytest.param("CTD_BINARY_OPERATION_MULTIPLY", 42, id="multiply"),
    ],
)
def test_returned_function_pointer_is_callable(
    ffi: CffiValue,
    lib: CffiValue,
    operation_kind: str,
    expected: int,
) -> None:
    """Call a borrowed function pointer returned by the C library."""
    operation = lib.ctd_get_binary_operation(getattr(lib, operation_kind))

    assert operation != ffi.NULL
    assert operation(6, 7) == expected


def test_returned_function_pointer_can_be_null(ffi: CffiValue, lib: CffiValue) -> None:
    operation = lib.ctd_get_binary_operation(999)

    assert operation == ffi.NULL


def test_descriptor_borrows_caller_owned_array(ffi: CffiValue, lib: CffiValue) -> None:
    """Keep owning cdata alive while accessing an aliased structure field."""
    values = ffi.new("int32_t[]", [4, 8, 15, 16, 23, 42])
    descriptor = ffi.new("ctd_descriptor *")

    status = lib.ctd_describe_i32(values, 6, descriptor)

    assert status == lib.CTD_OK
    assert ffi.string(descriptor.message) == b"integer sequence"
    assert descriptor.count == 6
    assert descriptor.values == ffi.cast("int32_t *", values)
    assert list(ffi.unpack(descriptor.values, descriptor.count)) == [
        4,
        8,
        15,
        16,
        23,
        42,
    ]


def test_structure_with_fixed_size_array_fields(ffi: CffiValue, lib: CffiValue) -> None:
    """Access fixed-size character and numeric arrays embedded in a structure."""
    record = ffi.new("ctd_record *")

    status = lib.ctd_record_initialize(record, 77, b"sample")

    assert status == lib.CTD_OK
    assert record.id == 77
    assert ffi.string(record.name) == b"sample"
    assert list(record.values) == pytest.approx([1.0, 2.0, 3.0])


def test_nested_structure_initialization_from_mapping(
    ffi: CffiValue,
    lib: CffiValue,
) -> None:
    """Initialize nested C structures directly from Python mappings."""
    config = ffi.new(
        "ctd_config *",
        {
            "range": {
                "minimum": -10.0,
                "maximum": 10.0,
            },
            "policy": lib.CTD_RANGE_CLAMP,
        },
    )
    result = ffi.new("double *", -999.0)

    status = lib.ctd_range_apply(config, 25.0, result)

    assert status == lib.CTD_OK
    assert config.range.minimum == pytest.approx(-10.0)
    assert config.range.maximum == pytest.approx(10.0)
    assert config.policy == lib.CTD_RANGE_CLAMP
    assert result[0] == pytest.approx(10.0)


def test_borrowed_const_nested_structure(ffi: CffiValue, lib: CffiValue) -> None:
    """Read a borrowed pointer to a library-owned nested structure."""
    config = lib.ctd_default_config()

    assert config != ffi.NULL
    assert config.range.minimum == pytest.approx(0.0)
    assert config.range.maximum == pytest.approx(100.0)
    assert config.policy == lib.CTD_RANGE_CLAMP

    result = ffi.new("double *")
    assert lib.ctd_range_apply(config, 125.0, result) == lib.CTD_OK
    assert result[0] == pytest.approx(100.0)


def test_python_buffer_is_borrowed_without_ffi_allocation(
    ffi: CffiValue,
    lib: CffiValue,
) -> None:
    """Expose mutable Python buffer storage directly to C with ``from_buffer``."""
    data = bytearray(b"abcd")
    buffer = ffi.from_buffer("uint8_t[]", data)

    status = lib.ctd_xor_bytes(buffer, len(data), 0x20)

    assert status == lib.CTD_OK
    assert data == bytearray(b"ABCD")
