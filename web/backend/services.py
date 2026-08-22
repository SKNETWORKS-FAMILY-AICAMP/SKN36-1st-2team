# 여러 query 결과를 Streamlit 화면용 구조로 조합

from __future__ import annotations

from typing import Any

from .db import MySQLDB
from .queries import (
    get_national_freight_count,
    get_population,
    get_population_history,
    get_region,
    get_region_count,
    get_vehicle_category_counts,
    get_vehicle_data,
    get_vehicle_history,
)


def get_dashboard_summary(db: MySQLDB, year_month: str) -> dict[str, Any]:
    """메인 화면의 지역 수와 특정 월 전국 화물차 합계를 한 dict로 반환한다."""
    # 서로 다른 SQL 결과를 각각 조회한 뒤 Streamlit metric에서 바로 쓸 수 있게 합친다.
    region_result = get_region_count(db)
    freight_result = get_national_freight_count(db, year_month)
    return {
        "date": year_month,
        "region_count": region_result["region_count"],
        # 해당 월 데이터가 없으면 화면이 이를 구분할 수 있도록 None을 유지한다.
        "national_freight_count": (
            freight_result["vehicle_count"] if freight_result is not None else None
        ),
    }


def get_region_detail(
    db: MySQLDB,
    region_code: str,
    year_month: str,
) -> dict[str, Any]:
    """선택 지역·월의 지역, 차량, 카테고리별 차량, 인구를 한 dict로 반환한다."""
    # 일부 데이터가 없어도 단건 None, 다건 [] 규칙을 유지해 화면 전체가 중단되지 않게 한다.
    region = get_region(db, region_code)
    vehicle = get_vehicle_data(db, region_code, year_month)
    vehicle_categories = get_vehicle_category_counts(db, region_code, year_month)
    population = get_population(db, region_code, year_month)

    # 지역 정보는 상위 region에 있으므로 차량 영역에는 날짜와 합계만 남긴다.
    vehicle_summary = None
    if vehicle is not None:
        vehicle_summary = {
            "date": vehicle["date"],
            "vehicle_count": vehicle["vehicle_count"],
        }

    # 카테고리 목록은 그대로 DataFrame으로 만들 수 있는 list[dict] 형태로 정리한다.
    category_summaries = [
        {
            "category_id": row["category_id"],
            "category_main": row["category_main"],
            "category_sub": row["category_sub"],
            "vehicle_count": row["vehicle_count"],
        }
        for row in vehicle_categories
    ]

    population_summary = None
    if population is not None:
        population_summary = {
            "date": population["date"],
            "population": population["population"],
        }

    return {
        "region": region,
        "vehicle": vehicle_summary,
        "vehicle_categories": category_summaries,
        "population": population_summary,
    }


def get_region_trend(
    db: MySQLDB,
    region_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """선택 지역의 차량·인구 월별 추이를 DataFrame 친화적인 두 목록으로 반환한다."""
    vehicle_rows = get_vehicle_history(db, region_code, start_date, end_date)
    population_rows = get_population_history(db, region_code, start_date, end_date)

    # 그래프에는 날짜와 값만 필요하므로 반복되는 지역 정보는 제거한다.
    # 조회 결과가 없으면 각 list comprehension도 자연스럽게 []를 반환한다.
    return {
        "vehicle_history": [
            {"date": row["date"], "vehicle_count": row["vehicle_count"]}
            for row in vehicle_rows
        ],
        "population_history": [
            {"date": row["date"], "population": row["population"]}
            for row in population_rows
        ],
    }
