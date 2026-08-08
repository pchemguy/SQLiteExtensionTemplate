import re
from pathlib import Path


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
