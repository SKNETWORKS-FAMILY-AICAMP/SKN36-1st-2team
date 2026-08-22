# SKN36-1st-2team

## 분석 DB 시작하기

새로 clone한 팀원은 다음 명령만 실행하면 됩니다.

```bash
cd database
docker compose up -d
```

MySQL 8.4 컨테이너(`skn36-2team-db`)가 호스트 포트 `3307`에서 시작되며,
빈 데이터 디렉터리를 처음 초기화할 때 `01_schema.sql`과 `02_seed.sql`을 파일명
순서대로 실행합니다. 그 결과 `region`, `date`, `category`, `people`, `vehicle`에는
분석용 초기 데이터가 들어가고 `member`, `inquiry`는 빈 테이블로 생성됩니다.

> MySQL의 `/docker-entrypoint-initdb.d/` 파일은 `database/mysql_data/`가 비어 있는
> 최초 실행에만 실행됩니다. 기존 `mysql_data`가 있으면 `docker compose up -d`만으로
> schema나 seed가 다시 적용되지 않습니다.

## 기존 개발 DB 갱신하기

프로젝트 루트에서 Python 가상환경과 접속 설정을 준비합니다.

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
pip install -r etl/requirements.txt
Copy-Item .env.example .env
python etl/load_data.py
```

macOS/Linux에서는 활성화와 환경 파일 복사를 다음처럼 실행합니다.

```bash
source .venv/bin/activate
cp .env.example .env
python etl/load_data.py
```

`load_data.py`는 분석 데이터 5개 테이블만 `vehicle → people → category → date → region`
순서로 재구축한 뒤 `region → date → category → people → vehicle` 순서로 전체
재적재합니다. 지역 ID는 `자동차등록현황_데이터셋.xlsx`의 `지역마스터.분석지역ID`
(`CHAR(5)`)를 그대로 사용하고, 차량은 합계 컬럼을 제외한 12개 원천 카테고리만
저장합니다. `member`, `inquiry` 테이블과 데이터는 변경하지 않습니다. 원본 변환은 DB
변경 전에 검증하며, 적재·검증이 실패하면 데이터 INSERT 트랜잭션을 rollback합니다.

## 초기 seed 다시 만들기

ETL 적재 및 콘솔 검증이 성공한 후 다음을 실행합니다.

```bash
python etl/export_seed.py
```

현재 `logistics_db`의 `region`, `date`, `category`, `people`, `vehicle` 데이터만 UTF-8
`database/02_seed.sql`로 내보냅니다. `member`, `inquiry` 및 CREATE TABLE 문은 포함하지
않습니다. 생성된 seed는 새 DB에서만 자동 적용되므로, 기존 개발 DB 갱신에는 위 ETL을
사용하세요.

MySQL을 실행할 수 없는 환경에서 동일한 검증·변환 결과로 seed만 재생성해야 할 때는
`python etl/build_seed_from_excel.py`를 사용할 수 있습니다. 팀 공유용 최종 seed는
가능하면 DB 적재 검증 후 `export_seed.py`로 다시 생성하세요.
