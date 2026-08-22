-- 기존 빈 member/inquiry를 새 admin/inquiry 구조로 교체한다.
-- 기존 데이터가 하나라도 있으면 SIGNAL로 중단하므로 먼저 백업/이관 방안을 정해야 한다.
USE logistics_db;

DELIMITER //
CREATE PROCEDURE migrate_admin_inquiry()
BEGIN
    DECLARE member_rows BIGINT DEFAULT 0;
    DECLARE inquiry_rows BIGINT DEFAULT 0;

    SELECT COUNT(*) INTO member_rows FROM member;
    SELECT COUNT(*) INTO inquiry_rows FROM inquiry;
    IF member_rows > 0 OR inquiry_rows > 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'member 또는 inquiry에 기존 데이터가 있어 마이그레이션을 중단합니다.';
    END IF;

    -- 새 테이블 생성이 모두 성공하기 전까지 기존 테이블을 유지한다.
    CREATE TABLE admin_new (
        admin_id INT NOT NULL AUTO_INCREMENT COMMENT '관리자아이디',
        admin_login_id VARCHAR(50) NOT NULL COMMENT '관리자로그인아이디',
        admin_pwd VARCHAR(255) NOT NULL COMMENT '관리자비밀번호',
        PRIMARY KEY (admin_id),
        UNIQUE KEY uq_admin_login_id (admin_login_id)
    );

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

    -- 네 테이블 이름을 하나의 RENAME 문으로 교체한다.
    RENAME TABLE
        inquiry TO inquiry_legacy,
        member TO member_legacy,
        admin_new TO admin,
        inquiry_new TO inquiry;

    -- 기존 테이블은 비어 있음을 위에서 확인했다. FK 자식부터 제거한다.
    DROP TABLE inquiry_legacy;
    DROP TABLE member_legacy;
END//
DELIMITER ;

CALL migrate_admin_inquiry();
DROP PROCEDURE migrate_admin_inquiry;
