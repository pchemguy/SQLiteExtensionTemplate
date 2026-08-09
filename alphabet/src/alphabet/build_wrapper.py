import platform
import sys
import os
import re
from pathlib import Path
import shutil

from cffi import FFI


def load_cdef_header(path: str | Path) -> str:
    """Load and transform a dual-use API header for ``FFI.cdef()``."""
    header_path = Path(path)
    declarations = header_path.read_text(encoding="utf-8")

    # Remove indiscriminately C-preprocessor directives from a dual-use API header.
    pattern = r"^[ \t]*#[ \t]*(?:if|ifdef|ifndef|endif|define)\b.*(?:\r?\n|$)"
    declarations = re.sub(pattern, "", declarations, flags=re.MULTILINE)
    pattern = r"^CTD_TEST_DATA_API[ \t]+"
    declarations = re.sub(pattern, "extern ", declarations, flags=re.MULTILINE)
    pattern = r"^[A-Z][A-Z0-9_]*_API[ \t]+"
    declarations = re.sub(pattern, "", declarations, flags=re.MULTILINE)

    return declarations


class Config:
    prefix: Path
    program_name: str
    wrapper_name: str
    repo_root: Path
    c_src: Path
    repo_bin: Path
    repo_inc: Path
    sources: list[str]
    libraries: list[str]
    wrapper_c_components: list[str]
    extra_compile_args: list[str]
    extra_link_args: list[str]

    def __init__(self) -> None:
        prefix = Path(__file__).resolve()

        self.prefix       = prefix.parent
        self.repo_root    = prefix.parents[3]
        self.program_name = self.prefix.name.upper()
        self.wrapper_name = f"_{self.program_name.lower()}_wrapper"
        self.c_src        = self.repo_root / "src"
        self.repo_bin     = self.repo_root / "out" / "bin"
        self.repo_inc     = self.repo_root / "out" / "include"

        self.sources = []
        self.libraries = ["sqlite3"]
        
        self.wrapper_c_components = []
        self.extra_compile_args = []
        self.extra_link_args = []

        if platform.python_compiler().startswith("MSC"):
            self.extra_compile_args = ["/TC", "/O2"]
        else:
            self.extra_compile_args = []

        if sys.platform != "win32":
            self.extra_link_args = ["-Wl,-rpath,$ORIGIN"]
        elif sys.platform == "darwin":
            self.extra_link_args = ["-Wl,-rpath,@loader_path"]
        else:
            self.extra_link_args = []

    def discover_wrapper_components(self) -> None:
        names = sorted(
            path.name.removesuffix("_api.h")
            for path in self.c_src.glob("*_api.h")
        )
        
        invalid: list[str] = []
        
        for name in names:
            source = self.c_src / f"{name}.c"
            header = self.c_src / f"{name}.h"
            api_header = self.c_src / f"{name}_api.h"
        
            missing = [
                path.name
                for path in (source, header, api_header)
                if not path.is_file()
            ]
        
            if missing:
                invalid.append(f"{name}: missing {', '.join(missing)}")
                continue
        
            text = header.read_text(encoding="utf-8")
            macro = name.upper()
        
            violations = []
        
            if not re.search(rf"\b{re.escape(macro)}_TEST\b", text):
                violations.append(f"no literal {macro}_TEST")
            
            if not re.search(rf"\b#\s*define\s+{re.escape(macro)}_TEST_API\b", text):
                violations.append(f"no #define {macro}_TEST_API")
        
            if violations:
                invalid.append(f"{name}: {', '.join(violations)}")
        
        if invalid:
            raise RuntimeError(
                f"Invalid C components under {self.c_src}:\n"
                + "\n".join(f"  {item}" for item in invalid)
            )
        
        self.wrapper_c_components = names


    def get_c_macros(
        self,
        *extra_c_macros: tuple[str] | tuple[str, str | None],
    ) -> list[tuple[str] | tuple[str, str | None]]:
        macros: list[tuple[str] | tuple[str, str | None]] = []
    
        for name in self.wrapper_c_components:
            macro = name.upper()
            macros.append((f"{macro}_TEST",))
            macros.append((f"{macro}_USE_LIB",))
    
        for item in extra_c_macros:
            if len(item) == 1:
                if not isinstance(item[0], str):
                    raise TypeError("C macro name must be str")
    
            elif len(item) == 2:
                name, value = item
    
                if not isinstance(name, str):
                    raise TypeError("C macro name must be str")

                if not name:
                    raise ValueError("C macro name must not be empty")
    
                if value is not None and not isinstance(value, str):
                    raise TypeError("C macro value must be str or None")
    
            else:
                raise ValueError("C macro must be a 1-tuple or 2-tuple")
    
        macros.extend(extra_c_macros)
        return macros

    def get_cdef(self, extra_c_snippet: str | None = None) -> str:
        declarations = [
            load_cdef_header(self.c_src / f"{name}_api.h")
            for name in self.wrapper_c_components
        ]
    
        if extra_c_snippet:
            declarations.append(extra_c_snippet)
    
        return "\n\n".join(declarations)

    def get_c_includes(self, *extra_c_includes: str) -> str:
        includes = [f'#include "{name}.h"'for name in self.wrapper_c_components]
    
        for header in extra_c_includes:
            if not isinstance(header, str):
                raise TypeError("C include must be str")
    
            if not header.endswith(".h"):
                raise ValueError(f"C include must end with '.h': {header!r}")
    
        includes.extend(f'#include "{header}"' for header in extra_c_includes)
    
        return "\n".join(includes) + "\n"




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
#include "{PROGRAM_NAME.lower()}.h"
"""
print(LIBRARIES)

def main() -> int:
    config = Config()
    config.discover_wrapper_components()

    ffibuilder = FFI()
    ffibuilder.cdef(config.get_cdef())

    ffibuilder.set_source(
        config.wrapper_name,
        config.get_c_includes(),
        sources=config.sources,
        include_dirs=[str(PREFIX), str(REPO_ROOT / "out" / "include")],
        libraries=config.libraries,
        library_dirs=[str(PREFIX), str(REPO_ROOT / "out" / "bin")],
        define_macros=config.get_c_macros(("SQLITE_CORE",)),
        extra_compile_args=config.extra_compile_args,
        extra_link_args=config.extra_link_args,

    )

    ffibuilder.compile(tmpdir=str(PREFIX), verbose=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
