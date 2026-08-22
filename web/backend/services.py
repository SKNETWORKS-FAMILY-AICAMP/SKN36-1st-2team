# 여러 query 결과를 Streamlit 화면용 구조로 조합

from __future__ import annotations

import re
from typing import Any

from pymysql import MySQLError

from .db import MySQLDB
from .queries import (
    get_national_population,
    get_national_freight_count,
    get_national_vehicle_metrics,
    get_population,
    get_population_history,
    get_region,
    get_region_count,
    get_vehicle_category_counts,
    get_vehicle_data,
    get_vehicle_history,
    insert_inquiry,
)
from .scoring import calculate_logistics_score, shift_year_month, validate_weight


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


def get_logistics_score(
    db: MySQLDB,
    region_code: str,
    date: str,
    industry_weight: int | float = 3,
    growth_weight: int | float = 3,
    demand_weight: int | float = 3,
) -> dict[str, Any] | None:
    """선택 지역·월의 전국 백분위 기반 물류 거점 점수를 반환한다."""
    # DB를 조회하기 전에 날짜와 중요도를 검증해 잘못된 입력을 빠르게 알려준다.
    target_date = shift_year_month(date, 0)
    validate_weight(industry_weight, "industry_weight")
    validate_weight(growth_weight, "growth_weight")
    validate_weight(demand_weight, "demand_weight")

    # 존재하지 않는 정상 형식의 지역코드는 기존 단건 조회 규칙과 같이 None을 반환한다.
    region = get_region(db, region_code)
    if region is None:
        return None

    # 성장성에는 기준월과 3·6·12개월 전 화물차 수가 필요하다.
    required_months = [
        target_date,
        shift_year_month(target_date, -3),
        shift_year_month(target_date, -6),
        shift_year_month(target_date, -12),
    ]
    vehicle_rows = get_national_vehicle_metrics(db, required_months)
    population_rows = get_national_population(db, target_date)

    # scoring.py는 DB를 모르고 전달받은 원본 값만으로 백분위와 점수를 계산한다.
    return calculate_logistics_score(
        region=region,
        target_date=target_date,
        vehicle_rows=vehicle_rows,
        population_rows=population_rows,
        industry_weight=industry_weight,
        growth_weight=growth_weight,
        demand_weight=demand_weight,
    )


def create_inquiry(
    db: MySQLDB,
    company_name: str,
    manager_name: str,
    email: str,
    contact: str | None,
    inquiry_type: str,
    inquiry_content: str,
    privacy_agreed: bool,
) -> dict[str, bool | int | str]:
    """문의 화면 입력값을 검증하고 정상일 때만 MySQL에 저장한다."""
    fields = [
        ("company_name", company_name, "회사명", 100),
        ("manager_name", manager_name, "담당자명", 50),
        ("email", email, "이메일", 255),
        ("inquiry_type", inquiry_type, "문의 유형", 50),
        ("inquiry_content", inquiry_content, "문의 내용", 1000),
    ]
    cleaned: dict[str, str] = {}
    for key, value, label, max_length in fields:
        if not isinstance(value, str) or not value.strip():
            return {"success": False, "message": f"{label}을(를) 입력해주세요."}
        normalized = value.strip()
        if len(normalized) > max_length:
            return {
                "success": False,
                "message": f"{label}은(는) {max_length}자 이하로 입력해주세요.",
            }
        cleaned[key] = normalized

    if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", cleaned["email"]) is None:
        return {"success": False, "message": "올바른 이메일 형식을 입력해주세요."}

    normalized_contact: str | None = None
    if contact is not None:
        if not isinstance(contact, str):
            return {"success": False, "message": "연락처는 문자열로 입력해주세요."}
        normalized_contact = contact.strip() or None
        if normalized_contact is not None and len(normalized_contact) > 30:
            return {"success": False, "message": "연락처는 30자 이하로 입력해주세요."}

    if privacy_agreed is not True:
        return {"success": False, "message": "개인정보 수집에 동의해주세요."}

    try:
        inquiry_id = insert_inquiry(
            db=db,
            company_name=cleaned["company_name"],
            manager_name=cleaned["manager_name"],
            email=cleaned["email"],
            contact=normalized_contact,
            inquiry_type=cleaned["inquiry_type"],
            inquiry_content=cleaned["inquiry_content"],
            privacy_agreed=True,
        )
    except MySQLError:
        return {
            "success": False,
            "message": "문의 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
        }

    return {
        "success": True,
        "inquiry_id": inquiry_id,
        "message": "문의가 정상적으로 등록되었습니다.",
    }
