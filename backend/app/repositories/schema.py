"""Schema description handed to the LLM so it can write SQL against our tables.

Phase 1 keeps this as a hardcoded constant: the schema is settled and changes only
through migrations we control, so a literal is simpler and cheaper than querying the
database on every request. In Phase 1.5 (the agent's ``get_schema()`` tool) this is
replaced by live introspection of ``information_schema`` from the repository — the
function signature here is chosen to make that swap a drop-in.

The text is written for a reader (the model), not a parser: it lists each table, its
columns with types and keys, the foreign keys that connect them, and — crucially — the
allowed values of the constrained columns, so the model filters on real values instead
of guessing.
"""

_SCHEMA_TEXT = """\
Manufacturing database — discrete-manufacturing factory making industrial
electrical / electromechanical products. PostgreSQL. All tables are read-only.

Table products — items the factory makes.
  id        integer  primary key
  name      text     not null, unique
  category  text     not null

Table production_lines — lines / cells on the shop floor.
  id        integer  primary key
  name      text     not null, unique
  location  text     not null

Table machines — machines belonging to a production line.
  id        integer  primary key
  line_id   integer  not null, foreign key -> production_lines(id)
  name      text     not null
  type      text     not null

Table shifts — work shifts.
  id          integer  primary key
  name        text     not null, unique  (e.g. Morning, Evening, Night)
  start_time  time     not null
  end_time    time     not null

Table work_orders — a batch/lot of a product scheduled on a line for a shift.
  id                integer  primary key
  product_id        integer  not null, foreign key -> products(id)
  line_id           integer  not null, foreign key -> production_lines(id)
  shift_id          integer  not null, foreign key -> shifts(id)
  planned_quantity  integer  not null  (> 0)
  start_date        date     not null
  status            text     not null  (one of: 'planned', 'in_progress', 'completed')

Table production_output — what a work order actually produced.
  id                 integer      primary key
  work_order_id      integer      not null, foreign key -> work_orders(id)
  produced_quantity  integer      not null  (>= 0)
  scrap_quantity     integer      not null  (>= 0, and <= produced_quantity)
  recorded_at        timestamptz  not null

Table downtime_events — recorded stops on the shop floor.
  id                integer      primary key
  line_id           integer      not null, foreign key -> production_lines(id)
  machine_id        integer      nullable, foreign key -> machines(id)
  shift_id          integer      not null, foreign key -> shifts(id)
  reason_code       text         not null  (one of: 'setup_changeover', 'breakdown',
                                             'material_shortage', 'planned_maintenance')
  is_planned        boolean      not null
  duration_minutes  integer      not null  (> 0)
  occurred_at       timestamptz  not null

Table quality_inspections — QC checks tied to a work order.
  id                  integer      primary key
  work_order_id       integer      not null, foreign key -> work_orders(id)
  inspected_quantity  integer      not null  (> 0)
  passed_quantity     integer      not null  (>= 0, and <= inspected_quantity)
  inspected_at        timestamptz  not null

Table defects — defects found in a quality inspection.
  id             integer  primary key
  inspection_id  integer  not null, foreign key -> quality_inspections(id)
  defect_type    text     not null
  severity       text     not null  (one of: 'minor', 'major', 'critical')
  quantity       integer  not null  (> 0)
"""


def get_schema_text() -> str:
    """Return the database schema as human-readable text for the LLM prompt."""
    return _SCHEMA_TEXT
