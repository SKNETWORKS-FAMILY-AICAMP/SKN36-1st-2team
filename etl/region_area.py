"""admdongkor 시군구 면적을 분석 region에 안전하게 매핑한다."""

from __future__ import annotations

import re
from typing import Iterable

import admdongkor as adk
import pandas as pd


AREA_ALIASES = {
    ("인천광역시", "서구통합권역"): [("인천광역시", "서해구"), ("인천광역시", "검단구")],
    ("인천광역시", "중구·동구통합권역"): [("인천광역시", "제물포구"), ("인천광역시", "영종구")],
    ("세종특별자치시", "세종특별자치시"): [("세종특별자치시", "세종시")],
    ("경기도", "부천시"): [
        ("경기도", "부천시원미구"), ("경기도", "부천시소사구"), ("경기도", "부천시오정구"),
    ],
    ("경기도", "화성시"): [
        ("경기도", "화성시만세구"), ("경기도", "화성시효행구"),
        ("경기도", "화성시병점구"), ("경기도", "화성시동탄구"),
    ],
}


def normalize_region_name(value: object) -> str:
    return re.sub(r"\s+", "", str(value)).strip()


def select_administrative_version(
    target_month: str,
    versions: Iterable[str] | None = None,
) -> str:
    """YYYY-MM 이하에서 사용할 수 있는 가장 최신 버전을 선택한다."""
    target = target_month.replace("-", "")
    if not re.fullmatch(r"\d{6}", target):
        raise ValueError("target_month는 YYYY-MM 형식이어야 합니다.")
    candidates = sorted(
        str(version) for version in (versions if versions is not None else adk.versions())
        if str(version)[:6] <= target
    )
    if not candidates:
        raise ValueError(f"{target_month} 이하의 admdongkor 버전이 없습니다.")
    return candidates[-1]


def load_sgg_areas(target_month: str) -> tuple[str, pd.DataFrame]:
    """선택 버전의 시군구명과 제공 면적(m²)을 읽는다."""
    version_key = select_administrative_version(target_month)
    frame = adk.get(version_key, "sgg")
    required = ["sggcd", "sggnm", "sidonm", "area"]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"admdongkor 시군구 필수 컬럼 누락: {sorted(missing)}")
    return version_key, frame[required].copy()


def map_region_areas(regions: pd.DataFrame, sgg_areas: pd.DataFrame) -> pd.DataFrame:
    """시도+시군구명과 최소 alias로 region별 km² 면적을 매핑한다."""
    required_regions = {"region_id", "region_name"}
    if not required_regions.issubset(regions.columns):
        raise ValueError(f"region 필수 컬럼 누락: {sorted(required_regions - set(regions.columns))}")
    required_sgg = {"sidonm", "sggnm", "area"}
    if not required_sgg.issubset(sgg_areas.columns):
        raise ValueError(f"시군구 필수 컬럼 누락: {sorted(required_sgg - set(sgg_areas.columns))}")

    area_lookup: dict[tuple[str, str], float] = {}
    for row in sgg_areas.itertuples(index=False):
        key = (normalize_region_name(row.sidonm), normalize_region_name(row.sggnm))
        if key in area_lookup:
            raise ValueError(f"중복 시군구 면적 key: {key}")
        area_lookup[key] = float(row.area) / 1_000_000.0

    aliases = {
        (normalize_region_name(sido), normalize_region_name(sgg)): [
            (normalize_region_name(alias_sido), normalize_region_name(alias_sgg))
            for alias_sido, alias_sgg in values
        ]
        for (sido, sgg), values in AREA_ALIASES.items()
    }
    result = regions.copy()
    mapped_areas: list[float | None] = []
    for row in result.itertuples(index=False):
        sido, separator, sgg = str(row.region_name).partition(" ")
        key = (normalize_region_name(sido), normalize_region_name(sgg if separator else sido))
        if key in area_lookup:
            mapped_areas.append(area_lookup[key])
            continue
        alias_keys = aliases.get(key)
        if not alias_keys or any(alias_key not in area_lookup for alias_key in alias_keys):
            mapped_areas.append(None)
            continue
        mapped_areas.append(sum(area_lookup[alias_key] for alias_key in alias_keys))
    result["area_km2"] = pd.Series(mapped_areas, index=result.index, dtype="Float64")
    return result


def attach_region_areas(
    regions: pd.DataFrame,
    target_month: str,
) -> tuple[pd.DataFrame, str | None]:
    """admdongkor 실패 시 기존 ETL을 막지 않고 nullable 면적으로 반환한다."""
    try:
        version_key, sgg_areas = load_sgg_areas(target_month)
        return map_region_areas(regions, sgg_areas), version_key
    except Exception as error:
        fallback = regions.copy()
        fallback["area_km2"] = pd.Series([None] * len(fallback), dtype="Float64")
        print(f"경고: admdongkor 면적 매핑 실패, area_km2=NULL 유지: {error}")
        return fallback, None
