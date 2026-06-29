"""Render live schema metadata into the text the LLM reads.

Phase 1 kept the schema as a hardcoded constant. From Phase 1.5 the agent's
``get_schema()`` tool introspects the live database instead (see
:class:`AsyncpgRepository`), so the text can never drift from the real tables: a
new migration shows up here without a code change.

This module is the *presentation* half of that — a pure function that turns the
rows fetched from ``information_schema`` / ``pg_catalog`` into a human-readable
block. Keeping it free of any database handle makes it trivial to unit-test and
keeps the repository focused on I/O. The DB read lives in the repository; the
formatting lives here.

The text is written for a reader (the model): each table, its columns with type
and nullability, then its constraints verbatim from ``pg_get_constraintdef`` —
primary/foreign keys and the CHECK clauses that pin the allowed values, so the
model filters on real values instead of guessing.
"""

from collections import defaultdict
from typing import Any

# information_schema reports the verbose SQL-standard spelling for a couple of
# types; shorten them to the names we actually write in migrations.
_TYPE_ALIASES = {
    "timestamp with time zone": "timestamptz",
    "time without time zone": "time",
}


def format_schema_text(
    columns: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> str:
    """Build the schema description from introspected column and constraint rows.

    ``columns`` rows carry ``table_name``, ``column_name``, ``data_type`` and
    ``is_nullable``; ``constraints`` rows carry ``table_name`` and a ready-made
    ``definition`` string (e.g. ``PRIMARY KEY (id)`` or a ``CHECK (...)`` clause).
    Both are expected pre-sorted by the repository's queries.
    """
    columns_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for column in columns:
        columns_by_table[column["table_name"]].append(column)

    constraints_by_table: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for constraint in constraints:
        constraints_by_table[constraint["table_name"]].append(constraint)

    blocks = [
        _format_table(table, cols, constraints_by_table.get(table, []))
        for table, cols in columns_by_table.items()
    ]

    header = "Manufacturing database (PostgreSQL), introspected live. All tables are read-only."
    return header + "\n\n" + "\n\n".join(blocks) + "\n"


def _format_table(
    table: str,
    columns: list[dict[str, Any]],
    constraints: list[dict[str, Any]],
) -> str:
    name_width = max(len(column["column_name"]) for column in columns)
    type_width = max(len(_type_label(column["data_type"])) for column in columns)

    lines = [f"Table {table}"]
    for column in columns:
        name = column["column_name"].ljust(name_width)
        type_label = _type_label(column["data_type"]).ljust(type_width)
        nullability = "not null" if column["is_nullable"] == "NO" else "nullable"
        lines.append(f"  {name}  {type_label}  {nullability}")
    for constraint in constraints:
        lines.append(f"  {constraint['definition']}")
    return "\n".join(lines)


def _type_label(data_type: str) -> str:
    return _TYPE_ALIASES.get(data_type, data_type)
