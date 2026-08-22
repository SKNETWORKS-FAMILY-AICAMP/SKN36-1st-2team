"""전국 시도 지도와 시도별 지역 목록 query 테스트."""

from __future__ import annotations

import unittest
from datetime import date

from .db import MySQLDB
from .queries import get_province_freight_counts, get_regions_by_province
from .queries import get_national_freight_count, get_national_vehicle_metrics


class FakeDB:
    """조회 결과를 반환하고 SQL과 바인딩 파라미터를 기록한다."""

    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def fetch_all(
        self,
        sql: str,
        params: tuple[object, ...] = (),
    ) -> list[dict]:
        self.calls.append((sql, params))
        return [row.copy() for row in self.rows]


class RegionMapQueryTest(unittest.TestCase):
    """시도 집계 SQL과 정확한 시도명 바인딩을 DB 없이 확인한다."""

    def test_province_counts_group_all_regions_and_filter_freight(self) -> None:
        db = FakeDB(
            [{"province_name": "경기도", "vehicle_count": 81_215}]
        )

        rows = get_province_freight_counts(db, "2026-07")

        self.assertEqual(rows[0]["vehicle_count"], 81_215)
        sql, params = db.calls[0]
        self.assertIn("SUM(v.vehicle_count)", sql)
        self.assertIn("GROUP BY SUBSTRING_INDEX", sql)
        self.assertIn("JOIN region", sql)
        self.assertEqual(params, (date(2026, 7, 1), "화물"))

    def test_regions_by_province_uses_exact_bound_name(self) -> None:
        db = FakeDB(
            [{"region_code": "R0001", "region_name": "경기도 가평군"}]
        )

        rows = get_regions_by_province(db, " 경기도 ")

        self.assertEqual(rows[0]["region_name"], "경기도 가평군")
        sql, params = db.calls[0]
        self.assertIn("SUBSTRING_INDEX(region_name, ' ', 1) = %s", sql)
        self.assertNotIn("LIKE", sql)
        self.assertEqual(params, ("경기도",))

    def test_invalid_empty_province_name(self) -> None:
        for province_name in ("", "   ", None):
            with self.subTest(province_name=province_name), self.assertRaises(ValueError):
                get_regions_by_province(FakeDB([]), province_name)


class RegionMapIntegrationTest(unittest.TestCase):
    """실제 적재 데이터의 시도 합계와 시군구 소속을 확인한다."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.db = MySQLDB.from_env()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_province_counts_equal_national_freight_total(self) -> None:
        province_rows = get_province_freight_counts(self.db, "2026-07")
        national = get_national_freight_count(self.db, "2026-07")

        self.assertGreater(len(province_rows), 1)
        self.assertEqual(
            sum(row["vehicle_count"] for row in province_rows),
            national["vehicle_count"],
        )

    def test_province_count_sums_every_region_in_province(self) -> None:
        province_rows = get_province_freight_counts(self.db, "2026-07")
        gyeonggi_total = next(
            row["vehicle_count"]
            for row in province_rows
            if row["province_name"] == "경기도"
        )
        regions = get_regions_by_province(self.db, "경기도")
        region_codes = {row["region_code"] for row in regions}
        metrics = get_national_vehicle_metrics(self.db, ["2026-07"])
        expected = sum(
            row["truck_count"]
            for row in metrics
            if row["region_code"] in region_codes
        )

        self.assertGreater(len(regions), 1)
        self.assertEqual(gyeonggi_total, expected)

    def test_regions_by_province_contains_only_selected_province(self) -> None:
        rows = get_regions_by_province(self.db, "경기도")

        self.assertTrue(rows)
        self.assertTrue(
            all(row["region_name"].startswith("경기도 ") for row in rows)
        )
        self.assertFalse(
            any(row["region_name"].startswith("부산광역시 ") for row in rows)
        )

    def test_unknown_province_returns_empty_list(self) -> None:
        self.assertEqual(get_regions_by_province(self.db, "존재하지않는시도"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
