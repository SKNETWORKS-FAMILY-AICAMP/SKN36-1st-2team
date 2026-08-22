"""전국 물류 거점 랭킹 서비스 테스트."""

from __future__ import annotations

import unittest
from unittest.mock import ANY, Mock, patch

from .services import get_logistics_ranking


def make_regions(include_missing: bool = False) -> list[dict]:
    rows = [
        {"region_code": "A", "region_name": "가상 지역 A"},
        {"region_code": "B", "region_name": "가상 지역 B"},
        {"region_code": "C", "region_name": "가상 지역 C"},
    ]
    if include_missing:
        rows.append({"region_code": "D", "region_name": "데이터 부족 지역"})
    return rows


def make_vehicle_rows() -> list[dict]:
    values = {
        "A": (200, 150, 100, 100),
        "B": (300, 250, 200, 200),
        "C": (100, 100, 100, 100),
    }
    totals = {"A": 400, "B": 1_000, "C": 100}
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
        {"region_code": "A", "date": "2026-07", "population": 1_000},
        {"region_code": "B", "date": "2026-07", "population": 2_000},
        {"region_code": "C", "date": "2026-07", "population": 3_000},
    ]


class LogisticsRankingTest(unittest.TestCase):
    """고정된 전국 원본으로 순위·가중치·조회 횟수를 검증한다."""

    def get_ranking(
        self,
        industry_weight: int | float = 3,
        growth_weight: int | float = 3,
        demand_weight: int | float = 3,
        limit: int = 10,
        include_missing: bool = False,
    ) -> tuple[list[dict], Mock, Mock, Mock]:
        with (
            patch(
                "web.backend.services.get_regions",
                return_value=make_regions(include_missing),
            ) as region_query,
            patch(
                "web.backend.services.get_national_vehicle_metrics",
                return_value=make_vehicle_rows(),
            ) as vehicle_query,
            patch(
                "web.backend.services.get_national_population",
                return_value=make_population_rows(),
            ) as population_query,
        ):
            result = get_logistics_ranking(
                Mock(),
                "2026-07",
                industry_weight,
                growth_weight,
                demand_weight,
                limit,
            )
        return result, region_query, vehicle_query, population_query

    def test_ranking_order_rank_limit_and_shape(self) -> None:
        result, region_query, vehicle_query, population_query = self.get_ranking(
            limit=2
        )

        self.assertEqual(len(result), 2)
        self.assertEqual([row["rank"] for row in result], [1, 2])
        self.assertTrue(
            all(
                result[index]["scores"]["total"]
                >= result[index + 1]["scores"]["total"]
                for index in range(len(result) - 1)
            )
        )
        self.assertEqual(
            set(result[0]["scores"]),
            {"industry", "growth", "demand", "total"},
        )
        self.assertIn("truck_count", result[0]["raw"])
        self.assertIn("population", result[0]["raw"])
        region_query.assert_called_once_with(ANY)
        vehicle_query.assert_called_once()
        population_query.assert_called_once_with(ANY, "2026-07")

    def test_percentage_weights_change_scores_and_ranking(self) -> None:
        industry_result, *_ = self.get_ranking(80, 10, 10)
        demand_result, *_ = self.get_ranking(10, 10, 80)

        self.assertEqual(industry_result[0]["region_code"], "B")
        self.assertEqual(demand_result[0]["region_code"], "C")
        self.assertNotEqual(
            industry_result[0]["scores"]["total"],
            demand_result[0]["scores"]["total"],
        )

    def test_tied_scores_use_region_code_as_secondary_order(self) -> None:
        result, *_ = self.get_ranking(15, 65, 20)

        self.assertEqual(result[0]["scores"]["total"], result[1]["scores"]["total"])
        self.assertEqual(
            [result[0]["region_code"], result[1]["region_code"]],
            ["A", "B"],
        )

    def test_default_limit_returns_at_most_ten(self) -> None:
        result, *_ = self.get_ranking()

        self.assertLessEqual(len(result), 10)

    def test_missing_region_data_is_excluded_without_error(self) -> None:
        result, *_ = self.get_ranking(include_missing=True)

        self.assertNotIn("D", {row["region_code"] for row in result})
        self.assertEqual(len(result), 3)

    def test_invalid_limit_fails_before_queries(self) -> None:
        for limit in (0, -1, True, 10.0, "10"):
            with self.subTest(limit=limit):
                db = Mock()
                with self.assertRaises(ValueError):
                    get_logistics_ranking(db, "2026-07", limit=limit)
                db.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
