"""DB와 분리된 물류 거점 백분위·세부 점수 계산 로직."""

from __future__ import annotations

from datetime import datetime
from typing import Any
import math
import re

def shift_year_month(year_month: str, months: int) -> str:
    """YYYY-MM에서 지정한 개월 수만큼 이동한 YYYY-MM을 반환한다."""

    if not isinstance(year_month, str) or not re.fullmatch(
        r"\d{4}-\d{2}", year_month
    ):
        raise ValueError(
            "date는 YYYY-MM 형식의 유효한 연월이어야 합니다."
        )

    try:
        parsed = datetime.strptime(year_month, "%Y-%m")
    except ValueError as error:
        raise ValueError(
            "date는 YYYY-MM 형식의 유효한 연월이어야 합니다."
        ) from error

    month_index = parsed.year * 12 + parsed.month - 1 + months
    year, zero_based_month = divmod(month_index, 12)

    return f"{year:04d}-{zero_based_month + 1:02d}"


def validate_weight(value: int | float, name: str) -> float:
    """사용자 중요도가 숫자 1~5인지 검사하고 float로 반환한다."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name}는 1~5 범위의 숫자여야 합니다.")
    numeric = float(value)
    if not 1 <= numeric <= 5:
        raise ValueError(f"{name}는 1~5 범위여야 합니다.")
    return numeric


def normalize_weights(
    industry_weight: int | float,
    growth_weight: int | float,
    demand_weight: int | float,
) -> tuple[dict[str, float], dict[str, float]]:
    """1~5 중요도 또는 합계 100인 비율을 검증하고 정규화한다."""
    raw_weights = {
        "industry": industry_weight,
        "growth": growth_weight,
        "demand": demand_weight,
    }
    if any(
        isinstance(value, bool) or not isinstance(value, (int, float))
        for value in raw_weights.values()
    ):
        raise ValueError("가중치는 숫자여야 합니다.")

    numeric_weights = {key: float(value) for key, value in raw_weights.items()}
    importance_scale = all(1 <= value <= 5 for value in numeric_weights.values())
    percentage_scale = (
        all(value >= 0 for value in numeric_weights.values())
        and math.isclose(sum(numeric_weights.values()), 100.0, abs_tol=0.01)
    )
    if not importance_scale and not percentage_scale:
        raise ValueError(
            "가중치는 각각 1~5이거나 0 이상이며 세 값의 합이 100이어야 합니다."
        )

    weight_sum = sum(numeric_weights.values())
    normalized_weights = {
        key: value / weight_sum for key, value in numeric_weights.items()
    }
    return numeric_weights, normalized_weights

# (current - previous) / previous × 100
def calculate_growth(current: int | None, previous: int | None) -> float | None:
    """현재값과 과거값의 증가율을 계산하며 분모가 0이거나 값이 없으면 None을 반환한다."""
    if current is None or previous is None or previous == 0:
        return None
    return (current - previous) / previous * 100.0

# ((평균 순위 - 1) / (N - 1)) × 100
def percentile_scores(values: dict[str, float | int | None]) -> dict[str, float | None]:
    """동일값 평균 순위를 사용해 지역별 값을 0~100 백분위 점수로 변환한다."""
    # None은 모집단에서 제외한다. 값이 같은 지역들은 차지한 순위들의 평균을 공유한다.
    valid = sorted((float(value), code) for code, value in values.items() if value is not None)
    result: dict[str, float | None] = {code: None for code in values}
    count = len(valid)
    if count == 0:
        return result
    if count == 1:
        # N-1이 0인 예외에서는 유일한 관측값을 최저점과 동일한 0점으로 안전 처리한다.
        result[valid[0][1]] = 0.0
        return result

    index = 0
    while index < count:
        end = index + 1
        while end < count and valid[end][0] == valid[index][0]:
            end += 1
        # 순위는 1부터 시작하며 동점 구간의 시작·끝 순위 평균을 사용한다.
        average_rank = ((index + 1) + end) / 2.0
        score = ((average_rank - 1.0) / (count - 1.0)) * 100.0
        for _, code in valid[index:end]:
            result[code] = score
        index = end
    return result


def calculate_ratio(
    numerator: int | float | None,
    denominator: int | float | None,
    scale: float = 1.0,
) -> float | None:
    """두 값의 안전한 비율을 반환하며 값이 없거나 분모가 0이면 None을 반환한다."""
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator * scale


def calculate_trend_persistence(
    monthly_counts: dict[str, int | None],
    target_date: str,
    require_complete: bool = True,
    scale: float = 1.0,
) -> float | None:
    """기준월까지 유효한 최대 25개 YoY 중 양수인 비율을 반환한다."""
    positive_months = 0
    valid_months = 0
    for offset in range(-24, 1):
        month = shift_year_month(target_date, offset)
        previous_month = shift_year_month(month, -12)
        growth = calculate_growth(
            monthly_counts.get(month),
            monthly_counts.get(previous_month),
        )
        if growth is None:
            if require_complete:
                return None
            continue
        valid_months += 1
        if growth > 0:
            positive_months += 1
    if valid_months == 0:
        return None
    return positive_months / valid_months * scale


def calculate_supplemental_metrics(
    target_date: str,
    vehicle_rows: list[dict[str, Any]],
    commercial_rows: list[dict[str, Any]],
    current_population_rows: list[dict[str, Any]],
    previous_population_rows: list[dict[str, Any]],
    population_history_rows: list[dict[str, Any]] | None = None,
    area_rows: list[dict[str, Any]] | None = None,
) -> dict[str, dict[str, dict[str, float | None]]]:
    """화면용 추가 지표 원값과 전국 백분위 점수를 계산한다."""
    target = shift_year_month(target_date, 0)
    previous = shift_year_month(target, -12)
    truck_by_region_month = {
        (row["region_code"], row["date"]): row["truck_count"]
        for row in vehicle_rows
    }
    total_by_region = {
        row["region_code"]: row["total_vehicle_count"]
        for row in vehicle_rows if row["date"] == target
    }
    commercial_by_region_month = {
        (row["region_code"], row["date"]): row["commercial_truck_count"]
        for row in commercial_rows
    }
    current_population = {
        row["region_code"]: row["population"] for row in current_population_rows
    }
    previous_population = {
        row["region_code"]: row["population"] for row in previous_population_rows
    }
    population_by_region_month = {
        (row["region_code"], row["date"]): row["population"]
        for row in (population_history_rows or [])
    }
    area_by_region = {
        row["region_code"]: row.get("area_km2") for row in (area_rows or [])
    }
    region_codes = {
        row["region_code"] for row in vehicle_rows
    } | set(current_population) | set(previous_population) | set(area_by_region)

    national_truck = sum(
        row["truck_count"] for row in vehicle_rows if row["date"] == target
    )
    national_total = sum(total_by_region.values())
    national_truck_ratio = calculate_ratio(national_truck, national_total)

    raw_by_code: dict[str, dict[str, float | None]] = {}
    for code in region_codes:
        truck_current = truck_by_region_month.get((code, target))
        truck_previous = truck_by_region_month.get((code, previous))
        commercial_current = commercial_by_region_month.get((code, target))
        commercial_previous = commercial_by_region_month.get((code, previous))
        local_ratio = calculate_ratio(truck_current, total_by_region.get(code))
        lq = calculate_ratio(local_ratio, national_truck_ratio)
        commercial_share = calculate_ratio(commercial_current, truck_current, 100.0)
        truck_history = {
            date: count
            for (region_code, date), count in truck_by_region_month.items()
            if region_code == code
        }
        persistence = calculate_trend_persistence(truck_history, target)
        commercial_delta = (
            commercial_current - commercial_previous
            if commercial_current is not None and commercial_previous is not None
            else None
        )
        truck_delta = (
            truck_current - truck_previous
            if truck_current is not None and truck_previous is not None
            else None
        )
        conversion = calculate_ratio(commercial_delta, truck_delta)
        population_growth = calculate_growth(
            current_population.get(code), previous_population.get(code)
        )
        population_history = {
            date: population
            for (region_code, date), population in population_by_region_month.items()
            if region_code == code
        }
        population_persistence = calculate_trend_persistence(
            population_history,
            target,
            require_complete=False,
            scale=100.0,
        )
        area_km2 = area_by_region.get(code)
        population_density = (
            calculate_ratio(current_population.get(code), area_km2)
            if area_km2 is not None and area_km2 > 0
            else None
        )
        raw_by_code[code] = {
            "location_quotient": round(lq, 4) if lq is not None else None,
            "commercial_truck_share": (
                round(commercial_share, 4) if commercial_share is not None else None
            ),
            "trend_persistence": (
                round(persistence, 4) if persistence is not None else None
            ),
            "commercial_conversion_rate": (
                round(conversion, 4) if conversion is not None else None
            ),
            "population_yoy_growth": (
                round(population_growth, 4) if population_growth is not None else None
            ),
            "population_trend_persistence": (
                round(population_persistence, 4)
                if population_persistence is not None else None
            ),
            "area_km2": round(area_km2, 4) if area_km2 is not None else None,
            "population_density": (
                round(population_density, 4) if population_density is not None else None
            ),
        }

    scored_metrics = [
        metric for metric in next(iter(raw_by_code.values()), {})
        if metric != "area_km2"
    ]
    normalized_by_metric = {
        f"{metric}_score": percentile_scores(
            {code: raw[metric] for code, raw in raw_by_code.items()}
        )
        for metric in scored_metrics
    }
    return {
        code: {
            "raw": raw,
            "normalized": {
                metric: round(scores.get(code), 4) if scores.get(code) is not None else None
                for metric, scores in normalized_by_metric.items()
            },
        }
        for code, raw in raw_by_code.items()
    }

# 계산 순서 : 원본 값 → 화물차 비중·YoY·가속도 → 전국 백분위 → 산업성·성장성·수요성 → 사용자 가중치 정규화 → 최종점수
def calculate_logistics_score(
    region: dict[str, Any],
    target_date: str,
    vehicle_rows: list[dict[str, Any]],
    population_rows: list[dict[str, Any]],
    industry_weight: int | float = 3,
    growth_weight: int | float = 3,
    demand_weight: int | float = 3,
) -> dict[str, Any]:
    """전국 원본 데이터를 백분위화하고 선택 지역의 물류 거점 점수를 계산한다."""
    weights, normalized_weights = normalize_weights(
        industry_weight,
        growth_weight,
        demand_weight,
    )

    t_minus_3 = shift_year_month(target_date, -3)
    t_minus_6 = shift_year_month(target_date, -6)
    t_minus_12 = shift_year_month(target_date, -12)

    # 지역별·월별 화물차 수와 기준월 전체 차량 수를 빠르게 찾을 수 있는 dict로 바꾼다.
    truck_by_region_month: dict[tuple[str, str], int] = {}
    total_by_region: dict[str, int] = {}
    region_codes: set[str] = set()
    for row in vehicle_rows:
        code = row["region_code"]
        row_date = row["date"]
        region_codes.add(code)
        truck_by_region_month[(code, row_date)] = row["truck_count"]
        if row_date == target_date:
            total_by_region[code] = row["total_vehicle_count"]

    population_by_region = {row["region_code"]: row["population"] for row in population_rows}
    region_codes.update(population_by_region)

    truck_counts: dict[str, int | None] = {}
    truck_ratios: dict[str, float | None] = {}
    yoy_values: dict[str, float | None] = {}
    acceleration_values: dict[str, float | None] = {}
    populations: dict[str, int | None] = {}

    for code in region_codes:
        truck_t = truck_by_region_month.get((code, target_date))
        total = total_by_region.get(code)
        truck_counts[code] = truck_t
        truck_ratios[code] = (
            truck_t / total * 100.0
            if truck_t is not None and total is not None and total != 0
            else None
        )
        yoy_values[code] = calculate_growth(
            truck_t, truck_by_region_month.get((code, t_minus_12))
        )
        recent_growth = calculate_growth(
            truck_t, truck_by_region_month.get((code, t_minus_3))
        )
        previous_growth = calculate_growth(
            truck_by_region_month.get((code, t_minus_3)),
            truck_by_region_month.get((code, t_minus_6)),
        )
        acceleration_values[code] = (
            recent_growth - previous_growth
            if recent_growth is not None and previous_growth is not None
            else None
        )
        populations[code] = population_by_region.get(code)

    normalized = {
        "truck_count_score": percentile_scores(truck_counts),
        "truck_ratio_score": percentile_scores(truck_ratios),
        "yoy_score": percentile_scores(yoy_values),
        "acceleration_score": percentile_scores(acceleration_values),
        "population_score": percentile_scores(populations),
    }

    code = region["region_code"]
    truck_count = truck_counts.get(code)
    total_vehicle_count = total_by_region.get(code)
    population = populations.get(code)
    yoy_growth = yoy_values.get(code)
    acceleration = acceleration_values.get(code)
    truck_per_10000 = (
        truck_count / population * 10_000.0
        if truck_count is not None and population is not None and population != 0
        else None
    )
    selected_normalized = {key: scores.get(code) for key, scores in normalized.items()}

    industry_score = None
    if selected_normalized["truck_count_score"] is not None and selected_normalized["truck_ratio_score"] is not None:
        industry_score = (
            selected_normalized["truck_count_score"] * 0.7
            + selected_normalized["truck_ratio_score"] * 0.3
        )
    growth_score = None
    if selected_normalized["yoy_score"] is not None and selected_normalized["acceleration_score"] is not None:
        growth_score = (
            selected_normalized["yoy_score"] * 0.7
            + selected_normalized["acceleration_score"] * 0.3
        )
    demand_score = selected_normalized["population_score"]

    reasons: list[str] = []
    if truck_count is None or total_vehicle_count is None:
        reasons.append("해당 월의 차량 데이터가 없습니다.")
    elif total_vehicle_count == 0:
        reasons.append("전체 차량수가 0이어서 화물차 비중을 계산할 수 없습니다.")
    if population is None:
        reasons.append("해당 월의 인구 데이터가 없습니다.")
    if yoy_growth is None or acceleration is None:
        reasons.append("전년 동월 또는 3·6개월 전 화물차 이력이 부족하거나 분모가 0입니다.")

    score_available = industry_score is not None and growth_score is not None and demand_score is not None
    total_score = None
    if score_available:
        total_score = (
            industry_score * normalized_weights["industry"]
            + growth_score * normalized_weights["growth"]
            + demand_score * normalized_weights["demand"]
        )

    def rounded(value: float | None) -> float | None:
        return round(value, 4) if value is not None else None

    return {
        "region": region,
        "date": target_date,
        "raw": {
            "truck_count": truck_count,
            "total_vehicle_count": total_vehicle_count,
            "truck_ratio": rounded(truck_ratios.get(code)),
            "population": population,
            "truck_per_10000": rounded(truck_per_10000),
            "yoy_growth": rounded(yoy_growth),
            "acceleration": rounded(acceleration),
        },
        "normalized": {key: rounded(value) for key, value in selected_normalized.items()},
        "scores": {
            "industry": rounded(industry_score),
            "growth": rounded(growth_score),
            "demand": rounded(demand_score),
            "total": rounded(total_score),
        },
        "weights": weights,
        "normalized_weights": {key: rounded(value) for key, value in normalized_weights.items()},
        "score_available": score_available,
        "unavailable_reason": " ".join(reasons) if reasons else None,
    }
