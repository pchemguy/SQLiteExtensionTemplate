---
url: https://chatgpt.com/c/6a786079-f408-83eb-87b1-e0d35b2804a5
---

# SQLite MSVC build system

`sqlite_msbuild.bat` builds SQLite on Windows with MSVC and SQLite's `Makefile.msc`. It can add ICU from Conda, build zlib, compile stock SQLite extensions into the amalgamation, and run project-specific build hooks. The default target produces a command-line shell, a DLL and libraries for static and dynamic linking. For the Python and CFFI workflow, see the [template README](README.md#test-with-python).

## Running a build

Run these commands from the repository root in `cmd.exe` with the Visual C++ Build Tools and Windows SDK installed. For the default build, activate a Conda environment containing ICU for the target architecture first. The harness calls the adjacent [msbuild.bat](msbuild.bat) to find or verify MSVC.

```cmd
sqlite_msbuild.bat
```

With the build switches initially unset, this includes ICU, zlib, the stock modules, alphabet and CTD. Select the full **test** preset to export the alphabet and CTD APIs used by CFFI. For a SQLite-only build, the bare preset also works from a plain CMD prompt with the Build Tools installed.

| Entry point | `USE_ICU` | `USE_ZLIB` | `SQLITE_EXTRA` (stock) | `USE_EXTRAS` (project) | Test API |
| --- | ---: | ---: | ---: | ---: | --- |
| [sqlite_msbuild.bat](sqlite_msbuild.bat), defaults | 1 | 1 | 1 | 1 | Off unless `USE_TEST=1` |
| [sqlite_msbuild_bare.bat](sqlite_msbuild_bare.bat) | 0 | 0 | 0 | 0 | No project modules |
| [sqlite_msbuild_bare_icu.bat](sqlite_msbuild_bare_icu.bat) | 1 | 0 | 0 | 0 | No project modules |
| [sqlite_msbuild_bare_icu_ext.bat](sqlite_msbuild_bare_icu_ext.bat) | 1 | 1 | 1 | 0 | No project modules |
| [sqlite_msbuild_bare_icu_ext_extra.bat](sqlite_msbuild_bare_icu_ext_extra.bat) | 1 | 1 | 1 | 1 | Sets `USE_TEST=1` and `SQLITE_ENABLE_ALPHABET=1` |

The four preset scripts set environment variables in the caller and invoke the harness without arguments. To isolate a preset's settings, run it in a child CMD, for example `cmd /d /c sqlite_msbuild_bare.bat`. To pass a target or NMAKE option, invoke the main script directly. Ordinary arguments reach the **final** NMAKE invocation. The harness still runs its preparation, export and packaging steps around that invocation.

```cmd
sqlite_msbuild.bat sqlite3.dll
```

### Configuration

Set feature switches to `0` or `1` before calling the main script. Start with a fresh `out\build` when changing the configuration.

| Variable | Effect |
| --- | --- |
| `USE_ICU` | Defaults to `1`. Validates the active Conda ICU and stages its headers, libraries and runtime DLLs. Set to `0` for a build without ICU or Conda. |
| `USE_ZLIB` | Defaults to `1`. Downloads or reuses zlib and builds it for SQLite. To turn it off, set **both** `SQLITE_EXTRA=0` and `USE_ZLIB=0`. Any `SQLITE_EXTRA` value other than `0` forces `USE_ZLIB=1`. |
| `SQLITE_EXTRA` | Defaults to `1`. The `1` branch stages the stock `ext\misc` sources, adds the generated dispatcher to `EXTRA_SRC`, and selects it through `SQLITE_EXTRA_AUTOEXT`. |
| `USE_EXTRAS` | Defaults to `1`. Calls the `sqlite_ext_*` files alongside the harness. The repository supplies an alphabet hook and a CTD hook. |
| `SQLITE_ENABLE_ALPHABET` | The alphabet hook skips its work only for the exact value `0`. Otherwise it adds `-DSQLITE_ENABLE_ALPHABET`. CTD runs whenever project hooks are enabled. |
| `USE_TEST` | The main script leaves this unset unless supplied by the caller. The enabled project hooks add their test export macros only for `1`. Every configuration uses `out\build`. |

For example, this builds alphabet and CTD for the full Python test suite without requiring Conda ICU. Stock extensions stay enabled because that stage connects alphabet to SQLite's per-connection initialization.

```cmd
set "USE_ICU=0"
set "SQLITE_EXTRA=1"
set "USE_EXTRAS=1"
set "SQLITE_ENABLE_ALPHABET=1"
set "USE_TEST=1"
sqlite_msbuild.bat
```

## Environment and tool checks

When `VSINSTALLDIR` is set, the helper verifies the active developer environment. Otherwise it looks for `vcvars64.bat` via `VCVARS` or `PATH`, the Visual Studio installation roots, and the local or configured Build Tools roots (`MSBUILDTOOLS`, `BUILDTOOLS`, `MSBUILD`). A `VCVARS` path ending in `vcvarsall.bat` selects its `vcvars64.bat` sibling. Automatic activation selects x64. For x86, start in an already initialized x86 developer prompt and use matching Python and ICU binaries. The [bundled Python bootstrap](pyenv/Anaconda.bat) downloads x64 tools.

The helper checks `VisualStudioVersion`, the `VCINSTALLDIR` directory and `VSCMD_ARG_TGT_ARCH` (`x86` or `x64`). It resolves `nmake.exe`, `cl.exe`, `link.exe`, `lib.exe`, `dumpbin.exe` and `curl.exe`, and checks for `%windir%\System32\tar.exe`. An external `tclsh.exe` is optional. The harness uses SQLite's `out\build\jimsh0.exe` for copying, patching and bundling sources. It leaves `NO_TCL` and `WITHOUT_JIMSH` to the makefile or calling environment.

The linker check examines `link.exe /?` for the Microsoft linker signature. A different directory from `cl.exe` triggers a warning. If a non-Microsoft `link.exe` resolves from a managed Conda `<prefix>\Library\usr\bin` and the matching `<prefix>.bat` exists, the helper renames it to `link_.exe`. It then resolves both tools again and requires the Microsoft linker beside `cl.exe`. For other collisions, correct `PATH` and use `where.exe cl.exe` and `where.exe link.exe` to inspect resolution. [MSVC environment helper](msbuild.bat)

With `USE_ICU=1` the helper also checks `CONDA_PREFIX` and uses `dumpbin /headers` on each versioned `icuuc*.dll` in `%CONDA_PREFIX%\Library\bin`. It requires at least one matching DLL and the selected PE machine type (`14C` for x86, `8664` for x64). This check runs on **every** ICU build, including one with an existing staged ICU tree.

## Inputs, cache and dependencies

The project root is the directory containing `sqlite_msbuild.bat`. The harness looks for `patch_sqlite_misc_autoext.tcl` in `tool\`, `tools\` and `extra\` in that order, then uses that directory for both preparation scripts. This repository uses `tool\`. Use a checkout path without spaces for builds with project hooks because the hook-discovery wildcard expands an unquoted path.

| Input | Source on first use | Reuse condition |
| --- | --- | --- |
| SQLite | [SQLite source-tree ZIP](https://sqlite.org/src/zip/sqlite.zip) | `out\cache\sqlite.zip` is reused. `out\sqlite\Makefile.msc` marks the extracted source tree. |
| zlib | [Latest madler/zlib release](https://github.com/madler/zlib/releases/latest) | `out\cache\zlib.tar.gz` skips release discovery and download. `out\sqlite\compat\zlib\win32\Makefile.msc` marks extraction, and `zlib1.dll` in that zlib root skips compilation. |
| alphabet and CTD | The hooks fetch their `.c`, `.h` and `_api.h` files from this repository's [main branch](https://github.com/pchemguy/SQLiteExtensionTemplate/tree/main/src) via `raw.githubusercontent.com`. | Each existing file under `out\cache\SQLiteExtensionTemplate\src` is reused individually. |
| ICU | The active Conda prefix's `Library` directory | A marked and validated `out\sqlite\compat\icu` tree is reused for the selected architecture. |

For a missing file, the downloader follows redirects, retries with curl, and writes to a sibling `.part`. It checks the final HTTP status for `200` and rejects a `text/html` response before renaming the file into place. Existing files bypass these checks. Response headers go to a sibling `.log` and the final status and media type to `<target>.response.log`. The extraction helper uses the Windows system tar and skips extraction when the specified marker exists. [Download helper](download_file.bat) · [Extraction helper](extract_archive.bat)

For zlib, the harness saves the effective `releases/latest` URL in `out\cache\zlib-release-url.txt`, validates the dotted numeric tag, and downloads `releases/download/v<version>/zlib-<version>.tar.gz`. It expects one versioned archive root containing `win32\Makefile.msc`, renames that root to `compat\zlib`, and runs SQLite's NMAKE `zlib` target with `ZLIBLIB=all` when the DLL is missing.

### Conda ICU staging

On first use, the staging routine checks `%CONDA_PREFIX%\python.exe` and `%CONDA_PREFIX%\Library\bin\icuinfo.exe`. It copies `Library\include\unicode`, `Library\lib\icu??.lib`, `Library\bin\icu*.dll` and `icuinfo.exe` into `out\sqlite\compat\icu.stage`. Headers go under `include\unicode`. The x64 target uses `lib64` and `bin64`, and x86 uses `lib` and `bin`. The routine removes unversioned `icu??.dll` aliases and `icutest*.dll` from the staging directory.

Validation requires exactly one versioned common DLL (`icuuc<N>.dll`), matching `icuin<N>.dll` and `icudt<N>.dll`, `icuinfo.exe`, the three import libraries `icuuc.lib`, `icuin.lib` and `icudt.lib`, and the headers `utypes.h`, `ucol.h`, `uregex.h` and `ustring.h`. It checks that the required files are nonempty. It then writes `.icu-staged` and renames `icu.stage` to `icu`. A subsequent build validates the marked tree before reusing it. Switching Conda prefixes or upgrading ICU leaves a valid staged copy in use until it is moved aside.

## Building the amalgamation

1. The harness creates the output directories, verifies MSVC, and sets the SQLite options. A diagnostic target exits at this point. A normal build fetches and extracts SQLite, builds or reuses zlib if enabled, and stages ICU if enabled.
2. From `out\build` it invokes `nmake` on `.target_source`. SQLite prepares `tsrc` and its Jim Tcl interpreter. All extension transformations below operate on staged files.
3. With `SQLITE_EXTRA=1` the stock stage copies the selected SQLite modules to `tsrc`. It runs the patcher and bundler and appends the prepared C files and `misc_ext_init.c` to `EXTRA_SRC`.
4. With `USE_EXTRAS=1` it calls the project hooks. Each participating hook stages its source and headers, runs the same preparation tools and appends its C file to the shared `EXTRA_SRC` list.
5. NMAKE builds `sqlite3.def` and its prerequisite `libsqlite3.lib`. The harness replaces the definition file, runs the requested NMAKE target with the assembled `EXTRA_SRC`, regenerates `sqlite3.lib`, and collects the available artifacts.

### SQLite options and stock modules

`BUILD_OPTIONS` sets `SESSION=1`, `RBU=1`, `API_ARMOR=1` and `SYMBOLS=0`. It initializes `OPT_XTRA` and `EXTRA_SRC` afresh. The base definitions in `OPT_XTRA` are listed below. ICU additionally appends `SQLITE_ENABLE_ICU_COLLATIONS`.

| Area | Base definitions |
| --- | --- |
| Full-text search | `SQLITE_ENABLE_FTS4=1`, `SQLITE_ENABLE_FTS3_PARENTHESIS`, `SQLITE_ENABLE_FTS3_TOKENIZER` |
| Planning and diagnostics | `SQLITE_ENABLE_QPSG`, `SQLITE_ENABLE_STAT4`, `SQLITE_ENABLE_EXPLAIN_COMMENTS=1`, `SQLITE_ENABLE_NORMALIZE` |
| SQL functions and behavior | `SQLITE_ENABLE_OFFSET_SQL_FUNC=1`, `SQLITE_SOUNDEX`, `SQLITE_DQS=0`, `SQLITE_LIKE_DOESNT_MATCH_BLOBS` |
| Limits and defaults | `SQLITE_MAX_EXPR_DEPTH=100`, `SQLITE_MAX_ATTACHED=100`, `SQLITE_DEFAULT_FOREIGN_KEYS=1`, `SQLITE_DEFAULT_SYNCHRONOUS=1` |
| Interfaces | `SQLITE_OMIT_DEPRECATED`, `SQLITE_USE_URI=1` |

The stock stage takes these 15 files from `out\sqlite\ext\misc`. Each entry names the source and the suffix of its `SQLITE_ENABLE_` definition.

| Source | Suffix | Source | Suffix | Source | Suffix |
| --- | --- | --- | --- | --- | --- |
| `compress.c` | `COMPRESS` | `csv.c` | `CSV` | `decimal.c` | `DECIMAL` |
| `fuzzer.c` | `FUZZER` | `noop.c` | `NOOP` | `prefixes.c` | `PREFIXES` |
| `regexp.c` | `REGEXP` | `remember.c` | `REMEMBER` | `rot13.c` | `ROT` |
| `series.c` | `SERIES` | `sha1.c` | `SHA` | `shathree.c` | `SHATHREE` |
| `sqlar.c` | `SQLAR` | `uint.c` | `UINT` | `uuid.c` | `UUID` |

The patcher adapts recognized loadable initializers for core use, preserves previously registered modules across hook calls, and generates `sqlite3ExtraAutoExtInit` in `tsrc\misc_ext_init.c`. Each call in that dispatcher is guarded by its module's `SQLITE_ENABLE_…` macro. The bundler recursively inlines local literal includes relative to `tsrc` and elides the bare SQLite public headers already supplied by the amalgamation. Set `BUNDLE_EXTRA_SRC_TRACE=0` to suppress the per-file trace. [Initializer patcher](tool/patch_sqlite_misc_autoext.tcl) · [Source bundler](tool/bundle_extra_src.tcl)

### Project hooks and SQL registration

| Hook | What enters SQLite | Effect of `USE_TEST=1` |
| --- | --- | --- |
| [sqlite_ext_alphabet.bat](sqlite_ext_alphabet.bat) | Adds `alphabet.c` and `SQLITE_ENABLE_ALPHABET`. The patcher adds `sqlite3AlphabetInit` to the dispatcher. | Defines `ALPHABET_TEST` and `ALPHABET_BUILD_LIB` to export the `ab_*` helpers. |
| [sqlite_ext_ctd.bat](sqlite_ext_ctd.bat) | Adds `ctd.c`, a standalone C API fixture. It has no SQLite initializer. The patcher's message about a missing initialization function is expected for this file. | Defines `CTD_TEST` and `CTD_BUILD_LIB` to export the `ctd_*` interface. |

**To get `alpha_string()` on a new connection, enable both stock and project extensions and leave alphabet enabled.** The stock stage alone sets `SQLITE_EXTRA_AUTOEXT=sqlite3ExtraAutoExtInit` and includes the dispatcher in `EXTRA_SRC`. With only project hooks enabled, the alphabet C source can enter the amalgamation and expose test symbols, but SQLite has no configured call to its initializer. CTD has no SQL registration dependency.

### Building local source edits

On a branch or working tree, the checked-in `src\` and the cache can differ. To build local changes, copy the originals into the hook cache before running the harness. The following commands are for an interactive CMD at the repository root. In a batch file use `%%F` for the loop variable.

```cmd
if not exist "out\cache\SQLiteExtensionTemplate\src" mkdir "out\cache\SQLiteExtensionTemplate\src"
for %F in (alphabet.c alphabet.h alphabet_api.h ctd.c ctd.h ctd_api.h) do copy /y "src\%F" "out\cache\SQLiteExtensionTemplate\src\"
```

Move the previous `out\build` aside before rebuilding so NMAKE regenerates the amalgamation and objects with these inputs. Simply deleting the hook cache downloads from `main` again. The CFFI builder reads the checkout's `src\*_api.h`, so keeping both sides on the same revision matters when declarations change.

## Exports and packaged files

The harness starts a new `sqlite3.def` with `EXPORTS`. It filters `dumpbin /linkermember:2 libsqlite3.lib` for names with an alphanumeric prefix followed by `_`, sorts the names from `exports.txt` and appends them to the definition file. This covers names such as `sqlite3_open`, `ab_utf8_length` and `ctd_version` in an undecorated listing. The filter does not match a leading underscore. Check the definition file and the DLL's export table when using x86 symbol decoration. After the final NMAKE invocation, `lib /def:… /machine:%VSCMD_ARG_TGT_ARCH%` creates the import library for the selected architecture.

| Destination | Files placed there |
| --- | --- |
| `out\build` | NMAKE working directory for all presets. Contains `tsrc`, the generated `sqlite3.c`, build tools and intermediates. |
| `out\bin` | `sqlite3.exe` and `sqlite3.dll` when built, staged `icu*.dll` with ICU, and `zlib1.dll` when available and enabled. |
| `out\include` | Generated `out\build\sqlite3*.h`, including `sqlite3.h` and `sqlite3ext.h` for a normal full build. Project headers for CFFI come from the checkout's `src\`. |
| `out\lib\import` | `sqlite3.def` and `sqlite3.lib`. Link against this import library to call the shared `sqlite3.dll`. |
| `out\lib\static` | `libsqlite3.lib` for consumers that link SQLite statically. |

Collection first deletes existing files in `out\bin`. It leaves the include and library directories in place and copies available build products. Most build stages propagate errors, but the collector returns success even when a copy fails or a named target produces only a subset. Check the actual files needed by the consumer.

After building the full test preset, these checks exercise SQL registration in the shell and inspect the DLL for one symbol from each project module. Run `dumpbin` in an active MSVC shell.

```cmd
out\bin\sqlite3.exe ":memory:" "SELECT narg FROM pragma_function_list WHERE name='alpha_string' ORDER BY narg;"
dumpbin /exports out\bin\sqlite3.dll | findstr /i /c:"ab_utf8_length" /c:"ctd_version"
```

The SQL query should return `1`, `2` and `3`. The symbol check should list both names. For SQL tests through Python, also check which DLL the interpreter loads. [Python test procedure](README.md#test-with-python)

## Diagnostics and rebuilding

`env`, `tcl-env` and `tcl-test` as the first argument dispatch directly to the identically named targets in the extracted `Makefile.msc`. The environment checks still run. Dispatch precedes downloads and builds, so prepare the SQLite tree first. After invoking NMAKE the harness returns **100**, regardless of the diagnostic target's own result. Read the console output for the target result.

```cmd
sqlite_msbuild.bat env
```

`sqlite_msbuild.bat clean` takes the ordinary target path. Preparation and definition generation still precede NMAKE's `clean`, and the harness then attempts to regenerate the import library from a definition file that `clean` can remove. For a fresh build, move the applicable generated state aside and run the desired preset again.

| What changed | State to refresh |
| --- | --- |
| Options, test exports or project sources | Start with a fresh `out\build`. For local source changes, update the hook cache first. |
| Architecture | Use a fresh build and matching zlib and ICU trees. Moving the whole `out` aside also isolates packaged libraries and headers. |
| SQLite or zlib version | Refresh both the cached archive and its extracted tree, then rebuild. `out\sqlite` also contains the staged dependencies under `compat`. |
| Conda ICU version or incomplete staging | Move `out\sqlite\compat\icu` aside to restage. Inspect and move aside any leftover `icu.stage` before retrying. |
| All inputs and outputs | Move `out` aside. A fresh run resolves the current SQLite snapshot, zlib release and project `main` sources again. |

The harness removes old `out\stdout.log` and `out\stderr.log` at startup. Normal diagnostics go to the console, and download logs live next to the cached files. Define `NO_COLOR` or `NOCOLOR` for plain status labels. For repeatable builds, retain the exact source archives and project inputs and record the Conda ICU version, architecture and switches. The download cache checks for presence and does not pin revisions or verify file hashes.
