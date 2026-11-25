@echo off

set "USE_ICU=0"
set "USE_ZLIB=0"
set "SQLITE_EXTRA=0"
set "USE_EXTRAS=1"
set "USE_TEST=1"

set "SQLITE_ENABLE_ALPHABET=1"

call "%~dp0sqlite_msbuild.bat"
