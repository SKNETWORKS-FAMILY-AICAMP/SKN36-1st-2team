# 화면 개발자가 사용할 공개 함수 모음

from .db import MySQLDB
from .queries import (
    get_categories,
    get_national_freight_count,
    get_national_population,
    get_national_vehicle_metrics,
    get_population,
    get_population_history,
    get_region,
    get_region_count,
    get_regions,
    get_vehicle_category_counts,
    get_vehicle_data,
    get_vehicle_history,
    insert_inquiry,
)
from .services import create_inquiry, get_dashboard_summary, get_logistics_score, get_region_detail, get_region_trend

__all__ = [
    "MySQLDB",
    "create_inquiry",
    "get_categories",
    "get_dashboard_summary",
    "get_logistics_score",
    "get_national_freight_count",
    "get_national_population",
    "get_national_vehicle_metrics",
    "get_population",
    "get_population_history",
    "get_region",
    "get_region_count",
    "get_region_detail",
    "get_region_trend",
    "get_regions",
    "get_vehicle_category_counts",
    "get_vehicle_data",
    "get_vehicle_history",
    "insert_inquiry",
]
