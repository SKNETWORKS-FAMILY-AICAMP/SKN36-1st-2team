USE logistics_db;

ALTER TABLE region
    ADD COLUMN area_km2 DECIMAL(14,4) NULL
    COMMENT 'admdongkor 시군구 면적(km²)' AFTER region_name;
