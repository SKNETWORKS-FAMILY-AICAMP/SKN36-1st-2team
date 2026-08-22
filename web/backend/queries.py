# 한 SQL 단위의 지역·차량·인구·카테고리 조회

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any

from .db import MySQLDB


# 화면에서 잘못된 코드가 들어오면 불필요한 DB 조회를 하지 않도록 먼저 형식을 검사한다.
REGION_CODE_PATTERN = re.compile(r"^R\d{4}$")


def _validate_region_code(region_code: str) -> str:
    """지역 코드를 검증하고 대문자 R0001 형식으로 정규화한다."""
    # 소문자나 앞뒤 공백을 입력해도 정상 코드라면 사용할 수 있게 정리한다.
    normalized = region_code.strip().upper() if isinstance(region_code, str) else ""
    if not REGION_CODE_PATTERN.fullmatch(normalized):
        raise ValueError("region_code는 R0001 형태여야 합니다.")
    return normalized


def _parse_year_month(value: str, field_name: str = "date") -> date:
    """외부의 YYYY-MM 문자열을 DB 비교용 DATE의 매월 1일로 변환한다."""
    # 화면은 2026-07 문자열을 사용하지만 DB에는 2026-07-01 DATE가 저장되어 있다.
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}", value):
        raise ValueError(f"{field_name}는 YYYY-MM 형식이어야 합니다.")
    try:
        return datetime.strptime(value, "%Y-%m").date()
    except ValueError as error:
        raise ValueError(f"{field_name}에 유효한 연월을 입력해주세요.") from error


def _parse_period(start_date: str | None, end_date: str | None) -> tuple[date | None, date | None]:
    """선택적으로 전달된 시작월과 종료월을 검사하고 DATE로 변환한다."""
    start = _parse_year_month(start_date, "start_date") if start_date is not None else None
    end = _parse_year_month(end_date, "end_date") if end_date is not None else None
    if start is not None and end is not None and start > end:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
    return start, end


def _cast_int(row: dict[str, Any] | None, *keys: str) -> dict[str, Any] | None:
    """MySQL 집계값을 화면에서 쓰기 쉬운 Python int로 변환한다."""
    # COUNT와 SUM은 드라이버에 따라 Decimal 등으로 반환될 수 있어 int로 통일한다.
    if row is not None:
        for key in keys:
            if row.get(key) is not None:
                row[key] = int(row[key])
    return row

def get_regions(db: MySQLDB) -> list[dict[str, Any]]:
    """전체 지역 목록을 region_code 순서의 list[dict]로 반환한다."""
    # 여러 지역 행이 필요하므로 fetch_all()을 사용하며, 결과가 없으면 []가 반환된다.
    return db.fetch_all(
        """SELECT region_id AS region_code, region_name
        FROM region
        ORDER BY region_id"""
    )


def get_regions_by_province(
    db: MySQLDB,
    province_name: str,
) -> list[dict[str, Any]]:
    """실제 DB 시도명과 정확히 일치하는 지역 목록을 반환한다."""
    province = province_name.strip() if isinstance(province_name, str) else ""
    if not province:
        raise ValueError("province_name은 비어 있지 않은 문자열이어야 합니다.")
    # ETL이 '표준시도명 + 공백 + 시군구명'으로 저장하므로 첫 토큰을 정확히 비교한다.
    return db.fetch_all(
        """SELECT region_id AS region_code, region_name
        FROM region
        WHERE SUBSTRING_INDEX(region_name, ' ', 1) = %s
        ORDER BY region_name, region_id""",
        (province,),
    )


def get_region_count(db: MySQLDB) -> dict[str, Any]:
    """전체 분석 대상 지역 수를 {'region_count': int} 형태로 반환한다."""
    # COUNT(*)는 결과가 한 행이므로 fetch_one()을 사용한다.
    row = _cast_int(db.fetch_one("SELECT COUNT(*) AS region_count FROM region"), "region_count")
    return row if row is not None else {"region_count": 0}


def get_region(db: MySQLDB, region_code: str) -> dict[str, Any] | None:
    """region_code에 해당하는 지역 한 건을 반환하고 없으면 None을 반환한다."""
    # R0001 같은 지역코드가 프로젝트 형식에 맞는지 먼저 검사한다.
    code = _validate_region_code(region_code)
    # 한 지역만 찾으므로 fetch_one()을 사용한다. %s 바인딩은 입력값을 SQL에 직접
    # 붙이지 않아 안전하게 조회하기 위한 방식이다.
    return db.fetch_one(
        """SELECT region_id AS region_code, region_name
        FROM region
        WHERE region_id = %s""",
        (code,),
    )


def get_categories(db: MySQLDB) -> list[dict[str, Any]]:
    """DB에 저장된 차량 카테고리 목록을 list[dict]로 반환한다."""
    rows = db.fetch_all(
        """SELECT category_id, category_main, category_sub
        FROM category
        ORDER BY category_id"""
    )
    for row in rows:
        row["category_id"] = int(row["category_id"])
    return rows

def get_vehicle_data(
    db: MySQLDB,
    region_code: str,
    year_month: str,
) -> dict[str, Any] | None:
    """특정 지역·월의 12개 차량 카테고리 등록대수 합계를 반환한다."""
    code = _validate_region_code(region_code)
    month = _parse_year_month(year_month)
    # vehicle과 region을 JOIN해 표시용 지역명을 가져온다. 여러 카테고리 행은 SUM()으로
    # 합산하고 GROUP BY로 같은 지역·월을 하나의 결과 행으로 묶는다.
    row = db.fetch_one(
        """SELECT r.region_id AS region_code,
                  r.region_name,
                  DATE_FORMAT(v.date_ym, '%%Y-%%m') AS date,
                  SUM(v.vehicle_count) AS vehicle_count
        FROM vehicle v
        JOIN region r ON r.region_id = v.region_id
        WHERE v.region_id = %s AND v.date_ym = %s
        GROUP BY r.region_id, r.region_name, v.date_ym""",
        (code, month),
    )
    return _cast_int(row, "vehicle_count")


def get_national_freight_count(
    db: MySQLDB,
    year_month: str,
) -> dict[str, Any] | None:
    """특정 월의 전국 화물 차량 등록대수 합계를 반환하고 없으면 None을 반환한다."""
    month = _parse_year_month(year_month)
    # vehicle과 category를 JOIN해 대분류가 화물인 행만 고른다. 모든 지역과 화물
    # 세부 카테고리 값을 SUM()하고 GROUP BY로 해당 월 결과 한 행을 만든다.
    row = db.fetch_one(
        """SELECT DATE_FORMAT(v.date_ym, '%%Y-%%m') AS date,
                  SUM(v.vehicle_count) AS vehicle_count
        FROM vehicle v
        JOIN category c ON c.category_id = v.category_id
        WHERE v.date_ym = %s AND c.category_main = %s
        GROUP BY v.date_ym""",
        (month, "화물"),
    )
    return _cast_int(row, "vehicle_count")


def get_province_freight_counts(
    db: MySQLDB,
    year_month: str,
) -> list[dict[str, Any]]:
    """특정 월의 전국 화물차 등록대수를 DB 시도명 단위로 합산한다."""
    month = _parse_year_month(year_month)
    rows = db.fetch_all(
        """SELECT SUBSTRING_INDEX(r.region_name, ' ', 1) AS province_name,
                  SUM(v.vehicle_count) AS vehicle_count
        FROM vehicle v
        JOIN category c ON c.category_id = v.category_id
        JOIN region r ON r.region_id = v.region_id
        WHERE v.date_ym = %s AND c.category_main = %s
        GROUP BY SUBSTRING_INDEX(r.region_name, ' ', 1)
        ORDER BY province_name""",
        (month, "화물"),
    )
    for row in rows:
        row["vehicle_count"] = int(row["vehicle_count"])
    return rows


def get_national_freight_usage_counts(
    db: MySQLDB,
    year_month: str,
) -> list[dict[str, Any]]:
    """특정 월의 전국 화물차 등록대수를 용도별로 합산해 반환한다."""
    month = _parse_year_month(year_month)
    rows = db.fetch_all(
        """SELECT DATE_FORMAT(v.date_ym, '%%Y-%%m') AS date,
                  c.category_sub AS category_usage,
                  SUM(v.vehicle_count) AS vehicle_count
        FROM vehicle v
        JOIN category c ON c.category_id = v.category_id
        WHERE v.date_ym = %s AND c.category_main = %s
        GROUP BY v.date_ym, c.category_sub
        ORDER BY c.category_sub""",
        (month, "화물"),
    )
    for row in rows:
        row["vehicle_count"] = int(row["vehicle_count"])
    return rows


def get_national_freight_history(
    db: MySQLDB,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """전국 화물차 월별 합계를 선택 기간 또는 전체 기간으로 반환한다."""
    start, end = _parse_period(start_date, end_date)
    conditions = ["c.category_main = %s"]
    params: list[object] = ["화물"]
    if start is not None:
        conditions.append("v.date_ym >= %s")
        params.append(start)
    if end is not None:
        conditions.append("v.date_ym <= %s")
        params.append(end)

    rows = db.fetch_all(
        f"""SELECT DATE_FORMAT(v.date_ym, '%%Y-%%m') AS date,
                   SUM(v.vehicle_count) AS vehicle_count
        FROM vehicle v
        JOIN category c ON c.category_id = v.category_id
        WHERE {' AND '.join(conditions)}
        GROUP BY v.date_ym
        ORDER BY v.date_ym""",
        tuple(params),
    )
    for row in rows:
        row["vehicle_count"] = int(row["vehicle_count"])
    return rows


def get_top_region_freight_counts(
    db: MySQLDB,
    year_month: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """특정 월의 화물차 등록대수가 많은 지역을 내림차순으로 반환한다."""
    month = _parse_year_month(year_month)
    if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
        raise ValueError("limit은 1 이상의 정수여야 합니다.")

    rows = db.fetch_all(
        """SELECT r.region_id AS region_code,
                  r.region_name,
                  SUM(v.vehicle_count) AS vehicle_count
        FROM vehicle v
        JOIN category c ON c.category_id = v.category_id
        JOIN region r ON r.region_id = v.region_id
        WHERE v.date_ym = %s AND c.category_main = %s
        GROUP BY r.region_id, r.region_name
        ORDER BY vehicle_count DESC, r.region_id
        LIMIT %s""",
        (month, "화물", limit),
    )
    for row in rows:
        row["vehicle_count"] = int(row["vehicle_count"])
    return rows


def get_vehicle_category_counts(
    db: MySQLDB,
    region_code: str,
    year_month: str,
) -> list[dict[str, Any]]:
    """특정 지역·월의 차량 등록대수를 12개 카테고리별로 반환한다."""
    code = _validate_region_code(region_code)
    month = _parse_year_month(year_month)
    # region JOIN은 지역명을, category JOIN은 대분류와 소분류를 얻기 위해 사용한다.
    rows = db.fetch_all(
        """SELECT r.region_id AS region_code,
                  r.region_name,
                  DATE_FORMAT(v.date_ym, '%%Y-%%m') AS date,
                  c.category_id,
                  c.category_main,
                  c.category_sub,
                  v.vehicle_count
        FROM vehicle v
        JOIN region r ON r.region_id = v.region_id
        JOIN category c ON c.category_id = v.category_id
        WHERE v.region_id = %s AND v.date_ym = %s
        ORDER BY c.category_id""",
        (code, month),
    )
    for row in rows:
        row["category_id"] = int(row["category_id"])
        row["vehicle_count"] = int(row["vehicle_count"])
    return rows


def get_vehicle_history(
    db: MySQLDB,
    region_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """특정 지역의 월별 차량 합계 추이를 선택 기간 또는 전체 기간으로 반환한다."""
    code = _validate_region_code(region_code)
    start, end = _parse_period(start_date, end_date)
    conditions = ["v.region_id = %s"]
    params: list[object] = [code]
    # 기간값이 있을 때만 SQL 조건을 동적으로 추가하며 값은 항상 %s로 바인딩한다.
    if start is not None:
        conditions.append("v.date_ym >= %s")
        params.append(start)
    if end is not None:
        conditions.append("v.date_ym <= %s")
        params.append(end)
    rows = db.fetch_all(
        f"""SELECT r.region_id AS region_code,
                   r.region_name,
                   DATE_FORMAT(v.date_ym, '%%Y-%%m') AS date,
                   SUM(v.vehicle_count) AS vehicle_count
        FROM vehicle v
        JOIN region r ON r.region_id = v.region_id
        WHERE {' AND '.join(conditions)}
        GROUP BY r.region_id, r.region_name, v.date_ym
        ORDER BY v.date_ym""",
        tuple(params),
    )
    for row in rows:
        row["vehicle_count"] = int(row["vehicle_count"])
    return rows


def get_population(
    db: MySQLDB,
    region_code: str,
    year_month: str,
) -> dict[str, Any] | None:
    """특정 지역·월의 인구 한 건을 반환하고 없으면 None을 반환한다."""
    code = _validate_region_code(region_code)
    month = _parse_year_month(year_month)
    # people과 region을 JOIN해 인구 값과 표시용 지역명을 함께 조회한다.
    row = db.fetch_one(
        """SELECT r.region_id AS region_code,
                  r.region_name,
                  DATE_FORMAT(p.date_ym, '%%Y-%%m') AS date,
                  p.people_population AS population
        FROM people p
        JOIN region r ON r.region_id = p.region_id
        WHERE p.region_id = %s AND p.date_ym = %s""",
        (code, month),
    )
    return _cast_int(row, "population")


def get_population_history(
    db: MySQLDB,
    region_code: str,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list[dict[str, Any]]:
    """특정 지역의 월별 인구 추이를 선택 기간 또는 전체 기간으로 반환한다."""
    code = _validate_region_code(region_code)
    start, end = _parse_period(start_date, end_date)
    conditions = ["p.region_id = %s"]
    params: list[object] = [code]
    # 시작월이나 종료월을 생략하면 해당 방향의 기간 제한 없이 조회한다.
    if start is not None:
        conditions.append("p.date_ym >= %s")
        params.append(start)
    if end is not None:
        conditions.append("p.date_ym <= %s")
        params.append(end)
    rows = db.fetch_all(
        f"""SELECT r.region_id AS region_code,
                   r.region_name,
                   DATE_FORMAT(p.date_ym, '%%Y-%%m') AS date,
                   p.people_population AS population
        FROM people p
        JOIN region r ON r.region_id = p.region_id
        WHERE {' AND '.join(conditions)}
        ORDER BY p.date_ym""",
        tuple(params),
    )
    for row in rows:
        row["population"] = int(row["population"])
    return rows

# 점수 계산에 필요한 여러 월의 지역별 화물차 수와 전체 차량 수를 반환
def get_national_vehicle_metrics(
    db: MySQLDB,
    year_months: list[str],
) -> list[dict[str, Any]]:
    
    if not year_months:
        return []

    # 점수 계산은 기준월, 3·6·12개월 전 자료를 한 번에 사용한다.
    # 중복 월은 제거하고, 외부 YYYY-MM 문자열은 DB DATE와 비교할 수 있게 변환한다.
    months = sorted({_parse_year_month(value, "year_months") for value in year_months})
    placeholders = ", ".join(["%s"] * len(months))

    # vehicle과 category를 JOIN해야 화물 대분류만 조건부로 합산할 수 있다.
    # SUM(CASE ...)는 화물 3개 세부 카테고리만, 일반 SUM은 12개 전체를 합산한다.
    rows = db.fetch_all(
        f"""SELECT v.region_id AS region_code,
                   DATE_FORMAT(v.date_ym, '%%Y-%%m') AS date,
                   SUM(CASE WHEN c.category_main = %s THEN v.vehicle_count ELSE 0 END) AS truck_count,
                   SUM(v.vehicle_count) AS total_vehicle_count
        FROM vehicle v
        JOIN category c ON c.category_id = v.category_id
        WHERE v.date_ym IN ({placeholders})
        GROUP BY v.region_id, v.date_ym
        ORDER BY v.region_id, v.date_ym""",
        tuple(["화물", *months]),
    )
    for row in rows:
        row["truck_count"] = int(row["truck_count"])
        row["total_vehicle_count"] = int(row["total_vehicle_count"])
    return rows


def get_national_population(
    db: MySQLDB,
    year_month: str,
) -> list[dict[str, Any]]:
    """특정 월에 데이터가 있는 전국 지역별 인구를 반환한다."""
    month = _parse_year_month(year_month)
    # 백분위 모집단은 같은 기준월의 모든 지역이며, 인구가 없는 지역은 결과에 포함되지 않는다.
    rows = db.fetch_all(
        """SELECT region_id AS region_code,
                  DATE_FORMAT(date_ym, '%%Y-%%m') AS date,
                  people_population AS population
        FROM people
        WHERE date_ym = %s
        ORDER BY region_id""",
        (month,),
    )
    for row in rows:
        row["population"] = int(row["population"])
    return rows


def insert_inquiry(
    db: MySQLDB,
    company_name: str,
    manager_name: str,
    email: str,
    contact: str | None,
    inquiry_type: str,
    inquiry_content: str,
    privacy_agreed: bool,
) -> int:
    """검증된 문의 입력값을 저장하고 자동 생성된 inquiry_id를 반환한다."""
    # inquiry_id, status, created_at은 DB가 자동 생성하므로 INSERT 컬럼에서 제외한다.
    # 모든 사용자 입력은 %s 파라미터로 전달하며 SQL 문자열에 직접 합치지 않는다.
    return db.execute(
        """INSERT INTO inquiry (
            company_name,
            manager_name,
            email,
            contact,
            inquiry_type,
            inquiry_content,
            privacy_agreed
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (
            company_name,
            manager_name,
            email,
            contact,
            inquiry_type,
            inquiry_content,
            privacy_agreed,
        ),
    )
