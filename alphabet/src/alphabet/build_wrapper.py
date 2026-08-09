import platform
import sys
import os
import re
from pathlib import Path
import shutil

from cffi import FFI


class Config:
    prefix: Path
    program_name: str
    wrapper_name: str
    repo_root: Path
    repo_bin: Path
    repo_inc: Path
    repo_libimport: Path
    repo_libstatic: Path
    c_src: Path
    wrapper_c_components: list[str]
    extra_compile_args: list[str]
    extra_link_args: list[str]

    def __init__(self) -> None:
        prefix = Path(__file__).resolve()

        self.prefix         = prefix.parent
        self.repo_root      = prefix.parents[3]
        self.program_name   = self.prefix.name.upper()
        self.wrapper_name   = "_cffi_wrapper"
        self.c_src          = self.repo_root / "src"
        self.repo_bin       = self.repo_root / "out" / "bin"
        self.repo_inc       = self.repo_root / "out" / "include"
        self.repo_libimport = self.repo_root / "out" / "lib" / "import"
        self.repo_libstatic = self.repo_root / "out" / "lib" / "static"

        if not self.c_src.is_dir():
            raise NotADirectoryError(f"C source directory does not exist: {self.c_src}")

        self.wrapper_c_components = []
        self.extra_compile_args = []
        self.extra_link_args = []

        if platform.python_compiler().startswith("MSC"):
            self.extra_compile_args = ["/TC", "/O2"]
        else:
            self.extra_compile_args = []

        if sys.platform == "darwin":
            self.extra_link_args = ["-Wl,-rpath,@loader_path"]
        elif sys.platform != "win32":
            self.extra_link_args = ["-Wl,-rpath,$ORIGIN"]
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
                violations.append(f"no {macro}_TEST")
            
            if not re.search(
                rf"^[ \t]*#[ \t]*define[ \t]+{re.escape(macro)}_TEST_API\b",
                text,
                flags=re.MULTILINE,
            ):
                violations.append(f"no #define {macro}_TEST_API")
        
            if violations:
                invalid.append(f"{name}: {', '.join(violations)}")
        
        if invalid:
            raise RuntimeError(
                f"Invalid C components under {self.c_src}:\n"
                + "\n".join(f"  {item}" for item in invalid)
            )
        
        self.wrapper_c_components = names

        if not names:
            raise RuntimeError("No wrapper components found.")

    def get_c_macros(
        self,
        *extra_c_macros: tuple[str, str | None]) -> list[tuple[str, str | None]]:
        macros: list[tuple[str] | tuple[str, str | None]] = []
    
        for name in self.wrapper_c_components:
            macro = name.upper()
            macros.append((f"{macro}_TEST", None))
            macros.append((f"{macro}_USE_LIB", None))
    
        for item in extra_c_macros:
            if len(item) == 2:
                name, value = item
    
                if not isinstance(name, str):
                    raise TypeError("C macro name must be str")

                if not name:
                    raise ValueError("C macro name must not be empty")
    
                if value is not None and not isinstance(value, str):
                    raise TypeError("C macro value must be str or None")
    
            else:
                raise ValueError("C macro must be a 2-tuple")
    
        macros.extend(extra_c_macros)

        return macros

    def get_libraries(self, *extra_libraries: str) -> list[str]:
        libraries: list[str] = []
    
        import_lib_dir = self.repo_libimport
    
        if import_lib_dir.is_dir():
            libraries.extend(
                path.stem for path in sorted(import_lib_dir.glob("*.lib"))
            )
    
        for library in extra_libraries:
            if not isinstance(library, str):
                raise TypeError("Library name must be str")
    
            libraries.append(
                library[:-4] if library.lower().endswith(".lib") else library
            )
    
        return libraries

    def get_library_dirs(self, *extra_library_dirs: str | Path) -> list[str]:
        library_dirs = [str(self.prefix)]
    
        if self.repo_libimport.is_dir():
            library_dirs.append(str(self.repo_libimport))
    
        for directory in extra_library_dirs:
            if not path:
                continue
            
            path = Path(directory)
    
            if not path.is_dir():
                raise NotADirectoryError(f"Library directory does not exist: {path}")
    
            library_dirs.append(str(path))
    
        return library_dirs

    def get_c_includes(self, *extra_c_includes: str) -> str:
        includes = [f'#include "{name}.h"' for name in self.wrapper_c_components]                      

        for header in extra_c_includes:
            if not isinstance(header, str):
                raise TypeError("C include must be str")
    
            if not header.endswith(".h"):
                raise ValueError(f"C include must end with '.h': {header!r}")
    
        includes.extend(f'#include "{header}"' for header in extra_c_includes)
    
        return "\n".join(includes) + "\n"

    def get_include_dirs(self, *extra_include_dirs: str | Path) -> list[str]:
        include_dirs = [str(self.prefix)]
    
        if self.repo_inc.is_dir():
            include_dirs.append(str(self.repo_inc))
    
        for directory in extra_include_dirs:
            path = Path(directory)
    
            if not path.is_dir():
                raise NotADirectoryError(f"Include directory does not exist: {path}")
    
            include_dirs.append(str(path))
    
        return include_dirs

    def get_cdef(self, extra_c_snippet: str | None = None) -> str:
        declarations = [
            load_cdef_header(self.c_src / f"{name}_api.h")
            for name in self.wrapper_c_components
        ]
    
        if extra_c_snippet:
            declarations.append(extra_c_snippet)
    
        return "\n\n".join(declarations)

    def copy_bin(self) -> None:
        if not self.repo_bin.is_dir():
            return
    
        for source in self.repo_bin.iterdir():
            destination = self.prefix / source.name
    
            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(source, destination)


def load_cdef_header(path: str | Path) -> str:
    """Load and transform a dual-use API header for ``FFI.cdef()``."""
    header_path = Path(path)
    declarations = header_path.read_text(encoding="utf-8")

    # Remove supported preprocessor directives from a dual-use API header.
    pattern = r"^[ \t]*#[ \t]*(?:if|ifdef|ifndef|endif|define)\b.*(?:\r?\n|$)"
    declarations = re.sub(pattern, "", declarations, flags=re.MULTILINE)
    pattern = r"^[A-Z][A-Z0-9_]*_TEST_DATA_API[ \t]+"
    declarations = re.sub(pattern, "extern ", declarations, flags=re.MULTILINE)
    pattern = r"^[A-Z][A-Z0-9_]*_API[ \t]+"
    declarations = re.sub(pattern, "", declarations, flags=re.MULTILINE)

    return declarations


def main() -> int:
    config = Config()
    config.discover_wrapper_components()

    ffibuilder = FFI()
    ffibuilder.cdef(config.get_cdef())

    ffibuilder.set_source(
        config.wrapper_name,
        config.get_c_includes(),
        sources=[],
        include_dirs=config.get_include_dirs(),
        libraries=config.get_libraries(),
        library_dirs=config.get_library_dirs(),
        define_macros=config.get_c_macros(),
        extra_compile_args=config.extra_compile_args,
        extra_link_args=config.extra_link_args,

    )

    ffibuilder.compile(tmpdir=str(config.prefix), verbose=True)
    config.copy_bin()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
