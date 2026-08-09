from __future__ import annotations

# import os
# import sys
#
# sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# sys.path.insert(0, os.sep.join(os.path.abspath(__file__).split(os.sep)[:-2]))

from importlib import import_module
from typing import Any

import _cffi_backend

_cffi_wrapper = (
    import_module("._cffi_wrapper", __package__)
    if __package__
    else import_module("_cffi_wrapper")
)

from introspect import cffi_model, database


def main() -> int:
    ffi, lib = _cffi_wrapper.ffi, _cffi_wrapper.lib

    db: database.CFFIModelDB = database.CFFIModelDB(database=".")
    cffi_model.cffi_init(ffi, lib)
    ctypes: cffi_model.CFFICTypes = cffi_model.CFFICTypes()

    ffi_names: list[str]
    lib_names: list[str]
    ffi_ctypes: list[dict[str, Any]]
    lib_ctypes: list[dict[str, Any]] 
     
    ffi_names, lib_names, ffi_ctypes, lib_ctypes = ctypes.get_ctypes()

    ffi_ctypes_filtered: list[dict[str, Any]] = [
        {prop: value for prop, value in desc.items() if prop != "ctype"}
        for desc in ffi_ctypes
    ]

    if ffi_names:
        db.ctypes_insert(ffi_ctypes_filtered)

    lib_ctypes_filtered: list[dict[str, Any]] = [
        {prop: value for prop, value in desc.items() if prop != "ctype"}
        for desc in lib_ctypes
    ]

    if lib_names:
        db.ctypes_insert(lib_ctypes_filtered)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
