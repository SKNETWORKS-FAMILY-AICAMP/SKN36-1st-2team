"""전국·시도·시군구 월별 화물차/인구 집계 서비스 테스트."""

from unittest import TestCase
from unittest.mock import Mock, patch

from .services import get_freight_per_population_trend


VEHICLES = [
    {"region_code": "R0001", "date": "2026-06", "truck_count": 90},
    {"region_code": "R0001", "date": "2026-07", "truck_count": 100},
    {"region_code": "R0002", "date": "2026-06", "truck_count": 270},
    {"region_code": "R0002", "date": "2026-07", "truck_count": 300},
    {"region_code": "R0003", "date": "2026-06", "truck_count": 180},
    {"region_code": "R0003", "date": "2026-07", "truck_count": 200},
]
POPULATIONS = [
    {"region_code": "R0001", "date": "2026-06", "population": 90},
    {"region_code": "R0001", "date": "2026-07", "population": 100},
    {"region_code": "R0002", "date": "2026-06", "population": 2610},
    {"region_code": "R0002", "date": "2026-07", "population": 2900},
    {"region_code": "R0003", "date": "2026-06", "population": 1800},
    {"region_code": "R0003", "date": "2026-07", "population": 2000},
]


class FreightPerPopulationTrendTest(TestCase):
    def setUp(self):
        self.db = Mock()
        self.vehicle_patch = patch(
            "web.backend.services.get_national_vehicle_metrics",
            return_value=VEHICLES,
        )
        self.population_patch = patch(
            "web.backend.services.get_national_population_history",
            return_value=POPULATIONS,
        )
        self.vehicle_patch.start()
        self.population_patch.start()
        self.addCleanup(self.vehicle_patch.stop)
        self.addCleanup(self.population_patch.stop)

    def test_national_uses_ratio_of_sums_and_sorts_oldest_first(self):
        result = get_freight_per_population_trend(self.db, "2026-06", "2026-07")

        self.assertEqual([row["date"] for row in result], ["2026-06", "2026-07"])
        self.assertEqual(result[-1]["truck_count"], 600)
        self.assertEqual(result[-1]["population"], 5000)
        self.assertAlmostEqual(result[-1]["truck_per_1000"], 120.0)

    @patch("web.backend.services.get_regions_by_province")
    def test_province_aggregates_only_its_region_codes(self, get_regions):
        get_regions.return_value = [
            {"region_code": "R0001"}, {"region_code": "R0002"},
        ]

        result = get_freight_per_population_trend(
            self.db, "2026-06", "2026-07", province_name="경기도"
        )

        self.assertEqual(result[-1]["truck_count"], 400)
        self.assertEqual(result[-1]["population"], 3000)
        self.assertAlmostEqual(result[-1]["truck_per_1000"], 400 / 3000 * 1000)
        # 지역별 비율의 단순 평균((1000 + 103.45...) / 2)과 다르다.
        simple_average = ((100 / 100 * 1000) + (300 / 2900 * 1000)) / 2
        self.assertNotAlmostEqual(result[-1]["truck_per_1000"], simple_average)

    @patch("web.backend.services.get_region")
    def test_region_keeps_existing_single_region_behavior(self, get_region):
        get_region.return_value = {"region_code": "R0002", "region_name": "경기도 테스트시"}

        result = get_freight_per_population_trend(
            self.db, "2026-06", "2026-07", region_code="R0002"
        )

        self.assertEqual(result[-1]["truck_count"], 300)
        self.assertEqual(result[-1]["population"], 2900)
        self.assertAlmostEqual(result[-1]["truck_per_1000"], 300 / 2900 * 1000)
        self.assertAlmostEqual(result[-1]["national_truck_per_1000"], 120.0)

    def test_missing_population_is_not_replaced_with_zero(self):
        with patch(
            "web.backend.services.get_national_population_history",
            return_value=[row for row in POPULATIONS if row["date"] == "2026-07"],
        ):
            result = get_freight_per_population_trend(
                self.db, "2026-06", "2026-07"
            )

        self.assertEqual([row["date"] for row in result], ["2026-07"])

