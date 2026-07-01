"""Result-set comparison — the heart of execution-accuracy grading.

The whole eval rests on one question: do two result sets *mean the same thing*?
Not "are the two SQL strings equal" (they never are), and not even "are the two
lists of rows byte-identical" — the agent is free to name its columns differently,
return them in a different order, and hand back an ``int`` where our reference SQL
produced a ``numeric``. All of those are the *same answer* and must compare equal.

So before comparing we put both sides through the same normalization, stripping away
the differences that are cosmetic (README, "the sharp edges"):

1. **Column names don't matter, values do.** We drop the keys and keep each row's
   *values*, so a row is matched by the values it carries, not by which column each
   sat in — the agent selecting ``total, name`` instead of ``name, total`` is still
   the same row.
2. **Numeric type and precision don't matter.** ``int``, ``float`` and ``Decimal``
   all collapse to a float rounded to a fixed number of decimals, so ``5`` == ``5.0``
   and ``0.9315`` == ``0.93150001`` (a ratio the model computed a hair differently).
3. **Row order usually doesn't matter** — but sometimes it's the whole point ("top 3",
   "highest first"). The caller passes ``order_sensitive`` per question: ``True``
   compares the rows as an ordered list, ``False`` as a multiset (order ignored).
4. **Extra columns don't matter.** The expected result lists the values a correct
   answer *must* contain; the agent is free to return more (a ratio question often
   comes back with the numerator and denominator alongside the ratio). So a row
   *matches* when the expected values are a sub-multiset of the actual row's values —
   a missing or wrong value still fails, but a helpful extra column doesn't.
"""

from collections import Counter
from decimal import Decimal
from typing import Any

# Ratios and averages never come back bit-identical across two different queries, so
# we compare numbers only to this many decimal places. Four is plenty for a scrap rate
# or a yield (0.0393) while still catching a genuinely wrong value.
_ROUND_DP = 4

type Row = dict[str, Any]


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


def _normalize_row(row: Row) -> Counter:
    """Reduce a row to a key-independent multiset of its normalized values.

    Dropping the keys makes the comparison ignore column names and column order; a
    ``Counter`` (multiset) is the natural shape for "these values, with these counts",
    which is what the containment check below needs.
    """
    return Counter(_normalize_value(v) for v in row.values())


def _row_contains(actual: Counter, expected: Counter) -> bool:
    """True when every expected value is present in the actual row (extra ones allowed)."""
    return expected <= actual


def results_match(
    expected: list[Row], actual: list[Row], order_sensitive: bool
) -> bool:
    """Return whether ``actual`` is the same answer as ``expected``.

    Row counts must match; then each expected row must be *contained in* an actual row
    (sub-multiset — see docstring rule 4). With ``order_sensitive`` the rows are paired
    positionally; otherwise each expected row is matched to a distinct actual row in
    any order.
    """
    expected_rows = [_normalize_row(r) for r in expected]
    actual_rows = [_normalize_row(r) for r in actual]

    if len(expected_rows) != len(actual_rows):
        return False

    if order_sensitive:
        return all(_row_contains(a, e) for a, e in zip(actual_rows, expected_rows))

    unmatched = list(actual_rows)
    for expected_row in expected_rows:
        for i, actual_row in enumerate(unmatched):
            if _row_contains(actual_row, expected_row):
                unmatched.pop(i)
                break
        else:
            return False
    return True
