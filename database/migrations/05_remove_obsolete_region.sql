-- 기존 Docker MySQL 볼륨에서 폐지 지역 R0167(충청북도 청원군)만 제거한다.
-- 신규 seed에는 R0167이 없으므로, 해당 지역이 남은 기존 DB에서만 수동 실행한다.
-- 원본 Excel, 다른 지역, category/date/admin/inquiry 데이터는 변경하지 않는다.
USE logistics_db;

START TRANSACTION;

-- region을 참조하는 자식 테이블부터 삭제해야 FK 위반이 발생하지 않는다.
DELETE FROM vehicle WHERE region_id = 'R0167';
DELETE FROM people WHERE region_id = 'R0167';
DELETE FROM region WHERE region_id = 'R0167';

COMMIT;

-- 세 결과가 모두 0이어야 정리가 완료된 것이다.
SELECT COUNT(*) AS obsolete_region_count FROM region WHERE region_id = 'R0167';
SELECT COUNT(*) AS obsolete_people_count FROM people WHERE region_id = 'R0167';
SELECT COUNT(*) AS obsolete_vehicle_count FROM vehicle WHERE region_id = 'R0167';

-- 지역 목록 중 전 기간 인구 이력이 한 건도 없는 지역 수다. 정상 결과는 0이다.
SELECT COUNT(*) AS regions_without_population
FROM region r
LEFT JOIN (
    SELECT DISTINCT region_id
    FROM people
) p ON p.region_id = r.region_id
WHERE p.region_id IS NULL;
