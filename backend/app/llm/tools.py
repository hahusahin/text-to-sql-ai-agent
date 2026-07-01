"""The tool catalogue we expose to the model — the agent's two capabilities.

A "tool" is, to the model, nothing more than this JSON description: a name, a
sentence on what it does, and a JSON Schema for its parameters. The model cannot
run anything itself; given this catalogue it can *ask* to call a tool by emitting
a structured ``function_call`` (name + JSON ``arguments``) instead of plain text.
The hand-written loop (Task 1.23) is what actually executes the call and feeds the
result — or the error — back. This module only declares the catalogue.

Shape note (see the ``openai-api-python`` skill): these are **Responses API** tool
schemas, which are flat — ``type``/``name``/``description``/``parameters`` at the
top level. This is deliberately *not* the legacy Chat Completions shape that nests
everything under a ``"function"`` key.

The descriptions are written for the model, not for us: they are part of the
prompt and steer when and how the model reaches for each tool, so they spell out
the rules (call ``get_schema`` first; a single read-only SELECT; errors come back
as text to be fixed) rather than assuming the model already knows them.
"""

GET_SCHEMA_TOOL = {
    "type": "function",
    "name": "get_schema",
    "description": (
        "Return the database schema as text: every table with its columns, types, "
        "primary and foreign keys, and the allowed values of constrained columns. "
        "Call this first, before writing any query, so you filter on real column "
        "names and real values instead of guessing. Takes no arguments."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
        "additionalProperties": False,
    },
}

RUN_QUERY_TOOL = {
    "type": "function",
    "name": "run_query",
    "description": (
        "Execute one read-only SQL query against the PostgreSQL database and return "
        "its rows as JSON. The query must be a single SELECT (a leading WITH ... "
        "SELECT is fine); no INSERT/UPDATE/DELETE or DDL, no multiple statements. "
        "Keep a LIMIT of at most 100 rows. If the query is rejected or the database "
        "raises an error, the error text is returned instead of rows — read it and "
        "call run_query again with a corrected query."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "A single read-only SELECT statement to execute.",
            },
        },
        "required": ["sql"],
        "additionalProperties": False,
    },
}

SEARCH_NOTES_TOOL = {
    "type": "function",
    "name": "search_notes",
    "description": (
        "Semantic search over operators' free-text notes on downtime events. Pass a "
        "short natural-language description of a problem or theme (e.g. 'oil or "
        "hydraulic leaks', 'waiting on materials', 'electrical control faults') and "
        "it returns the most similar downtime notes, each with its production line, "
        "time, reason_code and duration. Use this when the question is about WHAT "
        "operators described — symptoms, causes or themes that the structured "
        "reason_code column (only four coarse categories: breakdown, "
        "setup_changeover, material_shortage, planned_maintenance) cannot express. "
        "For counts, sums, averages or filters over structured columns, use "
        "run_query instead. The two can be combined: search_notes to find the "
        "relevant events, run_query to aggregate. Results are ranked by similarity, "
        "so treat weaker matches with caution and read each note before relying on it."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "A natural-language description of the notes to find.",
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}

TOOLS = [GET_SCHEMA_TOOL, RUN_QUERY_TOOL, SEARCH_NOTES_TOOL]
"""The full catalogue, ready to pass as ``tools=`` to ``responses.create``."""
