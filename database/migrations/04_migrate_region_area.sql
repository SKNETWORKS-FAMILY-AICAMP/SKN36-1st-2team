-- 신규 DB 초기화용이 아니며, area_km2가 없는 기존 DB에서만 수동 실행한다.
USE logistics_db;

ALTER TABLE region
    ADD COLUMN area_km2 DECIMAL(14,4) NULL
    COMMENT 'admdongkor 시군구 면적(km²)' AFTER region_name;
