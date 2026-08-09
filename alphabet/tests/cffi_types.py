"""Typing boundary for runtime-generated CFFI objects used by the test suite."""

from typing import Any, TypeAlias

# The generated wrapper has no static declaration-specific interface.  Keep its
# values explicitly dynamic while still requiring annotations at every boundary.
CffiValue: TypeAlias = Any
