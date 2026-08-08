import platform
import sys
from importlib import import_module
from pathlib import Path
import shutil

from cffi import FFI

_cdef_header = (
    import_module(".cdef_header", __package__)
    if __package__
    else import_module("cdef_header")
)
load_cdef_header = _cdef_header.load_cdef_header


PROGRAM_NAME = "ALPHABET"
PREFIX = Path(__file__).resolve().parent
REPO_ROOT =  Path(__file__).resolve().parents[3]

CDEF_HEADER = f"{PROGRAM_NAME.lower()}_api.h"
src = REPO_ROOT / "src" / CDEF_HEADER
dst = Path.cwd() / CDEF_HEADER

if not dst.exists() and src.exists():
    shutil.copy2(src, dst)

SOURCES = []
LIBRARIES = ["sqlite3"]

C_MACROS = [
    (f"{PROGRAM_NAME.upper()}_TEST", None),
    (f"{PROGRAM_NAME.upper()}_USE_LIB", None),
    ("SQLITE_CORE", None),
]

EXTRA_COMPILE_ARGS = []
EXTRA_LINK_ARGS = []
if platform.python_compiler().startswith("MSC"):
    EXTRA_COMPILE_ARGS = ["/TC", "/O2"]
elif sys.platform == "darwin":
    EXTRA_LINK_ARGS = ["-Wl,-rpath,@loader_path"]
elif sys.platform != "win32":
    EXTRA_LINK_ARGS = ["-Wl,-rpath,$ORIGIN"]

WRAPPER_NAME = f"_{PROGRAM_NAME.lower()}_wrapper"

C_SNIPPET = f"""
    #include "{PROGRAM_NAME.lower()}.h"
"""
print(LIBRARIES)

def main() -> int:
    ffibuilder = FFI()
    declarations = load_cdef_header(PREFIX / CDEF_HEADER)
    ffibuilder.cdef(declarations)

    ffibuilder.set_source(
        WRAPPER_NAME,
        C_SNIPPET,
        sources=[str(source) for source in SOURCES],
        include_dirs=[str(PREFIX), str(REPO_ROOT / "out" / "include")],
        libraries=LIBRARIES,
        library_dirs=[str(PREFIX), str(REPO_ROOT / "out" / "bin")],
        define_macros=C_MACROS,
        extra_compile_args=EXTRA_COMPILE_ARGS,
        extra_link_args=EXTRA_LINK_ARGS,
    )

    ffibuilder.compile(tmpdir=str(PREFIX), verbose=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
