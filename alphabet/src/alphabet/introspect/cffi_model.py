from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import _cffi_backend

__all__ = (
    "CFFITarget",
    "CFFICTypes",
)


@dataclass(frozen=True)
class CFFITarget:
    """A CFFI API out-of-line target.

    Attributes:
        ffi: The ``FFI`` object exported by the out-of-line CFFI extension module.
        lib: The library interface object exported by the out-of-line CFFI extension
            module, providing access to declared C functions, variables, and constants.
    """

    ffi: _cffi_backend.FFI
    lib: _cffi_backend.Lib

    @classmethod
    def bind(
        cls,
        ffi: _cffi_backend.FFI,
        lib: _cffi_backend.Lib,
    ) -> CFFITarget:
        """Create and install the active CFFI target."""
        global cffi_target

        if cffi_target is None:
            cffi_target = cls(ffi=ffi, lib=lib)
        elif cffi_target.ffi is not ffi or cffi_target.lib is not lib:
            raise RuntimeError("A different CFFI target is already bound")

        return cffi_target


cffi_target: CFFITarget | None = None


_ffi: _cffi_backend.FFI | None = None
_lib: _cffi_backend.Lib | None = None


def cffi_init(ffi: _cffi_backend.FFI, lib: _cffi_backend.Lib) -> None:
    """A CFFI API out-of-line target.

    Arguments:
        ffi: The ``FFI`` object exported by the out-of-line CFFI extension module.
        lib: The library interface object exported by the out-of-line CFFI extension
            module, providing access to declared C functions, variables, and constants.
    """
    global _ffi
    global _lib

    if _ffi is None:
        _ffi, _lib = ffi, lib
    elif _ffi is not ffi or _lib is not lib:
        raise RuntimeError("A different CFFI target is already bound")


CFFI_NONE = "CFFI target is not initialized; call cffi_init(ffi, lib) first."


class CTypeKinds(StrEnum):
    PRIMITIVE = "primitive"
    POINTER = "pointer"
    ARRAY = "array"
    FUNCTION = "function"
    STRUCT = "struct"
    UNION = "union"
    ENUM = "enum"


class CFieldAttributes(StrEnum):
    BITSHIFT = "bitshift"
    BITSIZE = "bitsize"
    FLAGS = "flags"
    OFFSET = "offset"
    TYPE = "type"


_fattr_names: list[str] = [member.value for member in CFieldAttributes]


class CTypeAttributes(StrEnum):
    NAME = "name"
    CATEGORY = "category"
    CNAME = "cname"
    KIND = "kind"
    ITEM = "item"
    LENGTH = "length"
    FIELDS = "fields"
    ARGS = "args"
    RESULT = "result"
    ELLIPSIS = "ellipsis"
    ABI = "abi"
    ELEMENTS = "elements"
    RELEMENTS = "relements"


_attr_names: list[str] = [member.value for member in CTypeAttributes]


def _ctype2dict(
    ctype: _cffi_backend.CType,
    seen: set[_cffi_backend.CType] | None = None,
) -> dict[str, Any]:
    if _ffi is None:
        raise RuntimeError(CFFI_NONE)

    if seen is None:
        seen = set()

    if ctype in seen:
        return {
            "cname": ctype.cname,
            "kind": ctype.kind,
            "recursive": True,
        }

    seen = seen | {ctype}

    ctype_dict: dict[str, Any] = {}
    for attr_name in _attr_names:
        if attr_name == "fields" and ctype.kind in {"struct", "union"}:
            try:
                _ffi.sizeof(ctype)
            except _ffi.error:
                continue

        attr_value = getattr(ctype, attr_name, None)
        if attr_value is not None:
            ctype_dict[attr_name] = attr_value

    if isinstance(ctype_dict.get("item"), _cffi_backend.CType):
        ctype_dict["item"] = _ctype2dict(ctype_dict["item"], seen)

    if isinstance(ctype_dict.get("fields"), (tuple, list)):
        ctype_dict["fields"] = _process_field(ctype_dict["fields"], seen)

    if isinstance(ctype_dict.get("args"), (tuple, list)):
        ctype_dict["args"] = [_ctype2dict(arg, seen) for arg in ctype_dict["args"]]

    if isinstance(ctype_dict.get("result"), _cffi_backend.CType):
        ctype_dict["result"] = _ctype2dict(ctype_dict["result"], seen)

    return ctype_dict


def _process_field(
    fields: list[tuple[str, object]] | tuple[tuple[str, object], ...],
    seen: set[_cffi_backend.CType],
) -> list[dict[str, Any]]:
    fields_list: list[dict[str, Any]] = []
    for field_entry in fields:
        field_name, field_value = field_entry
        field_dict: dict[str, Any] = {"name": field_name}

        if isinstance(field_value, _cffi_backend.CField):
            for fattr_name in _fattr_names:
                fattr_value = getattr(field_value, fattr_name, None)
                if fattr_value is None:
                    continue

                if isinstance(fattr_value, _cffi_backend.CType):
                    field_dict[fattr_name] = _ctype2dict(fattr_value, seen)
                else:
                    field_dict[fattr_name] = fattr_value
        else:
            field_dict["field_object"] = field_value

        fields_list.append(field_dict)

    return fields_list


def _ffiname2dict(name: str) -> dict[str, Any]:
    if _ffi is None:
        raise RuntimeError(CFFI_NONE)

    ctype: _cffi_backend.CType = _ffi.typeof(name)
    return {"name": name, "category": "ffi_typedef", "ctype": ctype} | _ctype2dict(
        ctype
    )


def _libname2dict(name: str) -> dict[str, Any]:
    if _ffi is None:
        raise RuntimeError(CFFI_NONE)

    ctype: _cffi_backend.CType

    try:
        ctype = _ffi.typeof(_ffi.addressof(_lib, name))
    except AttributeError as ea:
        try:
            ctype = _ffi.typeof(getattr(_lib, name))
        except TypeError as et:
            type_obj = type(getattr(_lib, name))
            if type_obj.__module__ == "builtins":
                type_str = f"builtins <{type_obj.__name__}>"
            else:
                type_str = str(type_obj)

            return {
                "name": name,
                "category": "lib_global",
                "ctype": None,
                "cname": f"NA - {type_str}",
            }

    return {"name": name, "category": "lib_global", "ctype": ctype} | _ctype2dict(ctype)


@dataclass
class CFFICTypes:
    ffi_names: list[str] = field(default_factory=list, init=False)
    lib_names: list[str] = field(default_factory=list, init=False)
    ffi_ctypes: list[dict[str, Any]] = field(default_factory=list, init=False)
    lib_ctypes: list[dict[str, Any]] = field(default_factory=list, init=False)
    enum_members: set[str] = field(default_factory=set, init=False)

    def get_ctypes(self) -> tuple[list[str], list[str], list[dict], list[dict]]:
        if _ffi is None:
            raise RuntimeError(CFFI_NONE)

        ffi_names: list[str] = sorted(set().union(*_ffi.list_types()))
        self.ffi_names = ffi_names

        if ffi_names:
            self.ffi_ctypes = [_ffiname2dict(ffi_name) for ffi_name in ffi_names]

            for ctype in self.ffi_ctypes:
                self.enum_members.update(ctype.get("relements") or {})

        lib_names: list[str] = sorted(set(dir(_lib)) - self.enum_members)
        self.lib_names = lib_names

        if lib_names:
            self.lib_ctypes = [_libname2dict(lib_name) for lib_name in lib_names]

        return ffi_names, lib_names, self.ffi_ctypes, self.lib_ctypes
