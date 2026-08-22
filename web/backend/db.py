# MySQL 연결과 fetch_one(), fetch_all() 제공

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class MySQLDB:
    """하나의 MySQL 연결을 관리하고 조회 결과를 dict 형태로 제공한다."""

    def __init__(
        self,
        host: str,
        port: int,
        user: str,
        password: str,
        database: str,
    ) -> None:
        # DictCursor를 사용하면 컬럼명을 key로 갖는 dict가 반환되어 화면 코드가 읽기 쉽다.
        # 조회 전용 계층이므로 별도 commit이 필요 없도록 autocommit을 사용한다.
        self._connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            cursorclass=DictCursor,
            autocommit=True,
        )

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> "MySQLDB":
        """프로젝트 .env의 접속정보로 MySQLDB 인스턴스를 생성한다."""
        # 비밀번호 같은 접속정보를 코드에 직접 적지 않고 .env에서 읽는다.
        load_dotenv(Path(env_path) if env_path is not None else PROJECT_ROOT / ".env")
        return cls(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3307")),
            user=os.getenv("DB_USER", "root"),
            password=os.getenv("DB_PASSWORD", ""),
            database=os.getenv("DB_NAME", "logistics_db"),
        )

    def fetch_one(
        self,
        sql: str,
        params: tuple[object, ...] = (),
    ) -> dict[str, Any] | None:
        """SELECT 결과 한 행을 dict로 반환하며 결과가 없으면 None을 반환한다."""
        # 연결이 끊겼다면 자동 재연결한 뒤, 단건 조회용 fetchone()만 호출한다.
        self._connection.ping(reconnect=True)
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
        return dict(row) if row is not None else None

    def fetch_all(
        self,
        sql: str,
        params: tuple[object, ...] = (),
    ) -> list[dict[str, Any]]:
        """SELECT 결과 전체를 list[dict]로 반환하며 결과가 없으면 []를 반환한다."""
        # 목록과 기간 조회는 여러 행이 필요하므로 fetchall()을 사용한다.
        self._connection.ping(reconnect=True)
        with self._connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [dict(row) for row in rows]

    def execute(
        self,
        sql: str,
        params: tuple[object, ...] = (),
    ) -> int:
        """쓰기 SQL을 트랜잭션으로 실행하고 생성된 AUTO_INCREMENT ID를 반환한다."""
        self._connection.ping(reconnect=True)
        try:
            # autocommit 연결에서도 명시적으로 트랜잭션을 시작해 성공과 실패를 구분한다.
            self._connection.begin()
            with self._connection.cursor() as cursor:
                cursor.execute(sql, params)
                inserted_id = int(cursor.lastrowid)
            self._connection.commit()
            return inserted_id
        except Exception:
            # 실행 중 오류가 나면 일부 변경도 남지 않도록 트랜잭션을 되돌린다.
            self._connection.rollback()
            raise

    def close(self) -> None:
        """사용이 끝난 MySQL 연결을 닫는다."""
        self._connection.close()

    def __enter__(self) -> "MySQLDB":
        """with 문 안에서 현재 DB 인스턴스를 사용할 수 있게 반환한다."""
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        """with 문을 벗어날 때 성공·실패 여부와 관계없이 연결을 닫는다."""
        self.close()
