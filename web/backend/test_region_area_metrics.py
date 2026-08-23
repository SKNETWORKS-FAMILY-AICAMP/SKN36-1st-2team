"""행정구역 면적 매핑·인구밀도·인구 성장 지속성 테스트."""

from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd
from streamlit.testing.v1 import AppTest

from etl.region_area import map_region_areas, select_administrative_version
from .scoring import calculate_supplemental_metrics, shift_year_month


def base_vehicle_rows():
    return [
        {
            "region_code": code,
            "date": shift_year_month("2026-07", offset),
            "truck_count": base + offset,
            "total_vehicle_count": 1_000,
        }
        for code, base in (("A", 100), ("B", 200))
        for offset in range(-36, 1)
    ]


def base_commercial_rows():
    return [
        {
            "region_code": code,
            "date": shift_year_month("2026-07", offset),
            "commercial_truck_count": base + offset,
        }
        for code, base in (("A", 40), ("B", 80))
        for offset in range(-36, 1)
    ]


def population_history(a_increasing=True):
    rows = []
    for code in ("A", "B"):
        for offset in range(-36, 1):
            if code == "A":
                population = 1_000 + offset if a_increasing else 1_000
            else:
                population = 2_000
            rows.append({
                "region_code": code,
                "date": shift_year_month("2026-07", offset),
                "population": population,
            })
    return rows


def calculate(area_rows, history=None, current=None):
    return calculate_supplemental_metrics(
        target_date="2026-07",
        vehicle_rows=base_vehicle_rows(),
        commercial_rows=base_commercial_rows(),
        current_population_rows=(
            [{"region_code": "A", "population": 1_000},
             {"region_code": "B", "population": 2_000}]
            if current is None else current
        ),
        previous_population_rows=[
            {"region_code": "A", "population": 988},
            {"region_code": "B", "population": 2_000},
        ],
        population_history_rows=population_history() if history is None else history,
        area_rows=area_rows,
    )


class RegionAreaMappingTest(unittest.TestCase):
    def test_selects_latest_version_not_after_target(self):
        self.assertEqual(
            select_administrative_version(
                "2026-07", ["20260201", "20260401", "20260701", "20261001"]
            ),
            "20260701",
        )

    def test_square_meters_are_converted_to_square_kilometers(self):
        regions = pd.DataFrame([{"region_id": "A", "region_name": "서울특별시 중구"}])
        sgg = pd.DataFrame([{
            "sidonm": "서울특별시", "sggnm": "중구", "area": 12_500_000.0,
        }])
        mapped = map_region_areas(regions, sgg)
        self.assertEqual(mapped.iloc[0]["area_km2"], 12.5)

    def test_same_district_name_in_other_province_is_not_mapped(self):
        regions = pd.DataFrame([{"region_id": "A", "region_name": "서울특별시 중구"}])
        sgg = pd.DataFrame([{
            "sidonm": "부산광역시", "sggnm": "중구", "area": 10_000_000.0,
        }])
        mapped = map_region_areas(regions, sgg)
        self.assertTrue(pd.isna(mapped.iloc[0]["area_km2"]))

    def test_unmatched_region_is_none(self):
        regions = pd.DataFrame([{"region_id": "A", "region_name": "가상도 없는군"}])
        sgg = pd.DataFrame([{
            "sidonm": "서울특별시", "sggnm": "중구", "area": 10_000_000.0,
        }])
        self.assertTrue(pd.isna(map_region_areas(regions, sgg).iloc[0]["area_km2"]))


class PopulationSupplementalMetricTest(unittest.TestCase):
    def test_population_density_and_national_percentile(self):
        result = calculate([
            {"region_code": "A", "area_km2": 10.0},
            {"region_code": "B", "area_km2": 40.0},
        ])
        self.assertEqual(result["A"]["raw"]["population_density"], 100.0)
        self.assertEqual(result["B"]["raw"]["population_density"], 50.0)
        self.assertEqual(
            result["A"]["normalized"]["population_density_score"], 100.0
        )

    def test_nonpositive_or_missing_area_returns_none(self):
        for area in (0, None, -1):
            with self.subTest(area=area):
                result = calculate([{"region_code": "A", "area_km2": area}])
                self.assertIsNone(result["A"]["raw"]["population_density"])

    def test_missing_population_returns_none(self):
        result = calculate(
            [{"region_code": "A", "area_km2": 10.0}],
            current=[{"region_code": "B", "population": 2_000}],
        )
        self.assertIsNone(result["A"]["raw"]["population_density"])

    def test_population_persistence_and_national_percentile(self):
        result = calculate([{"region_code": "A", "area_km2": 10.0},
                            {"region_code": "B", "area_km2": 10.0}])
        self.assertEqual(result["A"]["raw"]["population_trend_persistence"], 100.0)
        self.assertEqual(result["B"]["raw"]["population_trend_persistence"], 0.0)
        self.assertEqual(
            result["A"]["normalized"]["population_trend_persistence_score"],
            100.0,
        )

    def test_no_comparable_population_history_returns_none(self):
        result = calculate(
            [{"region_code": "A", "area_km2": 10.0}],
            history=[{"region_code": "A", "date": "2026-07", "population": 1_000}],
        )
        self.assertIsNone(result["A"]["raw"]["population_trend_persistence"])


class StreamlitSupplementalDisplayTest(unittest.TestCase):
    def test_population_persistence_and_density_cards_render(self):
        page = Path(__file__).resolve().parents[2] / "pages" / "data_search.py"
        app = AppTest.from_file(page, default_timeout=120).run()
        app.selectbox[0].set_value("서울특별시")
        app.run(timeout=120)
        app.selectbox[1].set_value("강남구")
        app.run(timeout=120)
        self.assertEqual(len(app.exception), 0)
        markdown = "\n".join(str(element.value) for element in app.markdown)
        self.assertIn("인구 성장 지속성", markdown)
        self.assertIn("인구 밀도", markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
