"""PDF 최종 지표 체계 회귀 테스트."""

from __future__ import annotations

import math
from pathlib import Path
import unittest

from .scoring import calculate_supplemental_metrics, shift_year_month


def rows_for(base: int, yearly_step: int, total: int, code: str) -> list[dict]:
    rows = []
    for offset in range(-36, 1):
        # 12개월마다 yearly_step만큼 증가하는 단순 시계열
        value = base + ((offset + 36) // 12) * yearly_step
        rows.append({
            "region_code": code,
            "date": shift_year_month("2026-07", offset),
            "truck_count": value,
            "total_vehicle_count": total,
        })
    return rows


class PdfMetricCalculationTest(unittest.TestCase):
    def calculate(self):
        vehicle = rows_for(100, 10, 1_000, "A") + rows_for(200, 5, 2_000, "B")
        commercial = [
            {
                "region_code": row["region_code"],
                "date": row["date"],
                "commercial_truck_count": row["truck_count"] // 2,
            }
            for row in vehicle
        ]
        population_history = [
            {
                "region_code": code,
                "date": shift_year_month("2026-07", offset),
                "population": population - 12 + offset + 36,
            }
            for code, population in (("A", 1_000), ("B", 2_000))
            for offset in range(-36, 1)
        ]
        return calculate_supplemental_metrics(
            "2026-07", vehicle, commercial,
            [{"region_code": "A", "population": 1_024}, {"region_code": "B", "population": 2_024}],
            [{"region_code": "A", "population": 1_012}, {"region_code": "B", "population": 2_012}],
            population_history,
            [{"region_code": "A", "area_km2": 10.0}, {"region_code": "B", "area_km2": 40.0}],
        )

    def test_acceleration_uses_current_previous_and_two_year_prior(self):
        raw = self.calculate()["A"]["raw"]
        current, previous, previous_2 = 130, 120, 110
        expected = ((current - previous) / previous - (previous - previous_2) / previous_2) * 100
        self.assertAlmostEqual(raw["acceleration"], expected, places=4)

    def test_stability_is_finite_and_percentiles_stay_in_range(self):
        result = self.calculate()
        for values in result.values():
            self.assertTrue(math.isfinite(values["raw"]["stability"]))
            for score in values["normalized"].values():
                if score is not None:
                    self.assertGreaterEqual(score, 0.0)
                    self.assertLessEqual(score, 100.0)

    def test_adjacent_population_is_explicitly_unavailable_without_adjacency(self):
        result = self.calculate()
        self.assertIsNone(result["A"]["raw"]["adjacent_population"])
        self.assertIsNone(result["A"]["normalized"]["adjacent_population_score"])


class MainRegionCountSourceTest(unittest.TestCase):
    def test_app_has_no_249_literal_and_uses_dashboard_region_count(self):
        app_source = (Path(__file__).resolve().parents[2] / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("249", app_source)
        self.assertIn('dashboard["region_count"]', app_source)
        self.assertIn("{region_count}", app_source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
