"""
Build the project's out-of-line CFFI wrapper against discovered C components.

The builder assumes a repository layout in which C components live under
``<repo>/src`` and built artifacts are staged under ``<repo>/out``. Each
wrapper-enabled C component is identified by a ``<name>_api.h`` header and must
also provide matching ``<name>.h`` and ``<name>.c`` files.

For each discovered component, the generated CFFI wrapper:

* consumes declarations from ``<name>_api.h`` via :func:`load_cdef_header`;
* includes ``<name>.h`` in the generated C source;
* defines ``<NAME>_TEST`` and ``<NAME>_USE_LIB`` while compiling the wrapper;
* links against discovered import libraries and any explicitly supplied
  libraries; and
* copies runtime binaries from ``out/bin`` beside the built Python extension.

The builder targets CFFI out-of-line API mode with dynamic linking to
pre-built C libraries.

https://chatgpt.com/c/6a7813fc-5d80-83eb-a476-70760939b048
"""

import platform
import sys
import os
import re
from pathlib import Path
import shutil

from cffi import FFI


class Config:
    """Derived build configuration for the generated CFFI wrapper.

    All paths and platform-specific compiler/linker settings are derived from
    the location of this module and the active Python runtime. No constructor
    arguments are required.

    The expected repository layout is::

        <repo>/
            src/
                <name>.c
                <name>.h
                <name>_api.h
            out/
                bin/
                include/
                lib/
                    import/
                    static/
            <python-package>/
                src/
                    <python-package>/
                        <this module>

    Attributes:
        prefix:
            Directory containing this builder module and the generated CFFI
            extension.
        program_name:
            Upper-case name of ``prefix``.
        wrapper_name:
            Python extension module name passed to :meth:`FFI.set_source`.
        repo_root:
            Derived repository root.
        repo_bin:
            Directory containing runtime shared-library artifacts.
        repo_inc:
            Directory containing staged public C headers.
        repo_libimport:
            Directory containing import libraries used for dynamic linking,
            primarily on Windows.
        repo_libstatic:
            Directory reserved for staged static libraries.
        c_src:
            Repository C source directory.
        wrapper_c_components:
            Names of validated C components participating in the wrapper.
        extra_compile_args:
            Platform-specific compiler arguments passed to CFFI.
        extra_link_args:
            Platform-specific linker arguments passed to CFFI.

    Raises:
        NotADirectoryError:
            If the derived repository C source directory does not exist.
    """

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
        """Derive repository paths and platform-specific build settings."""
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
            raise NotADirectoryError(
                f"C source directory does not exist: {self.c_src}"
            )

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
        """Discover and validate C components eligible for the CFFI wrapper.

        Component discovery is driven by files matching ``*_api.h`` under
        :attr:`c_src`. For each discovered component name, this method requires
        all of the following files to exist:

        * ``<name>.c``
        * ``<name>.h``
        * ``<name>_api.h``

        The top-level ``<name>.h`` header must additionally contain the
        component test macro ``<NAME>_TEST`` and at least one preprocessor
        definition of ``<NAME>_TEST_API``.

        Validation is performed for all discovered components before
        :attr:`wrapper_c_components` is updated. This prevents a failed
        discovery pass from leaving a partially populated component list.

        Raises:
            RuntimeError:
                If no wrapper components are discovered or if one or more
                discovered components violate the required file/header
                contract.
        """
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
        *extra_c_macros: tuple[str, str | None],
    ) -> list[tuple[str, str | None]]:
        """Build the preprocessor macro list for the generated wrapper.

        Each discovered C component contributes two automatically generated
        macros:

        * ``<NAME>_TEST``
        * ``<NAME>_USE_LIB``

        Additional macros are appended after validation.

        Args:
            *extra_c_macros:
                Additional two-item ``(name, value)`` macro tuples. ``name``
                must be a non-empty string. ``value`` must be either a string
                or ``None``.

        Returns:
            Macro tuples suitable for the ``define_macros`` argument of
            :meth:`FFI.set_source`.

        Raises:
            TypeError:
                If a macro name is not a string or a macro value is neither a
                string nor ``None``.
            ValueError:
                If a macro tuple does not contain exactly two items or if its
                name is empty.
        """
        macros: list[tuple[str, str | None]] = []

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
        """Return library names to link into the generated wrapper.

        If :attr:`repo_libimport` exists, all ``*.lib`` files in that directory
        are discovered in deterministic filename order and added using their
        stem names. Explicitly supplied libraries are then appended.

        A trailing ``.lib`` suffix on an explicit library name is stripped
        case-insensitively because CFFI/distutils expects logical library names
        rather than Windows import-library filenames.

        Args:
            *extra_libraries:
                Additional logical library names.

        Returns:
            Library names suitable for the ``libraries`` argument of
            :meth:`FFI.set_source`.

        Raises:
            TypeError:
                If an explicit library name is not a string.
        """
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
        """Return validated library search directories for the linker.

        The package directory is always included first so copied runtime/link
        artifacts beside the wrapper remain discoverable where supported.
        :attr:`repo_libimport` is included when it exists. Explicit directories
        are validated and appended in caller-supplied order.

        Args:
            *extra_library_dirs:
                Additional library directories. Empty values are ignored.

        Returns:
            Directory paths as strings suitable for the ``library_dirs``
            argument of :meth:`FFI.set_source`.

        Raises:
            NotADirectoryError:
                If a non-empty explicit directory does not exist or is not a
                directory.
        """
        library_dirs = [str(self.prefix)]

        if self.repo_libimport.is_dir():
            library_dirs.append(str(self.repo_libimport))

        for directory in extra_library_dirs:
            if not directory:
                continue

            path = Path(directory)

            if not path.is_dir():
                raise NotADirectoryError(
                    f"Library directory does not exist: {path}"
                )

            library_dirs.append(str(path))

        return library_dirs

    def get_c_includes(self, *extra_c_includes: str) -> str:
        """Generate the C ``#include`` block used by ``FFI.set_source()``.

        Each discovered wrapper component contributes an include directive for
        its top-level ``<name>.h`` header. Additional header names are validated
        and appended afterward.

        Args:
            *extra_c_includes:
                Additional C header names. Each value must be a string ending
                in ``.h``.

        Returns:
            A newline-delimited C source fragment ending with a trailing
            newline.

        Raises:
            TypeError:
                If an extra include is not a string.
            ValueError:
                If an extra include does not end in ``.h``.
        """
        includes = [
            f'#include "{name}.h"'
            for name in self.wrapper_c_components
        ]

        for header in extra_c_includes:
            if not isinstance(header, str):
                raise TypeError("C include must be str")

            if not header.endswith(".h"):
                raise ValueError(
                    f"C include must end with '.h': {header!r}"
                )

        includes.extend(
            f'#include "{header}"'
            for header in extra_c_includes
        )

        return "\n".join(includes) + "\n"

    def get_include_dirs(self, *extra_include_dirs: str | Path) -> list[str]:
        """Return validated C header search directories.

        The package directory is always included first. :attr:`repo_inc` is
        included when it exists. Explicit include directories are validated and
        appended in caller-supplied order.

        Args:
            *extra_include_dirs:
                Additional include directories.

        Returns:
            Directory paths as strings suitable for the ``include_dirs``
            argument of :meth:`FFI.set_source`.

        Raises:
            NotADirectoryError:
                If an explicit include directory does not exist or is not a
                directory.
        """
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
        """Assemble declarations passed to ``FFI.cdef()``.

        The ``<name>_api.h`` header for every discovered wrapper component is
        loaded and transformed by :func:`load_cdef_header`. The resulting
        declaration blocks are joined with one blank line between components.

        Args:
            extra_c_snippet:
                Optional additional C declarations appended after all discovered
                component declarations.

        Returns:
            Combined C declarations suitable for :meth:`FFI.cdef`.
        """
        declarations = [
            load_cdef_header(self.c_src / f"{name}_api.h")
            for name in self.wrapper_c_components
        ]

        if extra_c_snippet:
            declarations.append(extra_c_snippet)

        return "\n\n".join(declarations)

    def copy_bin(self) -> None:
        """Copy staged runtime binaries into the wrapper package directory.

        The contents of :attr:`repo_bin` are copied directly into
        :attr:`prefix`. Existing files are overwritten and existing
        subdirectories are merged.

        If :attr:`repo_bin` does not exist, the method performs no action.
        """
        if not self.repo_bin.is_dir():
            return

        for source in self.repo_bin.iterdir():
            destination = self.prefix / source.name

            if source.is_dir():
                shutil.copytree(source, destination, dirs_exist_ok=True)
            else:
                shutil.copy2(source, destination)


def load_cdef_header(path: str | Path) -> str:
    """Load a dual-use C API header and normalize it for ``FFI.cdef()``.

    The transformation removes the supported preprocessor directives that are
    meaningful to a C compiler but invalid or unnecessary in CFFI declarations.
    Component ``*_TEST_DATA_API`` declaration markers are converted to
    ``extern`` and generic ``*_API`` markers are removed.

    Args:
        path:
            Path to the API header to load.

    Returns:
        Header contents transformed into declarations consumable by
        :meth:`FFI.cdef`.

    Raises:
        OSError:
            If the header cannot be read.
        UnicodeError:
            If the header is not valid UTF-8.
    """
    header_path = Path(path)
    declarations = header_path.read_text(encoding="utf-8")

    # Remove supported preprocessor directives from a dual-use API header.
    pattern = r"^[ \t]*#[ \t]*(?:if|ifdef|ifndef|endif|define)\b.*(?:\r?\n|$)"
    declarations = re.sub(pattern, "", declarations, flags=re.MULTILINE)

    pattern = r"^[A-Z][A-Z0-9_]*_TEST_DATA_API[ \t]+"
    declarations = re.sub(
        pattern,
        "extern ",
        declarations,
        flags=re.MULTILINE,
    )

    pattern = r"^[A-Z][A-Z0-9_]*_API[ \t]+"
    declarations = re.sub(
        pattern,
        "",
        declarations,
        flags=re.MULTILINE,
    )

    return declarations


def main() -> int:
    """Discover components, build the CFFI wrapper, and stage runtime binaries.

    Returns:
        Process exit status. ``0`` indicates successful wrapper generation and
        runtime binary staging.

    Raises:
        Exception:
            Propagates configuration, discovery, CFFI compilation, filesystem,
            and linker errors to the caller.
    """
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

    ffibuilder.compile(
        tmpdir=str(config.prefix),
        verbose=True,
    )
    config.copy_bin()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
