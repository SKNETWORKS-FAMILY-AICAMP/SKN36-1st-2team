"""폐지 지역이 원본에는 남고 ETL 적재 대상에서는 제외되는지 검증한다."""

from __future__ import annotations

import unittest

import pandas as pd

from etl.load_data import (
    EXCLUDED_REGION_IDS,
    VEHICLE_FILE,
    read_population,
    read_region_master,
    read_vehicle,
    validate_population_region_mapping,
)


class ObsoleteRegionFilterTest(unittest.TestCase):
    """R0167 재적재 방지와 기존 인구 매핑을 검증한다."""

    def test_source_file_is_preserved_but_region_master_excludes_r0167(self) -> None:
        source = pd.read_excel(VEHICLE_FILE, sheet_name="지역마스터", dtype={"분석지역ID": str})
        self.assertIn("R0167", set(source["분석지역ID"].str.strip()))
        filtered = read_region_master()
        self.assertTrue(EXCLUDED_REGION_IDS.isdisjoint(set(filtered["분석지역ID"])))
        self.assertEqual(len(source) - len(filtered), 1)

    def test_vehicle_source_excludes_all_r0167_months(self) -> None:
        source = pd.read_excel(VEHICLE_FILE, sheet_name="차량_연속분석", dtype={"분석지역ID": str})
        self.assertEqual(int((source["분석지역ID"].str.strip() == "R0167").sum()), 37)
        filtered = read_vehicle()
        self.assertNotIn("R0167", set(filtered["분석지역ID"]))
        self.assertEqual(len(source) - len(filtered), 37)

    def test_population_mapping_still_has_no_failures(self) -> None:
        regions = read_region_master()
        population = read_population()
        mapped = validate_population_region_mapping(population, regions)
        self.assertEqual(len(mapped), len(population))
        self.assertFalse(mapped["region_id"].isna().any())
        self.assertNotIn("R0167", set(mapped["region_id"]))


if __name__ == "__main__":
    unittest.main()
