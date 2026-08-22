"""전국 화물차 현황 query와 service의 단위 테스트."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import ANY, Mock, patch

from .queries import (
    get_national_freight_history,
    get_national_freight_usage_counts,
    get_top_region_freight_counts,
)
from .services import (
    get_national_vehicle_trend,
    get_national_vehicle_usage,
    get_top_regions_by_freight_count,
)


class FakeDB:
    """조회 결과를 반환하고 전달받은 SQL과 파라미터를 기록한다."""

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


class NationalDashboardQueryTest(unittest.TestCase):
    """날짜·화물 조건과 안전한 LIMIT 바인딩을 확인한다."""

    def test_usage_query_filters_target_month_and_freight(self) -> None:
        db = FakeDB(
            [
                {
                    "date": "2026-07",
                    "category_usage": "자가용",
                    "vehicle_count": 100,
                }
            ]
        )

        rows = get_national_freight_usage_counts(db, "2026-07")

        self.assertEqual(rows[0]["vehicle_count"], 100)
        sql, params = db.calls[0]
        self.assertIn("c.category_sub AS category_usage", sql)
        self.assertEqual(params, (date(2026, 7, 1), "화물"))

    def test_trend_query_applies_period_and_orders_ascending(self) -> None:
        db = FakeDB(
            [
                {"date": "2023-07", "vehicle_count": 100},
                {"date": "2023-08", "vehicle_count": 110},
            ]
        )

        rows = get_national_freight_history(db, "2023-07", "2026-07")

        self.assertEqual(len(rows), 2)
        sql, params = db.calls[0]
        self.assertIn("v.date_ym >= %s", sql)
        self.assertIn("v.date_ym <= %s", sql)
        self.assertIn("ORDER BY v.date_ym", sql)
        self.assertEqual(
            params,
            ("화물", date(2023, 7, 1), date(2026, 7, 1)),
        )

    def test_top_query_filters_month_and_binds_limit(self) -> None:
        db = FakeDB(
            [
                {
                    "region_code": "R0001",
                    "region_name": "가상 지역",
                    "vehicle_count": 100,
                }
            ]
        )

        rows = get_top_region_freight_counts(db, "2026-07")

        self.assertEqual(len(rows), 1)
        sql, params = db.calls[0]
        self.assertIn("JOIN region", sql)
        self.assertIn("ORDER BY vehicle_count DESC", sql)
        self.assertIn("LIMIT %s", sql)
        self.assertEqual(params, (date(2026, 7, 1), "화물", 10))

    def test_top_query_rejects_unsafe_limit(self) -> None:
        for limit in (0, -1, True, 10.0, "10"):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                get_top_region_freight_counts(FakeDB([]), "2026-07", limit)


class NationalDashboardServiceTest(unittest.TestCase):
    """query 결과가 대시보드용 반환 구조로 가공되는지 확인한다."""

    @patch("web.backend.services.get_national_freight_usage_counts")
    def test_usage_counts_ratios_and_order(self, usage_query: Mock) -> None:
        usage_query.return_value = [
            {
                "date": "2026-07",
                "category_usage": "관용",
                "vehicle_count": 124,
            },
            {
                "date": "2026-07",
                "category_usage": "자가용",
                "vehicle_count": 564,
            },
            {
                "date": "2026-07",
                "category_usage": "영업용",
                "vehicle_count": 312,
            },
        ]

        result = get_national_vehicle_usage(Mock(), "2026-07")

        self.assertEqual(result["date"], "2026-07")
        self.assertEqual(result["total"], 1_000)
        self.assertEqual(
            [row["usage"] for row in result["usage"]],
            ["자가용", "영업용", "관용"],
        )
        self.assertEqual(
            [row["ratio"] for row in result["usage"]],
            [56.4, 31.2, 12.4],
        )
        self.assertAlmostEqual(
            sum(row["ratio"] for row in result["usage"]),
            100.0,
            places=1,
        )
        usage_query.assert_called_once_with(ANY, "2026-07")

    @patch("web.backend.services.get_national_freight_history")
    def test_trend_returns_multiple_months_in_query_order(
        self,
        history_query: Mock,
    ) -> None:
        history_query.return_value = [
            {"date": "2023-07", "vehicle_count": 100},
            {"date": "2023-08", "vehicle_count": 110},
        ]

        result = get_national_vehicle_trend(
            Mock(),
            start_date="2023-07",
            end_date="2026-07",
        )

        self.assertEqual(
            result,
            [
                {"date": "2023-07", "count": 100},
                {"date": "2023-08", "count": 110},
            ],
        )
        self.assertEqual(
            [row["date"] for row in result],
            sorted(row["date"] for row in result),
        )
        history_query.assert_called_once_with(
            ANY,
            "2023-07",
            "2026-07",
        )

    @patch("web.backend.services.get_top_region_freight_counts")
    def test_top_regions_shape_limit_and_descending_order(
        self,
        top_query: Mock,
    ) -> None:
        top_query.return_value = [
            {
                "region_code": f"R{index:04d}",
                "region_name": f"가상 지역 {index}",
                "vehicle_count": 1_100 - index,
            }
            for index in range(1, 11)
        ]

        result = get_top_regions_by_freight_count(Mock(), "2026-07")

        self.assertLessEqual(len(result), 10)
        self.assertTrue(
            all(
                result[index]["count"] >= result[index + 1]["count"]
                for index in range(9)
            )
        )
        self.assertEqual(
            set(result[0]),
            {"region_code", "region_name", "count"},
        )
        top_query.assert_called_once_with(ANY, "2026-07", 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
