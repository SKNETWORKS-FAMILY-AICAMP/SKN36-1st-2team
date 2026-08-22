"""메인 요약의 전국 화물차 전년 동월 대비 증가율 단위 테스트."""

from __future__ import annotations

import unittest
from unittest.mock import ANY, Mock, call, patch

from .services import get_dashboard_summary


class DashboardSummaryTest(unittest.TestCase):
    """DB query 결과를 고정해 요약 조합과 증가율 계산을 확인한다."""

    def get_summary(
        self,
        current_count: int | None,
        previous_count: int | None,
    ) -> tuple[dict, Mock]:
        freight_results = [
            {"date": "2026-07", "vehicle_count": current_count}
            if current_count is not None
            else None,
            {"date": "2025-07", "vehicle_count": previous_count}
            if previous_count is not None
            else None,
        ]
        freight_query = Mock(side_effect=freight_results)

        with (
            patch(
                "web.backend.services.get_region_count",
                return_value={"region_count": 250},
            ),
            patch(
                "web.backend.services.get_national_freight_count",
                freight_query,
            ),
        ):
            result = get_dashboard_summary(Mock(), "2026-07")

        return result, freight_query

    def test_positive_year_over_year_growth_and_existing_values(self) -> None:
        result, freight_query = self.get_summary(3_612_480, 3_527_813)

        self.assertEqual(result["date"], "2026-07")
        self.assertEqual(result["previous_year_month"], "2025-07")
        self.assertEqual(result["region_count"], 250)
        self.assertEqual(result["national_freight_count"], 3_612_480)
        self.assertEqual(result["year_over_year_growth_rate"], 2.4)
        self.assertEqual(
            freight_query.call_args_list,
            [call(ANY, "2026-07"), call(ANY, "2025-07")],
        )

    def test_negative_year_over_year_growth(self) -> None:
        result, _ = self.get_summary(900, 1_000)

        self.assertEqual(result["year_over_year_growth_rate"], -10.0)

    def test_missing_previous_year_data(self) -> None:
        result, _ = self.get_summary(1_000, None)

        self.assertIsNone(result["year_over_year_growth_rate"])

    def test_zero_previous_year_count(self) -> None:
        result, _ = self.get_summary(1_000, 0)

        self.assertIsNone(result["year_over_year_growth_rate"])

    def test_missing_current_data_keeps_existing_rule(self) -> None:
        result, _ = self.get_summary(None, 1_000)

        self.assertIsNone(result["national_freight_count"])
        self.assertIsNone(result["year_over_year_growth_rate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
