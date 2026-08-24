"""화면 상세용 추가 지표의 query·계산·service 테스트."""

from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import ANY, Mock, patch

from .queries import get_national_commercial_freight_counts
from .scoring import (
    calculate_ratio,
    calculate_supplemental_metrics,
    calculate_trend_persistence,
    shift_year_month,
)
from .services import get_supplemental_logistics_metrics


class FakeDB:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def fetch_all(self, sql, params=()):
        self.calls.append((sql, params))
        return [row.copy() for row in self.rows]


def make_vehicle_rows():
    rows = []
    for code, multiplier, total in (("A", 1, 300), ("B", 2, 700)):
        for offset in range(-36, 1):
            rows.append({
                "region_code": code,
                "date": shift_year_month("2026-07", offset),
                "truck_count": (100 + offset) * multiplier,
                "total_vehicle_count": total,
            })
    return rows


def make_commercial_rows():
    return [
        {
            "region_code": code,
            "date": shift_year_month("2026-07", offset),
            "commercial_truck_count": (40 + offset) * multiplier,
        }
        for code, multiplier in (("A", 1), ("B", 2))
        for offset in range(-36, 1)
    ]


class SupplementalQueryTest(unittest.TestCase):
    def test_commercial_query_filters_freight_and_commercial_usage(self):
        db = FakeDB([{
            "region_code": "R0001", "date": "2026-07",
            "commercial_truck_count": 123,
        }])
        rows = get_national_commercial_freight_counts(db, ["2026-07", "2025-07"])
        self.assertEqual(rows[0]["commercial_truck_count"], 123)
        sql, params = db.calls[0]
        self.assertIn("c.category_main = %s", sql)
        self.assertIn("c.category_sub = %s", sql)
        self.assertEqual(
            params,
            (date(2025, 7, 1), date(2026, 7, 1), "화물", "영업용"),
        )

    def test_empty_months_skip_query(self):
        db = FakeDB([])
        self.assertEqual(get_national_commercial_freight_counts(db, []), [])
        self.assertEqual(db.calls, [])


class SupplementalCalculationTest(unittest.TestCase):
    def calculate(self, vehicle_rows=None, commercial_rows=None,
                  current_population=None, previous_population=None):
        return calculate_supplemental_metrics(
            "2026-07",
            make_vehicle_rows() if vehicle_rows is None else vehicle_rows,
            make_commercial_rows() if commercial_rows is None else commercial_rows,
            ([{"region_code": "A", "population": 1_100},
              {"region_code": "B", "population": 2_000}]
             if current_population is None else current_population),
            ([{"region_code": "A", "population": 1_000},
              {"region_code": "B", "population": 2_000}]
             if previous_population is None else previous_population),
        )

    def test_normal_values_and_national_percentile(self):
        result = self.calculate()
        raw = result["A"]["raw"]
        self.assertGreater(raw["location_quotient"], 1.0)
        self.assertAlmostEqual(raw["commercial_truck_share"], 40.0)
        self.assertEqual(raw["trend_persistence"], 1.0)
        self.assertEqual(raw["commercial_conversion_rate"], 1.0)
        self.assertEqual(raw["population_yoy_growth"], 10.0)
        self.assertEqual(
            result["A"]["normalized"]["location_quotient_score"], 100.0
        )
        self.assertEqual(
            result["B"]["normalized"]["location_quotient_score"], 0.0
        )

    def test_zero_denominator_is_none(self):
        self.assertIsNone(calculate_ratio(10, 0))
        rows = make_vehicle_rows()
        for row in rows:
            if row["region_code"] == "A" and row["date"] == "2025-07":
                row["truck_count"] = row["truck_count"] + 12
        self.assertIsNone(
            self.calculate(vehicle_rows=rows)["A"]["raw"]["commercial_conversion_rate"]
        )

    def test_negative_denominator_is_calculated(self):
        vehicle_rows = make_vehicle_rows()
        commercial_rows = make_commercial_rows()
        for row in vehicle_rows:
            if row["region_code"] == "A" and row["date"] == "2026-07":
                row["truck_count"] = 50
            elif row["region_code"] == "A" and row["date"] == "2025-07":
                row["truck_count"] = 100
        for row in commercial_rows:
            if row["region_code"] == "A" and row["date"] == "2026-07":
                row["commercial_truck_count"] = 30
            elif row["region_code"] == "A" and row["date"] == "2025-07":
                row["commercial_truck_count"] = 40
        raw = self.calculate(
            vehicle_rows=vehicle_rows,
            commercial_rows=commercial_rows,
        )["A"]["raw"]
        self.assertEqual(raw["commercial_conversion_rate"], 0.2)

    def test_missing_history_makes_persistence_none(self):
        history = {"2026-07": 100}
        self.assertIsNone(calculate_trend_persistence(history, "2026-07"))
        rows = [row for row in make_vehicle_rows()
                if not (row["region_code"] == "A" and row["date"] == "2023-07")]
        self.assertIsNone(
            self.calculate(vehicle_rows=rows)["A"]["raw"]["trend_persistence"]
        )

    def test_missing_previous_population_is_none(self):
        result = self.calculate(previous_population=[{"region_code": "B", "population": 2_000}])
        self.assertIsNone(result["A"]["raw"]["population_yoy_growth"])

    def test_missing_commercial_data_is_none(self):
        rows = [row for row in make_commercial_rows() if row["region_code"] != "A"]
        raw = self.calculate(commercial_rows=rows)["A"]["raw"]
        self.assertIsNone(raw["commercial_truck_share"])
        self.assertIsNone(raw["commercial_conversion_rate"])


class SupplementalServiceTest(unittest.TestCase):
    @patch("web.backend.services.get_region_areas")
    @patch("web.backend.services.get_national_population_history")
    @patch("web.backend.services.get_national_population")
    @patch("web.backend.services.get_national_commercial_freight_counts")
    @patch("web.backend.services.get_national_vehicle_metrics")
    def test_service_reuses_queries_and_returns_screen_shape(
        self, vehicle_query, commercial_query, population_query,
        population_history_query, area_query,
    ):
        vehicle_query.return_value = make_vehicle_rows()
        commercial_query.return_value = make_commercial_rows()
        population_query.side_effect = [
            [{"region_code": "A", "population": 1_100},
             {"region_code": "B", "population": 2_000}],
            [{"region_code": "A", "population": 1_000},
             {"region_code": "B", "population": 2_000}],
        ]
        population_history_query.return_value = []
        area_query.return_value = []
        result = get_supplemental_logistics_metrics(Mock(), "2026-07")
        self.assertEqual(len(result), 2)
        self.assertIn("location_quotient", result[0]["raw"])
        self.assertIn("location_quotient_score", result[0]["normalized"])
        vehicle_query.assert_called_once()
        commercial_query.assert_called_once()
        self.assertEqual(population_query.call_count, 2)
        population_query.assert_any_call(ANY, "2026-07")
        population_query.assert_any_call(ANY, "2025-07")


if __name__ == "__main__":
    unittest.main(verbosity=2)
