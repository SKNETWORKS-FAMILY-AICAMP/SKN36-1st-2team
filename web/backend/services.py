# 여러 query 결과를 Streamlit 화면용 구조로 조합

from __future__ import annotations

import re
from typing import Any

from pymysql import MySQLError

from .db import MySQLDB
from .queries import (
    get_national_freight_history,
    get_national_commercial_freight_counts,
    get_national_population,
    get_national_population_history,
    get_national_freight_count,
    get_national_freight_usage_counts,
    get_national_vehicle_metrics,
    get_population,
    get_population_history,
    get_region,
    get_region_areas,
    get_region_count,
    get_regions,
    get_regions_by_province,
    get_vehicle_category_counts,
    get_vehicle_data,
    get_vehicle_history,
    get_top_region_freight_counts,
    insert_inquiry,
)
from .scoring import (
    calculate_growth,
    calculate_logistics_score,
    calculate_supplemental_metrics,
    normalize_weights,
    shift_year_month,
)


def get_dashboard_summary(db: MySQLDB, year_month: str) -> dict[str, Any]:
    """메인 화면의 지역 수와 전국 화물차 현황을 한 dict로 반환한다."""
    # 서로 다른 SQL 결과를 각각 조회한 뒤 Streamlit metric에서 바로 쓸 수 있게 합친다.
    previous_year_month = shift_year_month(year_month, -12)
    region_result = get_region_count(db)
    freight_result = get_national_freight_count(db, year_month)
    previous_freight_result = get_national_freight_count(db, previous_year_month)

    national_freight_count = (
        freight_result["vehicle_count"] if freight_result is not None else None
    )
    previous_freight_count = (
        previous_freight_result["vehicle_count"]
        if previous_freight_result is not None
        else None
    )
    year_over_year_growth_rate = calculate_growth(
        national_freight_count,
        previous_freight_count,
    )

    return {
        "date": year_month,
        "previous_year_month": previous_year_month,
        "region_count": region_result["region_count"],
        # 해당 월 데이터가 없으면 화면이 이를 구분할 수 있도록 None을 유지한다.
        "national_freight_count": national_freight_count,
        "year_over_year_growth_rate": (
            round(year_over_year_growth_rate, 1)
            if year_over_year_growth_rate is not None
            else None
        ),
    }


def get_national_vehicle_usage(
    db: MySQLDB,
    year_month: str,
) -> dict[str, Any]:
    """특정 월의 전국 화물차 합계와 용도별 등록대수·비율을 반환한다."""
    rows = get_national_freight_usage_counts(db, year_month)
    total = sum(row["vehicle_count"] for row in rows)
    usage_order = {"자가용": 0, "영업용": 1, "관용": 2}
    ordered_rows = sorted(
        rows,
        key=lambda row: usage_order.get(row["category_usage"], 3),
    )

    return {
        "date": year_month,
        "total": total,
        "usage": [
            {
                "usage": row["category_usage"],
                "count": row["vehicle_count"],
                "ratio": round(row["vehicle_count"] / total * 100.0, 1)
                if total != 0
                else None,
            }
            for row in ordered_rows
        ],
    }


def get_national_vehicle_trend(
    db: MySQLDB,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """선택 기간의 전국 화물차 월별 등록 추이를 반환한다."""
    rows = get_national_freight_history(db, start_date, end_date)
    return [
        {"date": row["date"], "count": row["vehicle_count"]}
        for row in rows
    ]


def get_top_regions_by_freight_count(
    db: MySQLDB,
    year_month: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """특정 월의 화물차 등록대수 상위 지역을 화면용 구조로 반환한다."""
    rows = get_top_region_freight_counts(db, year_month, limit)
    return [
        {
            "region_code": row["region_code"],
            "region_name": row["region_name"],
            "count": row["vehicle_count"],
        }
        for row in rows
    ]


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


def get_freight_per_population_trend(
    db: MySQLDB,
    start_date: str,
    end_date: str,
    province_name: str | None = None,
    region_code: str | None = None,
) -> list[dict[str, Any]]:
    """전국·시도·시군구의 월별 화물차 합계와 인구 1천명당 값을 반환한다."""
    start = shift_year_month(start_date, 0)
    end = shift_year_month(end_date, 0)
    if start > end:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")

    months: list[str] = []
    month = start
    while month <= end:
        months.append(month)
        month = shift_year_month(month, 1)

    vehicle_rows = get_national_vehicle_metrics(db, months)
    population_rows = get_national_population_history(db, start, end)
    population_by_key = {
        (row["region_code"], row["date"]): row["population"]
        for row in population_rows
    }
    # 같은 지역·월에 차량과 인구가 모두 있는 관측치만 비율 모집단에 포함한다.
    matched = [
        {
            "region_code": row["region_code"],
            "date": row["date"],
            "truck_count": row["truck_count"],
            "population": population_by_key[(row["region_code"], row["date"])],
        }
        for row in vehicle_rows
        if (row["region_code"], row["date"]) in population_by_key
        and population_by_key[(row["region_code"], row["date"])] is not None
        and population_by_key[(row["region_code"], row["date"])] > 0
    ]

    allowed_codes: set[str] | None = None
    if region_code is not None:
        region = get_region(db, region_code)
        allowed_codes = {region_code} if region is not None else set()
    elif province_name is not None:
        allowed_codes = {
            row["region_code"] for row in get_regions_by_province(db, province_name)
        }

    def aggregate(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
        totals: dict[str, dict[str, int]] = {}
        for row in rows:
            bucket = totals.setdefault(row["date"], {"truck_count": 0, "population": 0})
            bucket["truck_count"] += row["truck_count"]
            bucket["population"] += row["population"]
        return totals

    national = aggregate(matched)
    scoped_rows = (
        matched
        if allowed_codes is None
        else [row for row in matched if row["region_code"] in allowed_codes]
    )
    scoped = aggregate(scoped_rows)

    result = []
    for date in sorted(scoped):
        values = scoped[date]
        national_values = national.get(date)
        population = values["population"]
        national_population = national_values["population"] if national_values else 0
        result.append({
            "date": date,
            "truck_count": values["truck_count"],
            "population": population,
            "truck_per_1000": values["truck_count"] / population * 1000,
            "national_truck_per_1000": (
                national_values["truck_count"] / national_population * 1000
                if national_values and national_population > 0 else None
            ),
        })
    return result


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
    normalize_weights(industry_weight, growth_weight, demand_weight)

    # 존재하지 않는 정상 형식의 지역코드는 기존 단건 조회 규칙과 같이 None을 반환한다.
    region = get_region(db, region_code)
    if region is None:
        return None

    # 추세 지속성·안정성·12개월 가속도에 동일한 37개월 창을 사용한다.
    required_months = [shift_year_month(target_date, offset) for offset in range(-36, 1)]
    vehicle_rows = get_national_vehicle_metrics(db, required_months)
    commercial_rows = get_national_commercial_freight_counts(db, required_months)
    population_rows = get_national_population(db, target_date)
    previous_population_rows = get_national_population(
        db, shift_year_month(target_date, -12)
    )
    population_history_rows = get_national_population_history(
        db, required_months[0], target_date
    )
    area_rows = get_region_areas(db)
    supplemental_metrics = calculate_supplemental_metrics(
        target_date, vehicle_rows, commercial_rows, population_rows,
        previous_population_rows, population_history_rows, area_rows,
    )

    # scoring.py는 DB를 모르고 전달받은 원본 값만으로 백분위와 점수를 계산한다.
    return calculate_logistics_score(
        region=region,
        target_date=target_date,
        vehicle_rows=vehicle_rows,
        population_rows=population_rows,
        industry_weight=industry_weight,
        growth_weight=growth_weight,
        demand_weight=demand_weight,
        supplemental_metrics=supplemental_metrics,
    )


def get_logistics_ranking(
    db: MySQLDB,
    date: str,
    industry_weight: int | float = 3,
    growth_weight: int | float = 3,
    demand_weight: int | float = 3,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """전국 지역의 물류 거점 점수를 계산해 종합점수 순으로 반환한다."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit은 1 이상의 정수여야 합니다.")

    target_date = shift_year_month(date, 0)
    normalize_weights(industry_weight, growth_weight, demand_weight)
    required_months = [shift_year_month(target_date, offset) for offset in range(-36, 1)]

    # 전국 공통 원본은 한 번씩만 조회하고 모든 지역 계산에 같은 목록을 재사용한다.
    regions = get_regions(db)
    vehicle_rows = get_national_vehicle_metrics(db, required_months)
    commercial_rows = get_national_commercial_freight_counts(db, required_months)
    population_rows = get_national_population(db, target_date)
    previous_population_rows = get_national_population(
        db, shift_year_month(target_date, -12)
    )
    population_history_rows = get_national_population_history(
        db, required_months[0], target_date
    )
    area_rows = get_region_areas(db)
    supplemental_metrics = calculate_supplemental_metrics(
        target_date, vehicle_rows, commercial_rows, population_rows,
        previous_population_rows, population_history_rows, area_rows,
    )

    scored_regions: list[dict[str, Any]] = []
    for region in regions:
        result = calculate_logistics_score(
            region=region,
            target_date=target_date,
            vehicle_rows=vehicle_rows,
            population_rows=population_rows,
            industry_weight=industry_weight,
            growth_weight=growth_weight,
            demand_weight=demand_weight,
            supplemental_metrics=supplemental_metrics,
        )
        if not result["score_available"]:
            continue
        scored_regions.append(
            {
                "region_code": region["region_code"],
                "region_name": region["region_name"],
                "date": result["date"],
                "scores": result["scores"],
                "raw": result["raw"],
                "normalized": result["normalized"],
                "metrics": result["metrics"],
                "axis_completeness": result["axis_completeness"],
                "unavailable_metrics": result["unavailable_metrics"],
                "weights": result["weights"],
                "normalized_weights": result["normalized_weights"],
            }
        )

    scored_regions.sort(
        key=lambda row: (-row["scores"]["total"], row["region_code"])
    )
    ranking = scored_regions[:limit]
    for rank, row in enumerate(ranking, start=1):
        row["rank"] = rank
    return ranking


def get_supplemental_logistics_metrics(
    db: MySQLDB,
    date: str,
) -> list[dict[str, Any]]:
    """화면 상세용 추가 지표의 전국 원값과 백분위 점수를 반환한다."""
    target_date = shift_year_month(date, 0)
    months = [shift_year_month(target_date, offset) for offset in range(-36, 1)]
    vehicle_rows = get_national_vehicle_metrics(db, months)
    commercial_rows = get_national_commercial_freight_counts(db, months)
    current_population_rows = get_national_population(db, target_date)
    previous_population_rows = get_national_population(
        db, shift_year_month(target_date, -12)
    )
    population_history_rows = get_national_population_history(
        db, months[0], target_date
    )
    area_rows = get_region_areas(db)
    metrics = calculate_supplemental_metrics(
        target_date=target_date,
        vehicle_rows=vehicle_rows,
        commercial_rows=commercial_rows,
        current_population_rows=current_population_rows,
        previous_population_rows=previous_population_rows,
        population_history_rows=population_history_rows,
        area_rows=area_rows,
    )
    return [
        {
            "region_code": code,
            "date": target_date,
            "raw": values["raw"],
            "normalized": values["normalized"],
        }
        for code, values in sorted(metrics.items())
    ]


def create_inquiry(
    db: MySQLDB,
    company_name: str,
    manager_name: str,
    email: str,
    contact: str | None,
    inquiry_type: str,
    inquiry_content: str,
    privacy_agreed: bool,
) -> dict[str, bool | str]:
    """Streamlit 문의 입력값을 검증하고 정상일 때만 MySQL에 저장한다."""
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

    if re.fullmatch(r"[가-힣A-Za-z0-9][가-힣A-Za-z0-9\s&().,·㈜_\-/]*", cleaned["company_name"]) is None:
        return {
            "success": False,
            "message": "회사명에는 한글, 영문, 숫자와 일반적인 회사명 기호만 사용할 수 있습니다.",
        }

    if re.fullmatch(r"[가-힣A-Za-z]+(?:[\s'-][가-힣A-Za-z]+)*", cleaned["manager_name"]) is None:
        return {
            "success": False,
            "message": "담당자명에는 한글, 영문, 공백, 하이픈(-), 작은따옴표(')만 사용할 수 있습니다.",
        }

    if re.fullmatch(
        r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
        cleaned["email"],
    ) is None:
        return {"success": False, "message": "올바른 이메일 형식을 입력해주세요."}

    normalized_contact: str | None = None
    if contact is not None:
        if not isinstance(contact, str):
            return {"success": False, "message": "연락처는 문자열로 입력해주세요."}
        normalized_contact = contact.strip() or None
        if normalized_contact is not None and len(normalized_contact) > 30:
            return {"success": False, "message": "연락처는 30자 이하로 입력해주세요."}
        if normalized_contact is not None:
            if re.fullmatch(r"\+?[0-9()\s-]+", normalized_contact) is None:
                return {
                    "success": False,
                    "message": "연락처에는 숫자, 공백, 하이픈(-), 괄호, 국가번호(+)만 사용할 수 있습니다.",
                }
            digit_count = len(re.sub(r"\D", "", normalized_contact))
            if not 8 <= digit_count <= 15:
                return {
                    "success": False,
                    "message": "연락처는 숫자 기준 8~15자리로 입력해주세요.",
                }

    # 개인정보 동의가 정확히 True가 아니면 INSERT 함수를 호출하지 않는다.
    if privacy_agreed is not True:
        return {"success": False, "message": "개인정보 수집에 동의해주세요."}

    try:
        insert_inquiry(
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
        return {"success": False, "message": "문의 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}

    return {"success": True, "message": "문의가 정상적으로 등록되었습니다."}
