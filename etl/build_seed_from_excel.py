"""Build the initial seed directly from validated Excel transformations.

Use this only when a local MySQL instance is unavailable. The normal refresh path is
load_data.py followed by export_seed.py, which exports the verified database.
"""

from __future__ import annotations

from datetime import date, datetime

from load_data import (
    ROOT, build_categories, build_date_dimension, read_population, read_region_master,
    read_vehicle, transform_vehicle_to_long, validate_population_region_mapping,
    validate_vehicle_region_mapping,
)


OUTPUT = ROOT / "database" / "02_seed.sql"
BATCH_SIZE = 1_000


def sql_value(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (date, datetime)):
        return f"'{value:%Y-%m-%d}'"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace("\\", "\\\\").replace("'", "''")
    return f"'{escaped}'"


def append_frame(lines, table, frame, columns):
    rows = list(frame[columns].itertuples(index=False, name=None))
    column_sql = ", ".join(f"`{column}`" for column in columns)
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start:start + BATCH_SIZE]
        values = ["(" + ",".join(sql_value(value) for value in row) + ")" for row in batch]
        lines.append(f"INSERT INTO `{table}` ({column_sql}) VALUES\n" + ",\n".join(values) + ";")
    lines.append("")


def main() -> None:
    regions = read_region_master()
    population = read_population()
    vehicle_source = read_vehicle()
    people = validate_population_region_mapping(population, regions)
    vehicle_mapped = validate_vehicle_region_mapping(vehicle_source, regions)
    dates = build_date_dimension(people, vehicle_mapped)
    categories = build_categories()
    vehicle = transform_vehicle_to_long(vehicle_mapped, categories)
    people = people[["region_id", "date_ym", "people_population"]]

    lines = [
        "-- Generated from validated Excel sources by etl/build_seed_from_excel.py.",
        "SET NAMES utf8mb4;", "SET FOREIGN_KEY_CHECKS=0;", "START TRANSACTION;",
        "DELETE FROM vehicle;", "DELETE FROM people;", "DELETE FROM category;",
        "DELETE FROM `date`;", "DELETE FROM region;", "",
    ]
    append_frame(lines, "region", regions, ["region_id", "region_name"])
    append_frame(lines, "date", dates, ["date_ym", "date_half", "date_quarter", "date_year", "date_month"])
    append_frame(lines, "category", categories, ["category_id", "category_main", "category_sub"])
    append_frame(lines, "people", people, ["region_id", "date_ym", "people_population"])
    append_frame(lines, "vehicle", vehicle, ["category_id", "region_id", "date_ym", "vehicle_count"])
    lines.extend(["COMMIT;", "SET FOREIGN_KEY_CHECKS=1;", ""])
    OUTPUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"생성 완료: {OUTPUT}")
    print(f"region={len(regions):,}, date={len(dates):,}, category={len(categories):,}, people={len(people):,}, vehicle={len(vehicle):,}")


if __name__ == "__main__":
    main()
