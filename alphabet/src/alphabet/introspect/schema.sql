PRAGMA foreign_keys = 0;

DROP TABLE IF EXISTS ctypes;
DROP TABLE IF EXISTS kinds;

CREATE TABLE kinds (
    "id"   INTEGER PRIMARY KEY,
    "name" TEXT COLLATE NOCASE NOT NULL UNIQUE
);

CREATE TABLE ctypes (
    "id"        INTEGER PRIMARY KEY,
    "name"      TEXT COLLATE NOCASE NOT NULL UNIQUE,
    "category"  TEXT COLLATE NOCASE NOT NULL CHECK("category" IN ('ffi_typedef', 'lib_global')),
    "cname"     TEXT COLLATE NOCASE NOT NULL,
    "kind"      TEXT COLLATE NOCASE,
    "item"      TEXT COLLATE NOCASE,
    "length"    INTEGER,
    "fields"    TEXT COLLATE NOCASE,
    "args"      TEXT COLLATE NOCASE,
    "result"    TEXT COLLATE NOCASE,
    "ellipsis"  TEXT COLLATE NOCASE,
    "abi"       TEXT COLLATE NOCASE,
    "elements"  TEXT COLLATE NOCASE,
    "relements" TEXT COLLATE NOCASE,
    CONSTRAINT "fk_ctypes_kind_kinds_name"
        FOREIGN KEY ("kind") REFERENCES "kinds"("name")
);

INSERT INTO kinds(id, name) VALUES
    (0, 'primitive'),
    (1, 'pointer'),
    (2, 'array'),
    (3, 'function'),
    (4, 'struct'),
    (5, 'union'),
    (6, 'enum');

PRAGMA foreign_keys = 1;
