-- Sanity-check queries for the seeded data.
-- Run any of these against the local DB to eyeball realism, e.g.:
--   docker compose exec db psql -U app -d manufacturing -f /dev/stdin < db/sanity_checks.sql
-- or paste them one at a time into pgAdmin. They progress from simple aggregates
-- to multi-table JOIN chains over the manufacturing schema.


-- 1. Aggregate over one table (no JOIN, no GROUP BY): overall scrap rate.
--    Expect a low single-digit percentage (seed scraps 0-8% per batch).
SELECT
    SUM(produced_quantity) AS produced,
    SUM(scrap_quantity)    AS scrap,
    round(100.0 * SUM(scrap_quantity) / SUM(produced_quantity), 2) AS scrap_pct
FROM production_output;


-- 2. GROUP BY on one table: defect units per defect type.
--    Defect types are seeded uniformly (only severity is weighted), so occurrences
--    come out fairly even; total_units varies from the random per-defect quantity.
SELECT
    defect_type,
    COUNT(*)       AS occurrences,
    SUM(quantity)  AS total_units
FROM defects
GROUP BY defect_type
ORDER BY total_units DESC;


-- 3. First JOIN (two tables): each machine with its line's human-readable name.
--    The FK machines.line_id is turned into the line name from production_lines.
SELECT
    m.name AS machine,
    m.type,
    l.name AS line,
    l.location
FROM machines AS m
JOIN production_lines AS l ON m.line_id = l.id
ORDER BY l.name, m.name;


-- 4. JOIN + GROUP BY: total downtime minutes per line (catalog name + event sum).
SELECT
    l.name                  AS line,
    COUNT(*)                AS event_count,
    SUM(d.duration_minutes) AS total_minutes
FROM downtime_events AS d
JOIN production_lines AS l ON d.line_id = l.id
GROUP BY l.name
ORDER BY total_minutes DESC;


-- 5. JOIN + WHERE (boolean + date) + GROUP BY: the headline question shape --
--    unplanned downtime minutes per line over the last 30 days.
SELECT
    l.name                  AS line,
    SUM(d.duration_minutes) AS unplanned_minutes
FROM downtime_events AS d
JOIN production_lines AS l ON d.line_id = l.id
WHERE d.is_planned = false
  AND d.occurred_at >= now() - interval '30 days'
GROUP BY l.name
ORDER BY unplanned_minutes DESC;


-- 6. Multi-hop JOIN chain (four tables): defect units per product.
--    Walks defects -> quality_inspections -> work_orders -> products, the chain
--    that makes quality "hang off" production.
SELECT
    p.name        AS product,
    SUM(df.quantity) AS defect_units
FROM defects AS df
JOIN quality_inspections AS qi ON df.inspection_id = qi.id
JOIN work_orders         AS wo ON qi.work_order_id = wo.id
JOIN products            AS p  ON wo.product_id = p.id
GROUP BY p.name
ORDER BY defect_units DESC;
