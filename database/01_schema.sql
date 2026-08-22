-- =============================================
-- 1. 데이터베이스 생성
-- =============================================

CREATE DATABASE IF NOT EXISTS logistics_db
    DEFAULT CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE logistics_db;


-- =============================================
-- 2. 시군구지역 테이블
-- =============================================

CREATE TABLE region (
    region_id CHAR(5) NOT NULL COMMENT '분석지역ID',
    region_name VARCHAR(30) NOT NULL COMMENT '지역이름',

    PRIMARY KEY (region_id)
);


-- =============================================
-- 3. 날짜 테이블
-- =============================================

CREATE TABLE `date` (
    date_ym DATE NOT NULL COMMENT '날짜연월',

    date_half TINYINT NOT NULL COMMENT '반기',
    date_quarter TINYINT NOT NULL COMMENT '분기',
    date_year SMALLINT NOT NULL COMMENT '연도',
    date_month TINYINT NOT NULL COMMENT '월',

    PRIMARY KEY (date_ym)
);


-- =============================================
-- 4. 카테고리 테이블
-- =============================================

CREATE TABLE category (
    category_id INT NOT NULL AUTO_INCREMENT COMMENT '카테고리아이디',
    category_main VARCHAR(30) NOT NULL COMMENT '카테고리대분류',
    category_sub VARCHAR(30) NOT NULL COMMENT '카테고리소분류',

    PRIMARY KEY (category_id)
);


-- =============================================
-- 5. 관리자 테이블
-- =============================================

CREATE TABLE admin (
    admin_id INT NOT NULL AUTO_INCREMENT COMMENT '관리자아이디',
    admin_login_id VARCHAR(50) NOT NULL COMMENT '관리자로그인아이디',
    admin_pwd VARCHAR(255) NOT NULL COMMENT '관리자비밀번호',

    PRIMARY KEY (admin_id),
    UNIQUE KEY uq_admin_login_id (admin_login_id)
);


-- =============================================
-- 6. 인구 테이블
-- =============================================

CREATE TABLE people (
    region_id CHAR(5) NOT NULL COMMENT '분석지역ID',
    date_ym DATE NOT NULL COMMENT '날짜연월',
    people_population INT NOT NULL COMMENT '인구수',

    PRIMARY KEY (region_id, date_ym),

    CONSTRAINT fk_people_region
        FOREIGN KEY (region_id)
        REFERENCES region(region_id),

    CONSTRAINT fk_people_date
        FOREIGN KEY (date_ym)
        REFERENCES `date`(date_ym)
);


-- =============================================
-- 7. 차량등록 테이블
-- =============================================

CREATE TABLE vehicle (
    category_id INT NOT NULL COMMENT '카테고리아이디',
    region_id CHAR(5) NOT NULL COMMENT '분석지역ID',
    date_ym DATE NOT NULL COMMENT '날짜연월',
    vehicle_count INT NOT NULL COMMENT '차량등록대수',

    PRIMARY KEY (
        category_id,
        region_id,
        date_ym
    ),

    CONSTRAINT fk_vehicle_category
        FOREIGN KEY (category_id)
        REFERENCES category(category_id),

    CONSTRAINT fk_vehicle_region
        FOREIGN KEY (region_id)
        REFERENCES region(region_id),

    CONSTRAINT fk_vehicle_date
        FOREIGN KEY (date_ym)
        REFERENCES `date`(date_ym)
);


-- =============================================
-- 8. 문의 테이블
-- =============================================

CREATE TABLE inquiry (
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
