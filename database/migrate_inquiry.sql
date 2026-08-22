-- 기존 Docker 볼륨의 구형 inquiry를 최근 문의 화면 입력 구조로 교체한다.
-- 이미 신형 구조이면 아무 작업도 하지 않는다.
-- 구형 inquiry에 데이터가 있으면 임의 변환하거나 삭제하지 않고 중단한다.
USE logistics_db;

DROP PROCEDURE IF EXISTS migrate_inquiry;

DELIMITER //
CREATE PROCEDURE migrate_inquiry()
BEGIN
    DECLARE new_column_count INT DEFAULT 0;
    DECLARE inquiry_rows BIGINT DEFAULT 0;

    SELECT COUNT(*) INTO new_column_count
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = 'inquiry'
      AND COLUMN_NAME IN (
          'inquiry_id', 'company_name', 'manager_name', 'email', 'contact',
          'inquiry_type', 'inquiry_content', 'privacy_agreed', 'status', 'created_at'
      );

    IF new_column_count < 10 THEN
        SELECT COUNT(*) INTO inquiry_rows FROM inquiry;

        IF inquiry_rows > 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = '기존 inquiry 데이터가 있어 마이그레이션을 중단합니다.';
        END IF;

        CREATE TABLE inquiry_new (
            inquiry_id INT NOT NULL AUTO_INCREMENT COMMENT '문의아이디',
            company_name VARCHAR(100) NOT NULL COMMENT '회사명',
            manager_name VARCHAR(50) NOT NULL COMMENT '담당자명',
            email VARCHAR(255) NOT NULL COMMENT '이메일',
            contact VARCHAR(30) NULL COMMENT '연락처',
            inquiry_type VARCHAR(50) NOT NULL COMMENT '문의유형',
            inquiry_content VARCHAR(1000) NOT NULL COMMENT '문의내용',
            privacy_agreed BOOLEAN NOT NULL COMMENT '개인정보수집동의',
            status VARCHAR(20) NOT NULL DEFAULT '접수' COMMENT '처리상태',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '등록일시',
            PRIMARY KEY (inquiry_id)
        );

        RENAME TABLE inquiry TO inquiry_legacy, inquiry_new TO inquiry;
        DROP TABLE inquiry_legacy;
    END IF;
END//
DELIMITER ;

CALL migrate_inquiry();
DROP PROCEDURE migrate_inquiry;
