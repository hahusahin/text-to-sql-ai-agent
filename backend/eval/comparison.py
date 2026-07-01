"""Result-set comparison — the heart of execution-accuracy grading.

The whole eval rests on one question: do two result sets *mean the same thing*?
Not "are the two SQL strings equal" (they never are), and not even "are the two
lists of rows byte-identical" — the agent is free to name its columns differently,
return them in a different order, and hand back an ``int`` where our reference SQL
produced a ``numeric``. All of those are the *same answer* and must compare equal.

So before comparing we put both sides through the same normalization, stripping away
the three differences that are cosmetic (README, "the sharp edges"):

1. **Column names don't matter, values do.** We drop the keys and keep each row's
   *values*. We then sort the values within a row, so a row is matched by the *set*
   of values it carries, not by which column each sat in — the agent selecting
   ``total, name`` instead of ``name, total`` is still the same row.
2. **Numeric type and precision don't matter.** ``int``, ``float`` and ``Decimal``
   all collapse to a float rounded to a fixed number of decimals, so ``5`` == ``5.0``
   and ``0.9315`` == ``0.93150001`` (a ratio the model computed a hair differently).
3. **Row order usually doesn't matter** — but sometimes it's the whole point ("top 3",
   "highest first"). The caller passes ``order_sensitive`` per question: ``True``
   compares the rows as an ordered list, ``False`` as a multiset (order ignored).
"""

from collections import Counter
from decimal import Decimal
from typing import Any

# Ratios and averages never come back bit-identical across two different queries, so
# we compare numbers only to this many decimal places. Four is plenty for a scrap rate
# or a yield (0.0393) while still catching a genuinely wrong value.
_ROUND_DP = 4

Row = dict[str, Any]


def _normalize_value(value: Any) -> Any:
    """Collapse a single cell to a canonical form that ignores cosmetic differences.

    Numbers (but not booleans, which are technically ``int`` in Python) become a
    float rounded to ``_ROUND_DP``; everything else is compared by its string form,
    which folds away e.g. a ``datetime`` vs its ISO text without special-casing types.
    ``None`` stays ``None`` so a genuine null never collides with the text ``"None"``.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float, Decimal)):
        return round(float(value), _ROUND_DP)
    return str(value)


def _normalize_row(row: Row) -> tuple[Any, ...]:
    """Reduce a row to a key-independent, column-order-independent signature.

    We keep the values (not the column names) and sort them, so two rows carrying the
    same values match regardless of which columns they came from or in what order.
    """
    return tuple(sorted((_normalize_value(v) for v in row.values()), key=str))


def results_match(
    expected: list[Row], actual: list[Row], order_sensitive: bool
) -> bool:
    """Return whether ``actual`` is the same answer as ``expected``.

    Both sides are normalized (see module docstring); then compared as an ordered
    list when ``order_sensitive`` is set, or as a multiset (``Counter``) — same rows,
    same counts, any order — when it isn't.
    """
    expected_rows = [_normalize_row(r) for r in expected]
    actual_rows = [_normalize_row(r) for r in actual]

    if order_sensitive:
        return expected_rows == actual_rows
    return Counter(expected_rows) == Counter(actual_rows)
