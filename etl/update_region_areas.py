"""기존 MySQL region 테이블에 admdongkor 면적을 갱신한다."""

from __future__ import annotations

import pandas as pd

from load_data import connect
from region_area import attach_region_areas


TARGET_MONTH = "2026-07"


def main() -> None:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT COUNT(*) FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='region'
                  AND COLUMN_NAME='area_km2'"""
            )
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """ALTER TABLE region
                    ADD COLUMN area_km2 DECIMAL(14,4) NULL
                    COMMENT 'admdongkor 시군구 면적(km²)' AFTER region_name"""
                )
            cursor.execute("SELECT region_id, region_name FROM region ORDER BY region_id")
            regions = pd.DataFrame(cursor.fetchall(), columns=["region_id", "region_name"])
        mapped, version_key = attach_region_areas(regions, TARGET_MONTH)
        if version_key is None:
            connection.rollback()
            raise RuntimeError("admdongkor 호출 실패로 면적 갱신을 적용하지 않았습니다.")
        with connection.cursor() as cursor:
            cursor.executemany(
                "UPDATE region SET area_km2=%s WHERE region_id=%s",
                [
                    (None if pd.isna(row.area_km2) else float(row.area_km2), row.region_id)
                    for row in mapped.itertuples(index=False)
                ],
            )
        connection.commit()
        failures = mapped[mapped["area_km2"].isna()]["region_name"].tolist()
        print(f"version_key={version_key}")
        print(f"region={len(mapped)}, mapped={len(mapped)-len(failures)}, failed={len(failures)}")
        if failures:
            print("면적 매핑 실패 지역:", failures)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
