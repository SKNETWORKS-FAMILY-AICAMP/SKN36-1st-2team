"""물류 거점 점수 계산 로직의 단위 테스트와 실제 DB 통합 테스트."""

from __future__ import annotations

import unittest
import re

from .db import MySQLDB
from .scoring import (
    calculate_growth,
    calculate_logistics_score,
    percentile_scores,
    shift_year_month,
    validate_weight,
)
from .services import get_logistics_score


def make_vehicle_rows() -> list[dict]:
    """손으로 예상 점수를 계산할 수 있는 A·B·C 지역의 가상 차량 데이터."""
    values = {
        # 지역: 기준월, 3개월 전, 6개월 전, 12개월 전
        "A": (200, 150, 100, 100),
        "B": (300, 250, 200, 200),
        "C": (100, 100, 100, 100),
    }
    totals = {"A": 400, "B": 1000, "C": 100}
    months = ("2026-07", "2026-04", "2026-01", "2025-07")

    return [
        {
            "region_code": code,
            "date": month,
            "truck_count": truck_count,
            "total_vehicle_count": totals[code],
        }
        for code, counts in values.items()
        for month, truck_count in zip(months, counts)
    ]


def make_population_rows() -> list[dict]:
    return [
        {"region_code": "A", "date": "2026-07", "population": 1000},
        {"region_code": "B", "date": "2026-07", "population": 2000},
        {"region_code": "C", "date": "2026-07", "population": 3000},
    ]


class ScoringHelperTest(unittest.TestCase):
    """DB를 사용하지 않고 증가율·백분위·입력 검증 함수를 확인한다."""

    def test_growth(self) -> None:
        self.assertAlmostEqual(calculate_growth(120, 100), 20.0)
        self.assertAlmostEqual(calculate_growth(80, 100), -20.0)
        self.assertEqual(calculate_growth(100, 100), 0.0)

    def test_growth_missing_or_zero_denominator(self) -> None:
        self.assertIsNone(calculate_growth(None, 100))
        self.assertIsNone(calculate_growth(100, None))
        self.assertIsNone(calculate_growth(10, 0))

    def test_percentile_ties_and_none(self) -> None:
        scores = percentile_scores({"A": 10, "B": 20, "C": 20, "D": 30, "E": None})
        self.assertEqual(scores["A"], 0.0)
        self.assertEqual(scores["B"], 50.0)
        self.assertEqual(scores["C"], 50.0)
        self.assertEqual(scores["D"], 100.0)
        self.assertIsNone(scores["E"])

    def test_percentile_all_tied(self) -> None:
        self.assertEqual(
            percentile_scores({"A": 10, "B": 10, "C": 10}),
            {"A": 50.0, "B": 50.0, "C": 50.0},
        )

    def test_percentile_single_value_current_policy(self) -> None:
        # 현재 scoring.py의 정책은 모집단이 한 지역뿐이면 0점이다.
        self.assertEqual(percentile_scores({"A": 10}), {"A": 0.0})

    def test_shift_year_month_across_year(self) -> None:
        self.assertEqual(shift_year_month("2026-01", -3), "2025-10")
        self.assertEqual(shift_year_month("2025-12", 2), "2026-02")

    def test_invalid_date(self) -> None:
        for value in ("2026-13", "2026-7", "", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                shift_year_month(value, 0)

    def test_valid_weights(self) -> None:
        self.assertEqual(validate_weight(1, "weight"), 1.0)
        self.assertEqual(validate_weight(2.5, "weight"), 2.5)
        self.assertEqual(validate_weight(5, "weight"), 5.0)

    def test_invalid_weights(self) -> None:
        for value in (0, 6, "3", None, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_weight(value, "weight")


class LogisticsScoreFormulaTest(unittest.TestCase):
    """고정된 가상 데이터로 산업성·성장성·수요성·최종점수를 정확히 검증한다."""

    def setUp(self) -> None:
        self.result = calculate_logistics_score(
            region={"region_code": "A", "region_name": "가상 지역 A"},
            target_date="2026-07",
            vehicle_rows=make_vehicle_rows(),
            population_rows=make_population_rows(),
        )

    def test_raw_metrics(self) -> None:
        self.assertEqual(self.result["raw"]["truck_count"], 200)
        self.assertEqual(self.result["raw"]["total_vehicle_count"], 400)
        self.assertEqual(self.result["raw"]["truck_ratio"], 50.0)
        self.assertEqual(self.result["raw"]["truck_per_10000"], 2000.0)
        self.assertEqual(self.result["raw"]["yoy_growth"], 100.0)
        self.assertAlmostEqual(self.result["raw"]["acceleration"], -16.6667, places=4)

    def test_normalized_metrics(self) -> None:
        # A는 화물차 수 중간, 비중 중간, YoY 최고, 가속도 최저, 인구 최저다.
        self.assertEqual(self.result["normalized"]["truck_count_score"], 50.0)
        self.assertEqual(self.result["normalized"]["truck_ratio_score"], 50.0)
        self.assertEqual(self.result["normalized"]["yoy_score"], 100.0)
        self.assertEqual(self.result["normalized"]["acceleration_score"], 0.0)
        self.assertEqual(self.result["normalized"]["population_score"], 0.0)

    def test_component_score_formulas(self) -> None:
        # 산업성 = 50*0.7 + 50*0.3 = 50
        # 성장성 = 100*0.7 + 0*0.3 = 70
        # 수요성 = 인구 백분위 = 0
        self.assertEqual(self.result["scores"]["industry"], 50.0)
        self.assertEqual(self.result["scores"]["growth"], 70.0)
        self.assertEqual(self.result["scores"]["demand"], 0.0)

    def test_default_weight_total(self) -> None:
        self.assertEqual(
            self.result["normalized_weights"],
            {"industry": 0.3333, "growth": 0.3333, "demand": 0.3333},
        )
        self.assertEqual(self.result["scores"]["total"], 40.0)
        self.assertTrue(self.result["score_available"])
        self.assertIsNone(self.result["unavailable_reason"])

    def test_custom_weight_total(self) -> None:
        result = calculate_logistics_score(
            region={"region_code": "A", "region_name": "가상 지역 A"},
            target_date="2026-07",
            vehicle_rows=make_vehicle_rows(),
            population_rows=make_population_rows(),
            industry_weight=5,
            growth_weight=3,
            demand_weight=2,
        )
        # 50*0.5 + 70*0.3 + 0*0.2 = 46
        self.assertEqual(result["normalized_weights"], {"industry": 0.5, "growth": 0.3, "demand": 0.2})
        self.assertEqual(result["scores"]["total"], 46.0)

    def test_missing_population_makes_total_unavailable(self) -> None:
        rows = [row for row in make_population_rows() if row["region_code"] != "A"]
        result = calculate_logistics_score(
            region={"region_code": "A", "region_name": "가상 지역 A"},
            target_date="2026-07",
            vehicle_rows=make_vehicle_rows(),
            population_rows=rows,
        )
        self.assertFalse(result["score_available"])
        self.assertIsNone(result["raw"]["truck_per_10000"])
        self.assertIsNone(result["scores"]["demand"])
        self.assertIsNone(result["scores"]["total"])
        self.assertIn("인구 데이터", result["unavailable_reason"])

    def test_zero_population_makes_truck_per_10000_unavailable(self) -> None:
        rows = make_population_rows()
        rows[0]["population"] = 0
        result = calculate_logistics_score(
            region={"region_code": "A", "region_name": "가상 지역 A"},
            target_date="2026-07",
            vehicle_rows=make_vehicle_rows(),
            population_rows=rows,
        )

        self.assertIsNone(result["raw"]["truck_per_10000"])

    def test_missing_truck_count_makes_truck_per_10000_unavailable(self) -> None:
        rows = [
            row
            for row in make_vehicle_rows()
            if not (row["region_code"] == "A" and row["date"] == "2026-07")
        ]
        result = calculate_logistics_score(
            region={"region_code": "A", "region_name": "가상 지역 A"},
            target_date="2026-07",
            vehicle_rows=rows,
            population_rows=make_population_rows(),
        )

        self.assertIsNone(result["raw"]["truck_per_10000"])

    def test_missing_history_makes_growth_unavailable(self) -> None:
        rows = [
            row
            for row in make_vehicle_rows()
            if not (row["region_code"] == "A" and row["date"] == "2025-07")
        ]
        result = calculate_logistics_score(
            region={"region_code": "A", "region_name": "가상 지역 A"},
            target_date="2026-07",
            vehicle_rows=rows,
            population_rows=make_population_rows(),
        )
        self.assertFalse(result["score_available"])
        self.assertIsNone(result["scores"]["growth"])
        self.assertIsNone(result["scores"]["total"])
        self.assertIn("화물차 이력", result["unavailable_reason"])


class LogisticsScoreIntegrationTest(unittest.TestCase):
    """프로젝트의 실제 MySQL 데이터와 서비스 연결을 확인한다."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.db = MySQLDB.from_env()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_2026_07_normal_region(self) -> None:
        result = get_logistics_score(self.db, "R0001", "2026-07")
        self.assertIsNotNone(result)
        self.assertTrue(result["score_available"])
        self.assertGreaterEqual(result["scores"]["total"], 0.0)
        self.assertLessEqual(result["scores"]["total"], 100.0)

    def test_2024_07_first_expected_full_history(self) -> None:
        result = get_logistics_score(self.db, "R0001", "2024-07")
        self.assertIsNotNone(result)
        self.assertTrue(result["score_available"])

    def test_2023_07_has_insufficient_growth_history(self) -> None:
        result = get_logistics_score(self.db, "R0001", "2023-07")
        self.assertIsNotNone(result)
        self.assertFalse(result["score_available"])
        self.assertIsNone(result["scores"]["growth"])
        self.assertIsNone(result["scores"]["total"])

    def test_custom_weight_result_matches_formula(self) -> None:
        result = get_logistics_score(self.db, "R0001", "2026-07", 5, 3, 2)
        expected = (
            result["scores"]["industry"] * 0.5
            + result["scores"]["growth"] * 0.3
            + result["scores"]["demand"] * 0.2
        )
        self.assertAlmostEqual(result["scores"]["total"], expected, places=3)

    def test_unknown_region(self) -> None:
        self.assertIsNone(get_logistics_score(self.db, "R9999", "2026-07"))

    def test_weight_out_of_range(self) -> None:
        with self.assertRaises(ValueError):
            get_logistics_score(self.db, "R0001", "2026-07", industry_weight=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)

# from web.backend import MySQLDB, get_logistics_score

# db = MySQLDB.from_env()

# result = get_logistics_score(
#     db,
#     "R0167",
#     "2026-07",
# )

# print(result)
