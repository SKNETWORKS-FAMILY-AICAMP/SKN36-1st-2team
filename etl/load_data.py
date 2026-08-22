"""Load reference Excel data into the existing logistics_db schema."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent / "data"
POPULATION_FILE = DATA_DIR / "전국_인구데이터_전처리완료.xlsx"
VEHICLE_FILE = DATA_DIR / "자동차등록현황_데이터셋.xlsx"
BATCH_SIZE = 5_000

# 분석 기간(2023-07~2026-07) 이전에 폐지된 행정구역은 원본을 보존하되 적재에서 제외한다.
EXCLUDED_REGION_IDS = {"R0167"}

ALLOWED_CATEGORY_MAIN = {"승용", "승합", "화물", "특수"}
ALLOWED_CATEGORY_SUB = {"관용", "자가용", "영업용"}
CATEGORY_COLUMNS = {
    "승용_관용": ("승용", "관용"), "승용_자가용": ("승용", "자가용"),
    "승용_영업용": ("승용", "영업용"),
    "승합_관용": ("승합", "관용"), "승합_자가용": ("승합", "자가용"),
    "승합_영업용": ("승합", "영업용"),
    "화물_관용": ("화물", "관용"), "화물_자가용": ("화물", "자가용"),
    "화물_영업용": ("화물", "영업용"),
    "특수_관용": ("특수", "관용"), "특수_자가용": ("특수", "자가용"),
    "특수_영업용": ("특수", "영업용"),
}


def normalize_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def parse_month(values: pd.Series, label: str) -> pd.Series:
    text = values.astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    parsed = pd.to_datetime(text, format="%Y%m", errors="coerce")
    if parsed.isna().any():
        parsed = pd.to_datetime(text, format="%Y-%m", errors="coerce")
    if parsed.isna().any():
        raise ValueError(f"{label} 날짜 변환 실패:\n{text[parsed.isna()].value_counts().head(20)}")
    return parsed.dt.date


def require_columns(frame: pd.DataFrame, required: Iterable[str], label: str) -> None:
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"{label} 필수 컬럼 누락: {missing}")


def read_region_master() -> pd.DataFrame:
    frame = pd.read_excel(VEHICLE_FILE, sheet_name="지역마스터", dtype={"분석지역ID": str})
    required = ["분석지역ID", "표준시도명", "시군구/연속분석권역"]
    require_columns(frame, required, "지역마스터")
    for column in required:
        frame[column] = frame[column].map(normalize_text)
    excluded_count = int(frame["분석지역ID"].isin(EXCLUDED_REGION_IDS).sum())
    frame = frame[~frame["분석지역ID"].isin(EXCLUDED_REGION_IDS)].copy()
    print(f"지역마스터 폐지 지역 제외: {excluded_count:,}행 ({sorted(EXCLUDED_REGION_IDS)})")
    if (frame[required] == "").any().any():
        raise ValueError("지역마스터 필수값에 NULL/공백이 있습니다.")
    duplicates = frame[frame.duplicated("분석지역ID", keep=False)]
    if not duplicates.empty:
        raise ValueError(f"중복 분석지역ID:\n{duplicates[required].to_string(index=False)}")
    frame["region_name"] = frame["표준시도명"] + " " + frame["시군구/연속분석권역"]
    name_duplicates = frame[frame.duplicated("region_name", keep=False)]
    if not name_duplicates.empty:
        raise ValueError(f"중복 region_name:\n{name_duplicates[required + ['region_name']].to_string(index=False)}")
    invalid_length = frame["분석지역ID"].str.len() != 5
    if invalid_length.any():
        raise ValueError(f"CHAR(5)에 맞지 않는 분석지역ID:\n{frame.loc[invalid_length, required].to_string(index=False)}")
    frame = frame.sort_values("분석지역ID", kind="stable").reset_index(drop=True)
    frame["region_id"] = frame["분석지역ID"]
    return frame


def read_population() -> pd.DataFrame:
    frame = pd.read_excel(POPULATION_FILE, sheet_name="인구_원본")
    require_columns(frame, ["지역", "시도", "시군구", "연월", "인구수"], "인구_원본")
    for column in ["지역", "시도", "시군구"]:
        frame[column] = frame[column].map(normalize_text)
    frame["date_ym"] = parse_month(frame["연월"], "인구")
    frame["people_population"] = pd.to_numeric(frame["인구수"], errors="coerce")
    if frame["people_population"].isna().any() or (frame["people_population"] < 0).any():
        raise ValueError("인구수에 숫자가 아니거나 음수인 값이 있습니다.")
    frame["people_population"] = frame["people_population"].astype("int64")
    return frame


def read_vehicle() -> pd.DataFrame:
    frame = pd.read_excel(VEHICLE_FILE, sheet_name="차량_연속분석", dtype={"분석지역ID": str})
    required = ["년도-월", "분석지역ID", "표준시도명", "시군구/연속분석권역", *CATEGORY_COLUMNS]
    require_columns(frame, required, "차량_연속분석")
    for column in ["분석지역ID", "표준시도명", "시군구/연속분석권역"]:
        frame[column] = frame[column].map(normalize_text)
    excluded_count = int(frame["분석지역ID"].isin(EXCLUDED_REGION_IDS).sum())
    frame = frame[~frame["분석지역ID"].isin(EXCLUDED_REGION_IDS)].copy()
    print(f"차량 원본 폐지 지역 제외: {excluded_count:,}행 ({sorted(EXCLUDED_REGION_IDS)})")
    frame["date_ym"] = parse_month(frame["년도-월"], "차량")
    return frame


def validate_population_region_mapping(population: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    keys = ["시도", "시군구"]
    lookup = regions.rename(columns={"표준시도명": "시도", "시군구/연속분석권역": "시군구"})
    ambiguous = lookup[lookup.duplicated(keys, keep=False)]
    if not ambiguous.empty:
        affected = population.merge(ambiguous[keys].drop_duplicates(), on=keys, how="inner")
        if not affected.empty:
            raise ValueError(f"여러 지역에 매핑되는 인구 지역:\n{ambiguous[keys + ['분석지역ID']].to_string(index=False)}")
    mapped = population.merge(lookup[keys + ["분석지역ID"]], on=keys, how="left", validate="many_to_one")
    mapped["region_id"] = mapped["분석지역ID"]
    failures = mapped[mapped["region_id"].isna()]
    if not failures.empty:
        report = failures.groupby(["시도", "시군구", "지역"], dropna=False).size().reset_index(name="행 개수")
        raise ValueError(f"매핑되지 않은 인구 지역:\n{report.to_string(index=False)}")
    if mapped.duplicated(["region_id", "date_ym"]).any():
        rows = mapped[mapped.duplicated(["region_id", "date_ym"], keep=False)]
        raise ValueError(f"인구 PK 중복:\n{rows[['지역', 'date_ym']].to_string(index=False)}")
    return mapped


def validate_vehicle_region_mapping(vehicle: pd.DataFrame, regions: pd.DataFrame) -> pd.DataFrame:
    valid_ids = set(regions["분석지역ID"])
    failures = vehicle[~vehicle["분석지역ID"].isin(valid_ids)]
    if not failures.empty:
        columns = ["분석지역ID", "표준시도명", "시군구/연속분석권역"]
        raise ValueError(f"지역마스터에 없는 차량 지역:\n{failures[columns].drop_duplicates().to_string(index=False)}")
    mapped = vehicle.copy()
    mapped["region_id"] = mapped["분석지역ID"]
    return mapped


def build_date_dimension(population: pd.DataFrame, vehicle: pd.DataFrame) -> pd.DataFrame:
    months = sorted(set(population["date_ym"]) | set(vehicle["date_ym"]))
    frame = pd.DataFrame({"date_ym": months})
    timestamps = pd.to_datetime(frame["date_ym"])
    frame["date_half"] = ((timestamps.dt.month - 1) // 6 + 1).astype(int)
    frame["date_quarter"] = timestamps.dt.quarter.astype(int)
    frame["date_year"] = timestamps.dt.year.astype(int)
    frame["date_month"] = timestamps.dt.month.astype(int)
    return frame


def build_categories() -> pd.DataFrame:
    ordered = list(CATEGORY_COLUMNS.values())
    if len(ordered) != 12 or len(set(ordered)) != 12:
        raise ValueError("차량 카테고리는 중복 없는 12개여야 합니다.")
    if {main for main, _ in ordered} != ALLOWED_CATEGORY_MAIN:
        raise ValueError("허용되지 않은 category_main이 있습니다.")
    if {sub for _, sub in ordered} != ALLOWED_CATEGORY_SUB:
        raise ValueError("허용되지 않은 category_sub가 있습니다.")
    frame = pd.DataFrame(ordered, columns=["category_main", "category_sub"])
    frame.insert(0, "category_id", range(1, len(frame) + 1))
    return frame


def transform_vehicle_to_long(vehicle: pd.DataFrame, categories: pd.DataFrame) -> pd.DataFrame:
    for column in CATEGORY_COLUMNS:
        vehicle[column] = pd.to_numeric(vehicle[column], errors="coerce")
    bad = vehicle[list(CATEGORY_COLUMNS)].isna().any(axis=1)
    if bad.any() or (vehicle[list(CATEGORY_COLUMNS)] < 0).any().any():
        raise ValueError("차량 수에 숫자가 아니거나 음수인 값이 있습니다.")
    long = vehicle.melt(
        id_vars=["region_id", "date_ym"], value_vars=list(CATEGORY_COLUMNS),
        var_name="source_category", value_name="vehicle_count",
    )
    category_ids = {source: index + 1 for index, source in enumerate(CATEGORY_COLUMNS)}
    long["category_id"] = long["source_category"].map(category_ids)
    long["vehicle_count"] = long["vehicle_count"].astype("int64")
    key = ["category_id", "region_id", "date_ym"]
    duplicate_contributions = int(long.duplicated(key, keep=False).sum())
    before_total = int(long["vehicle_count"].sum())
    long = long.groupby(key, as_index=False, sort=True)["vehicle_count"].sum()
    after_total = int(long["vehicle_count"].sum())
    expected = vehicle[["region_id", "date_ym"]].drop_duplicates().shape[0] * len(categories)
    if len(long) != expected or before_total != after_total:
        raise ValueError("차량 지역 통합 후 행 수 또는 차량 총합이 보존되지 않았습니다.")
    print(
        f"차량 지역 변경 이력 통합: raw={len(vehicle) * len(categories):,}, "
        f"PK contributions={duplicate_contributions:,}, final={len(long):,}, total preserved={before_total == after_total}"
    )
    return long[key + ["vehicle_count"]]


def connect():
    import pymysql
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    return pymysql.connect(
        host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", "3307")),
        user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""),
        database=os.getenv("DB_NAME", "logistics_db"), charset="utf8mb4", autocommit=False,
    )


def batched(rows: Sequence[tuple], size: int = BATCH_SIZE):
    for start in range(0, len(rows), size):
        yield rows[start:start + size]


def insert_frame(cursor, sql: str, frame: pd.DataFrame, columns: list[str]) -> None:
    rows = list(frame[columns].itertuples(index=False, name=None))
    for batch in batched(rows):
        cursor.executemany(sql, batch)


def rebuild_analysis_schema(connection) -> None:
    """Recreate only analysis tables; admin and inquiry are intentionally untouched."""
    statements = [
        "DROP TABLE IF EXISTS vehicle", "DROP TABLE IF EXISTS people",
        "DROP TABLE IF EXISTS category", "DROP TABLE IF EXISTS `date`", "DROP TABLE IF EXISTS region",
        """CREATE TABLE region (
            region_id CHAR(5) NOT NULL COMMENT '분석지역ID',
            region_name VARCHAR(30) NOT NULL COMMENT '지역이름',
            PRIMARY KEY (region_id)
        )""",
        """CREATE TABLE `date` (
            date_ym DATE NOT NULL COMMENT '날짜연월', date_half TINYINT NOT NULL COMMENT '반기',
            date_quarter TINYINT NOT NULL COMMENT '분기', date_year SMALLINT NOT NULL COMMENT '연도',
            date_month TINYINT NOT NULL COMMENT '월', PRIMARY KEY (date_ym)
        )""",
        """CREATE TABLE category (
            category_id INT NOT NULL AUTO_INCREMENT COMMENT '카테고리아이디',
            category_main VARCHAR(30) NOT NULL COMMENT '카테고리대분류',
            category_sub VARCHAR(30) NOT NULL COMMENT '카테고리소분류', PRIMARY KEY (category_id)
        )""",
        """CREATE TABLE people (
            region_id CHAR(5) NOT NULL COMMENT '분석지역ID', date_ym DATE NOT NULL COMMENT '날짜연월',
            people_population INT NOT NULL COMMENT '인구수', PRIMARY KEY (region_id, date_ym),
            CONSTRAINT fk_people_region FOREIGN KEY (region_id) REFERENCES region(region_id),
            CONSTRAINT fk_people_date FOREIGN KEY (date_ym) REFERENCES `date`(date_ym)
        )""",
        """CREATE TABLE vehicle (
            category_id INT NOT NULL COMMENT '카테고리아이디',
            region_id CHAR(5) NOT NULL COMMENT '분석지역ID', date_ym DATE NOT NULL COMMENT '날짜연월',
            vehicle_count INT NOT NULL COMMENT '차량등록대수', PRIMARY KEY (category_id, region_id, date_ym),
            CONSTRAINT fk_vehicle_category FOREIGN KEY (category_id) REFERENCES category(category_id),
            CONSTRAINT fk_vehicle_region FOREIGN KEY (region_id) REFERENCES region(region_id),
            CONSTRAINT fk_vehicle_date FOREIGN KEY (date_ym) REFERENCES `date`(date_ym)
        )""",
    ]
    with connection.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)
    connection.commit()
    print("분석 테이블 5개 스키마 재구축 완료 (admin/inquiry 유지)")


def load_all(connection, regions, dates, categories, people, vehicle) -> None:
    with connection.cursor() as cursor:
        for table in ["vehicle", "people", "category", "`date`", "region"]:
            cursor.execute(f"DELETE FROM {table}")
        insert_frame(cursor, "INSERT INTO region (region_id, region_name) VALUES (%s,%s)", regions, ["region_id", "region_name"])
        insert_frame(cursor, "INSERT INTO `date` VALUES (%s,%s,%s,%s,%s)", dates, ["date_ym", "date_half", "date_quarter", "date_year", "date_month"])
        insert_frame(cursor, "INSERT INTO category VALUES (%s,%s,%s)", categories, ["category_id", "category_main", "category_sub"])
        insert_frame(cursor, "INSERT INTO people VALUES (%s,%s,%s)", people, ["region_id", "date_ym", "people_population"])
        insert_frame(cursor, "INSERT INTO vehicle VALUES (%s,%s,%s,%s)", vehicle, ["category_id", "region_id", "date_ym", "vehicle_count"])


def scalar(cursor, sql: str):
    cursor.execute(sql)
    return cursor.fetchone()[0]


def validate_database(connection, source_regions: pd.DataFrame, source_population_rows: int, source_vehicle_rows: int, expected_vehicle_rows: int) -> None:
    with connection.cursor() as cursor:
        checks = {
            "region": {
                "전체 지역 수": "SELECT COUNT(*) FROM region",
                "region_id 중복": "SELECT COUNT(*)-COUNT(DISTINCT region_id) FROM region",
                "region_name 중복": "SELECT COUNT(*)-COUNT(DISTINCT region_name) FROM region",
                "NULL": "SELECT COUNT(*) FROM region WHERE region_id IS NULL OR region_name IS NULL",
                "ID 형식 오류": "SELECT COUNT(*) FROM region WHERE region_id NOT REGEXP '^R[0-9]{4}$'",
                "폐지 지역": "SELECT COUNT(*) FROM region WHERE region_id='R0167'",
                "인구 이력 누락": "SELECT COUNT(*) FROM region r LEFT JOIN (SELECT DISTINCT region_id FROM people) p ON p.region_id=r.region_id WHERE p.region_id IS NULL",
            },
            "date": {
                "전체 월 수": "SELECT COUNT(*) FROM `date`", "최소 월": "SELECT MIN(date_ym) FROM `date`",
                "최대 월": "SELECT MAX(date_ym) FROM `date`", "연도 개수": "SELECT COUNT(DISTINCT date_year) FROM `date`",
                "NULL": "SELECT COUNT(*) FROM `date` WHERE date_ym IS NULL OR date_half IS NULL OR date_quarter IS NULL OR date_year IS NULL OR date_month IS NULL",
            },
            "category": {
                "전체 카테고리 수": "SELECT COUNT(*) FROM category",
                "대/소분류 중복": "SELECT COUNT(*)-COUNT(DISTINCT category_main, category_sub) FROM category",
                "총계 main": "SELECT COUNT(*) FROM category WHERE category_main='총계'",
                "계 sub": "SELECT COUNT(*) FROM category WHERE category_sub='계'",
            },
            "people": {
                "전체 row 수": "SELECT COUNT(*) FROM people", "지역 개수": "SELECT COUNT(DISTINCT region_id) FROM people",
                "월 개수": "SELECT COUNT(DISTINCT date_ym) FROM people", "최소 월": "SELECT MIN(date_ym) FROM people", "최대 월": "SELECT MAX(date_ym) FROM people",
                "PK 중복": "SELECT COUNT(*)-COUNT(DISTINCT region_id, date_ym) FROM people",
                "region FK 누락": "SELECT COUNT(*) FROM people p LEFT JOIN region r ON p.region_id=r.region_id WHERE r.region_id IS NULL",
                "date FK 누락": "SELECT COUNT(*) FROM people p LEFT JOIN `date` d ON p.date_ym=d.date_ym WHERE d.date_ym IS NULL",
                "NULL": "SELECT COUNT(*) FROM people WHERE region_id IS NULL OR date_ym IS NULL OR people_population IS NULL",
                "ID 형식 오류": "SELECT COUNT(*) FROM people WHERE region_id NOT REGEXP '^R[0-9]{4}$'",
                "폐지 지역": "SELECT COUNT(*) FROM people WHERE region_id='R0167'",
            },
            "vehicle": {
                "전체 row 수": "SELECT COUNT(*) FROM vehicle", "지역 개수": "SELECT COUNT(DISTINCT region_id) FROM vehicle",
                "월 개수": "SELECT COUNT(DISTINCT date_ym) FROM vehicle", "카테고리 개수": "SELECT COUNT(DISTINCT category_id) FROM vehicle",
                "최소 월": "SELECT MIN(date_ym) FROM vehicle", "최대 월": "SELECT MAX(date_ym) FROM vehicle",
                "PK 중복": "SELECT COUNT(*)-COUNT(DISTINCT category_id, region_id, date_ym) FROM vehicle",
                "region FK 누락": "SELECT COUNT(*) FROM vehicle v LEFT JOIN region r ON v.region_id=r.region_id WHERE r.region_id IS NULL",
                "date FK 누락": "SELECT COUNT(*) FROM vehicle v LEFT JOIN `date` d ON v.date_ym=d.date_ym WHERE d.date_ym IS NULL",
                "category FK 누락": "SELECT COUNT(*) FROM vehicle v LEFT JOIN category c ON v.category_id=c.category_id WHERE c.category_id IS NULL",
                "NULL": "SELECT COUNT(*) FROM vehicle WHERE category_id IS NULL OR region_id IS NULL OR date_ym IS NULL OR vehicle_count IS NULL",
                "총계 main": "SELECT COUNT(*) FROM vehicle v JOIN category c ON v.category_id=c.category_id WHERE c.category_main='총계'",
                "계 sub": "SELECT COUNT(*) FROM vehicle v JOIN category c ON v.category_id=c.category_id WHERE c.category_sub='계'",
                "폐지 지역": "SELECT COUNT(*) FROM vehicle WHERE region_id='R0167'",
            },
        }
        results = {}
        for table, table_checks in checks.items():
            results[table] = {name: scalar(cursor, sql) for name, sql in table_checks.items()}
            print(f"\n[{table}]")
            for name, value in results[table].items():
                print(f"{name}: {value}")
        cursor.execute("SELECT DATA_TYPE, COLUMN_TYPE, EXTRA FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='region' AND COLUMN_NAME='region_id'")
        region_schema = cursor.fetchone()
        print(f"region.region_id 스키마: data_type={region_schema[0]}, column_type={region_schema[1]}, extra={region_schema[2] or '(없음)'}")
        if region_schema[0].lower() != "char" or region_schema[1].lower() != "char(5)" or "auto_increment" in region_schema[2].lower():
            raise ValueError(f"region.region_id 스키마 오류: {region_schema}")
        cursor.execute("SELECT region_id FROM region")
        database_region_ids = {row[0] for row in cursor.fetchall()}
        source_region_ids = set(source_regions["분석지역ID"])
        if database_region_ids != source_region_ids:
            raise ValueError(f"Excel/DB region_id 집합 불일치: Excel only={sorted(source_region_ids-database_region_ids)}, DB only={sorted(database_region_ids-source_region_ids)}")
        if results["region"]["전체 지역 수"] != len(source_regions):
            raise ValueError("지역마스터/DB region 행 수가 다릅니다.")
        cursor.execute("SELECT region_id, region_name FROM region ORDER BY region_id LIMIT 10")
        print("region 샘플 10개:")
        for region_id, region_name in cursor.fetchall():
            print(f"{region_id} | {region_name}")
        if results["category"]["전체 카테고리 수"] != 12:
            raise ValueError("DB 카테고리 수가 12개가 아닙니다.")
        cursor.execute("SELECT DISTINCT category_main FROM category")
        if {row[0] for row in cursor.fetchall()} != ALLOWED_CATEGORY_MAIN:
            raise ValueError("DB category_main 허용 목록 검증 실패")
        cursor.execute("SELECT DISTINCT category_sub FROM category")
        if {row[0] for row in cursor.fetchall()} != ALLOWED_CATEGORY_SUB:
            raise ValueError("DB category_sub 허용 목록 검증 실패")
        if results["people"]["전체 row 수"] != source_population_rows:
            raise ValueError("인구 원본/DB 행 수가 다릅니다.")
        print(f"\n인구 원본/DB: {source_population_rows:,}/{results['people']['전체 row 수']:,}")
        print(f"차량 wide/long/DB: {source_vehicle_rows:,}/{expected_vehicle_rows:,}/{results['vehicle']['전체 row 수']:,}")
        if results["vehicle"]["전체 row 수"] != expected_vehicle_rows:
            raise ValueError("차량 wide→long/DB 행 수가 다릅니다.")
        failure_keys = {"중복", "NULL", "FK 누락", "형식 오류", "총계 main", "계 sub", "폐지 지역", "인구 이력 누락"}
        for table, values in results.items():
            for name, value in values.items():
                if any(key in name for key in failure_keys) and value != 0:
                    raise ValueError(f"DB 검증 실패: {table}.{name}={value}")


def main() -> None:
    regions = read_region_master()
    population_source = read_population()
    vehicle_source = read_vehicle()
    people = validate_population_region_mapping(population_source, regions)
    vehicle_mapped = validate_vehicle_region_mapping(vehicle_source, regions)
    dates = build_date_dimension(people, vehicle_mapped)
    categories = build_categories()
    vehicle = transform_vehicle_to_long(vehicle_mapped, categories)
    people = people[["region_id", "date_ym", "people_population"]]
    print(f"변환 완료: region={len(regions):,}, date={len(dates):,}, category={len(categories):,}, people={len(people):,}, vehicle={len(vehicle):,}")
    connection = connect()
    try:
        rebuild_analysis_schema(connection)
        load_all(connection, regions, dates, categories, people, vehicle)
        validate_database(connection, regions, len(population_source), len(vehicle_source), len(vehicle))
        connection.commit()
        print("\nETL 적재 및 검증 완료 (commit)")
    except Exception:
        connection.rollback()
        print("\nETL 실패: 전체 트랜잭션 rollback")
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
