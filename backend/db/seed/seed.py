"""Synthetic data seed generator for the manufacturing database.

Run from ``backend/``::

    poetry run poe seed        # == python -m db.seed.seed

Wipes every table and regenerates a ~12-month dataset. Uses the sync psycopg2
driver on purpose: a one-off batch script gains nothing from async (no
concurrency to overlap), unlike the live request path which is async.

Determinism: a fixed RANDOM_SEED fixes the data's *shape* (counts, quantities,
category mix) run to run. REFERENCE_DATE is today, so only the calendar window
slides forward over time, keeping "last month/quarter" questions meaningful;
eval stays valid because it compares against reference SQL executed live.
"""

import random
from datetime import date, datetime, time, timedelta, timezone

import psycopg2

from app.core.config import get_settings

RANDOM_SEED = 42

# Anchor the dataset to "today" so "last month/quarter" questions stay meaningful
# as time passes. With the fixed RANDOM_SEED the data's shape is identical run to
# run; only the calendar window slides forward. Eval stays valid because it
# compares against reference SQL executed live (not frozen numbers).
REFERENCE_DATE = date.today()
WINDOW_DAYS = 365

# Upper bound for any generated timestamp: a manufacturing event must not be
# dated in the future. Recent work orders / downtime can otherwise land past now.
NOW = datetime.now(timezone.utc)

WORK_ORDER_COUNT = 1200
DOWNTIME_EVENT_COUNT = 450
PLANNED_QUANTITIES = [50, 100, 150, 200, 250, 300, 400, 500]

DEFECT_TYPES = [
    "loose_terminal",
    "cracked_casing",
    "wiring_error",
    "paint_defect",
    "calibration_error",
    "missing_label",
]
SEVERITIES = ["minor", "major", "critical"]
SEVERITY_WEIGHTS = [6, 3, 1]

REASON_CODES = ["breakdown", "setup_changeover", "material_shortage", "planned_maintenance"]
REASON_WEIGHTS = [4, 4, 2, 3]
DURATION_RANGES = {
    "breakdown": (30, 300),
    "setup_changeover": (10, 60),
    "material_shortage": (20, 180),
    "planned_maintenance": (60, 240),
}

# Fraction of downtime events that carry an operator note; the rest stay NULL
# (not every stop is annotated in real life, and it exercises the Phase 2
# embedding pipeline's handling of missing text).
NOTE_PROBABILITY = 0.85

# Free-text operator notes, grouped by reason_code so the wording stays coherent
# with the structured column. Deliberately varied and full of synonyms
# ("oil leak" / "hydraulic fluid" / "seepage") so Phase 2 semantic search can
# beat a brittle keyword LIKE, which the coarse reason_code enum cannot express.
NOTE_TEMPLATES: dict[str, list[str]] = {
    "breakdown": [
        "Lost hydraulic pressure; found a leaking seal and replaced the O-ring.",
        "Oil seepage around the main cylinder, topped up the fluid and tightened the fittings.",
        "Hydraulic fluid leaking onto the floor, isolated the unit until the hose was swapped.",
        "Motor overheated and tripped the thermal overload; let it cool and reset the breaker.",
        "Electrical fault on the control board, swapped the PLC module.",
        "Bearing seized on the spindle; replaced the bearing and re-greased the shaft.",
        "Coolant pump failed, no flow to the tool, pump replaced.",
        "Drive belt snapped mid-run, fitted a new belt and re-tensioned it.",
        "Sensor gave false readings, recalibrated and cleaned the probe.",
        "Pneumatic actuator stuck, air line was blocked, cleared and re-seated it.",
    ],
    "setup_changeover": [
        "Changed tooling for the next product batch.",
        "Retooled the die for a larger panel size.",
        "Swapped fixtures to switch to a different contactor model.",
        "Recalibrated torque settings after the product change.",
        "Loaded a new program and ran a first-off check for the incoming order.",
    ],
    "material_shortage": [
        "Held up waiting on a copper busbar delivery from the warehouse.",
        "Ran out of terminal blocks, paused until stock arrived.",
        "Insulation sheets not delivered on time, the line idled.",
        "Missing coil wire, waited for replenishment from stores.",
        "Short on labels, packaging held until supply came in.",
    ],
    "planned_maintenance": [
        "Scheduled lubrication and general inspection.",
        "Quarterly preventive maintenance as per the plan.",
        "Replaced worn carbon brushes on schedule.",
        "Routine firmware update and self-test.",
        "Planned filter change and cleaning.",
    ],
}


def _note_for(reason_code: str) -> str | None:
    """Pick a realistic operator note for a downtime event, or None (unannotated)."""
    if random.random() > NOTE_PROBABILITY:
        return None
    return random.choice(NOTE_TEMPLATES[reason_code])

PRODUCTS: list[tuple[str, str]] = [
    ("Type C Contactor", "Contactors"),
    ("Type K Contactor", "Contactors"),
    ("400A Switchgear Panel", "Switchgear"),
    ("630A Switchgear Panel", "Switchgear"),
    ("MV Distribution Transformer", "Transformers"),
    ("Dry-Type Transformer", "Transformers"),
    ("3-Phase Induction Motor", "Motors"),
    ("Servo Control Unit", "Control Units"),
]

PRODUCTION_LINES: list[tuple[str, str]] = [
    ("Assembly Line A", "Hall 1"),
    ("Assembly Line B", "Hall 1"),
    ("Winding Cell 1", "Hall 2"),
    ("Panel Build Line", "Hall 3"),
    ("Testing & Packaging", "Hall 4"),
]

MACHINES_BY_LINE: dict[str, list[tuple[str, str]]] = {
    "Assembly Line A": [
        ("Press A1", "press"),
        ("Assembly Station A1", "assembly"),
        ("Tester A1", "tester"),
    ],
    "Assembly Line B": [
        ("Press B1", "press"),
        ("Assembly Station B1", "assembly"),
        ("Tester B1", "tester"),
    ],
    "Winding Cell 1": [
        ("Winder 1", "winder"),
        ("Winder 2", "winder"),
        ("Coil Tester 1", "tester"),
    ],
    "Panel Build Line": [
        ("Panel Frame Jig", "assembly"),
        ("Busbar Press", "press"),
        ("Panel Tester", "tester"),
    ],
    "Testing & Packaging": [
        ("HiPot Tester", "tester"),
        ("Packaging Robot", "packaging"),
    ],
}

SHIFTS: list[tuple[str, time, time]] = [
    ("Morning", time(6, 0), time(14, 0)),
    ("Evening", time(14, 0), time(22, 0)),
    ("Night", time(22, 0), time(6, 0)),
]


def reset_tables(cur) -> None:
    """Empty every table and reset identity counters, so re-runs are idempotent.

    CASCADE follows foreign keys, so listing the tables in any order is safe;
    RESTART IDENTITY makes generated ids start again from 1 each run.
    """
    cur.execute(
        """
        TRUNCATE
            defects,
            quality_inspections,
            downtime_events,
            production_output,
            work_orders,
            machines,
            shifts,
            production_lines,
            products
        RESTART IDENTITY CASCADE;
        """
    )


def seed_products(cur) -> list[int]:
    """Insert the product catalog; return the generated ids."""
    ids: list[int] = []
    for name, category in PRODUCTS:
        cur.execute(
            "INSERT INTO products (name, category) VALUES (%s, %s) RETURNING id;",
            (name, category),
        )
        ids.append(cur.fetchone()[0])
    return ids


def seed_production_lines(cur) -> dict[str, int]:
    """Insert production lines; return a name -> id map (machines need it)."""
    line_ids: dict[str, int] = {}
    for name, location in PRODUCTION_LINES:
        cur.execute(
            "INSERT INTO production_lines (name, location) VALUES (%s, %s) RETURNING id;",
            (name, location),
        )
        line_ids[name] = cur.fetchone()[0]
    return line_ids


def seed_machines(cur, line_ids: dict[str, int]) -> dict[int, list[int]]:
    """Insert machines under their lines; return a line_id -> [machine_id] map.

    Grouping by line matters downstream: a downtime event's machine must belong
    to the same line, so we keep machines indexed by their line.
    """
    machines_by_line: dict[int, list[int]] = {}
    for line_name, machines in MACHINES_BY_LINE.items():
        line_id = line_ids[line_name]
        machines_by_line[line_id] = []
        for name, machine_type in machines:
            cur.execute(
                "INSERT INTO machines (line_id, name, type) VALUES (%s, %s, %s) RETURNING id;",
                (line_id, name, machine_type),
            )
            machines_by_line[line_id].append(cur.fetchone()[0])
    return machines_by_line


def seed_shifts(cur) -> list[int]:
    """Insert the three work shifts; return the generated ids."""
    shift_ids: list[int] = []
    for name, start_time, end_time in SHIFTS:
        cur.execute(
            "INSERT INTO shifts (name, start_time, end_time) VALUES (%s, %s, %s) RETURNING id;",
            (name, start_time, end_time),
        )
        shift_ids.append(cur.fetchone()[0])
    return shift_ids


def _status_for(days_ago: int) -> str:
    """Older work orders are completed; recent ones may still be running/planned."""
    if days_ago >= 14:
        return "completed"
    if days_ago >= 3:
        return random.choice(["completed", "in_progress"])
    return random.choice(["in_progress", "planned"])


def _split_count(total: int, parts: int) -> list[int]:
    """Split a positive int into ``parts`` positive ints that sum back to it."""
    parts = max(1, min(parts, total))
    base, remainder = divmod(total, parts)
    return [base + (1 if i < remainder else 0) for i in range(parts)]


def _timestamp_on(day: date, day_offset: int = 0) -> datetime:
    """A timezone-aware timestamp during working hours on ``day`` (+ offset days)."""
    base = datetime(
        day.year, day.month, day.day,
        random.randint(6, 20), random.randint(0, 59),
        tzinfo=timezone.utc,
    )
    return min(base + timedelta(days=day_offset), NOW)


def _random_timestamp_within_window() -> datetime:
    """A timezone-aware timestamp at a random point in the last WINDOW_DAYS."""
    day = REFERENCE_DATE - timedelta(days=random.randint(0, WINDOW_DAYS - 1))
    ts = datetime(
        day.year, day.month, day.day,
        random.randint(0, 23), random.randint(0, 59),
        tzinfo=timezone.utc,
    )
    return min(ts, NOW)


def seed_work_orders(
    cur, product_ids: list[int], line_ids: list[int], shift_ids: list[int]
) -> list[dict]:
    """Insert work orders (the plan); return dicts carrying the fields the
    production/quality step needs (id, planned_quantity, start_date, status).

    Built in two passes: generate all specs, sort them by start_date, then
    insert in date order so generated ids line up with chronology (as a real
    auto-incremented table would). Sorting work_orders cascades to their output
    and inspections, which are inserted per work order in this same order.
    """
    specs: list[dict] = []
    for _ in range(WORK_ORDER_COUNT):
        days_ago = random.randint(0, WINDOW_DAYS - 1)
        specs.append(
            {
                "product_id": random.choice(product_ids),
                "line_id": random.choice(line_ids),
                "shift_id": random.choice(shift_ids),
                "planned_quantity": random.choice(PLANNED_QUANTITIES),
                "start_date": REFERENCE_DATE - timedelta(days=days_ago),
                "status": _status_for(days_ago),
            }
        )
    specs.sort(key=lambda s: s["start_date"])

    work_orders: list[dict] = []
    for s in specs:
        cur.execute(
            "INSERT INTO work_orders "
            "(product_id, line_id, shift_id, planned_quantity, start_date, status) "
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;",
            (s["product_id"], s["line_id"], s["shift_id"],
             s["planned_quantity"], s["start_date"], s["status"]),
        )
        work_orders.append(
            {
                "id": cur.fetchone()[0],
                "planned_quantity": s["planned_quantity"],
                "start_date": s["start_date"],
                "status": s["status"],
            }
        )
    return work_orders


def seed_production_and_quality(cur, work_orders: list[dict]) -> tuple[int, int, int]:
    """For each producing work order: record output, then (for completed ones)
    a quality inspection and any defects. Enforces the consistency rules:
    scrap <= produced, passed <= inspected, defect quantities sum to failures."""
    output_count = inspection_count = defect_count = 0

    for wo in work_orders:
        if wo["status"] == "planned":
            continue  # nothing produced yet

        fraction = random.uniform(0.85, 1.05) if wo["status"] == "completed" else random.uniform(0.3, 0.7)
        total_produced = max(1, round(wo["planned_quantity"] * fraction))
        last_recorded_at = None
        for day_offset, produced in enumerate(_split_count(total_produced, random.randint(1, 3))):
            scrap = round(produced * random.uniform(0.0, 0.08))  # always <= produced
            recorded_at = _timestamp_on(wo["start_date"], day_offset)
            cur.execute(
                "INSERT INTO production_output "
                "(work_order_id, produced_quantity, scrap_quantity, recorded_at) "
                "VALUES (%s, %s, %s, %s);",
                (wo["id"], produced, scrap, recorded_at),
            )
            output_count += 1
            last_recorded_at = recorded_at

        if wo["status"] != "completed" or random.random() > 0.85:
            continue  # only most completed orders get inspected

        inspected = min(total_produced, max(1, round(total_produced * random.uniform(0.3, 1.0))))
        failed = min(inspected, round(inspected * random.uniform(0.0, 0.12)))
        passed = inspected - failed
        inspected_at = min(
            last_recorded_at + timedelta(days=random.randint(0, 3), hours=random.randint(1, 8)),
            NOW,
        )
        cur.execute(
            "INSERT INTO quality_inspections "
            "(work_order_id, inspected_quantity, passed_quantity, inspected_at) "
            "VALUES (%s, %s, %s, %s) RETURNING id;",
            (wo["id"], inspected, passed, inspected_at),
        )
        inspection_id = cur.fetchone()[0]
        inspection_count += 1

        if failed > 0:
            quantities = _split_count(failed, random.randint(1, 2))
            for defect_type, quantity in zip(random.sample(DEFECT_TYPES, k=len(quantities)), quantities):
                cur.execute(
                    "INSERT INTO defects (inspection_id, defect_type, severity, quantity) "
                    "VALUES (%s, %s, %s, %s);",
                    (
                        inspection_id,
                        defect_type,
                        random.choices(SEVERITIES, weights=SEVERITY_WEIGHTS)[0],
                        quantity,
                    ),
                )
                defect_count += 1

    return output_count, inspection_count, defect_count


def seed_downtime_events(cur, machines_by_line: dict[int, list[int]], shift_ids: list[int]) -> int:
    """Insert downtime events. machine_id is sometimes NULL (line-level stop);
    when set, it is a machine on that same line. is_planned stays coherent with
    reason_code (only planned_maintenance is planned)."""
    line_ids = list(machines_by_line.keys())
    specs: list[dict] = []
    for _ in range(DOWNTIME_EVENT_COUNT):
        line_id = random.choice(line_ids)
        machines_on_line = machines_by_line[line_id]
        machine_id = random.choice(machines_on_line) if machines_on_line and random.random() < 0.6 else None
        reason_code = random.choices(REASON_CODES, weights=REASON_WEIGHTS)[0]
        specs.append(
            {
                "line_id": line_id,
                "machine_id": machine_id,
                "shift_id": random.choice(shift_ids),
                "reason_code": reason_code,
                "is_planned": reason_code == "planned_maintenance",
                "duration_minutes": random.randint(*DURATION_RANGES[reason_code]),
                "occurred_at": _random_timestamp_within_window(),
                "notes": _note_for(reason_code),
            }
        )
    specs.sort(key=lambda s: s["occurred_at"])

    for s in specs:
        cur.execute(
            "INSERT INTO downtime_events "
            "(line_id, machine_id, shift_id, reason_code, is_planned, duration_minutes, occurred_at, notes) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
            (s["line_id"], s["machine_id"], s["shift_id"], s["reason_code"],
             s["is_planned"], s["duration_minutes"], s["occurred_at"], s["notes"]),
        )
    return DOWNTIME_EVENT_COUNT


def main() -> None:
    random.seed(RANDOM_SEED)
    settings = get_settings()
    conn = psycopg2.connect(settings.database_url)
    try:
        with conn:
            with conn.cursor() as cur:
                reset_tables(cur)
                product_ids = seed_products(cur)
                line_ids = seed_production_lines(cur)
                machines_by_line = seed_machines(cur, line_ids)
                shift_ids = seed_shifts(cur)
                work_orders = seed_work_orders(
                    cur, product_ids, list(line_ids.values()), shift_ids
                )
                output_count, inspection_count, defect_count = seed_production_and_quality(
                    cur, work_orders
                )
                downtime_count = seed_downtime_events(cur, machines_by_line, shift_ids)
        machine_count = sum(len(ids) for ids in machines_by_line.values())
        print(
            "Seeded:\n"
            f"  catalog : {len(product_ids)} products, {len(line_ids)} lines, "
            f"{machine_count} machines, {len(shift_ids)} shifts\n"
            f"  events  : {len(work_orders)} work_orders, {output_count} output, "
            f"{inspection_count} inspections, {defect_count} defects, "
            f"{downtime_count} downtime"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
