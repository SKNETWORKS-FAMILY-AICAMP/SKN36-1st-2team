"""문의 등록 query·service 단위 테스트와 실제 MySQL 통합 테스트."""

from __future__ import annotations

import unittest
from uuid import uuid4

from .db import MySQLDB
from .queries import insert_inquiry
from .services import create_inquiry


class FakeDB:
    """SQL과 파라미터를 기록하는 문의 단위 테스트용 DB 대역."""

    def __init__(self, inserted_id: int = 17) -> None:
        self.inserted_id = inserted_id
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> int:
        self.calls.append((sql, params))
        return self.inserted_id


class InquiryQueryTest(unittest.TestCase):
    """문의 INSERT가 사용자 값을 SQL에 합치지 않는지 확인한다."""

    def test_insert_uses_bound_parameters(self) -> None:
        db = FakeDB(inserted_id=23)
        content = "배송센터의 '입지'가 궁금합니다."

        inquiry_id = insert_inquiry(
            db=db,
            company_name="테스트물류",
            manager_name="홍길동",
            email="test@example.com",
            contact="010-1234-5678",
            inquiry_type="서비스 문의",
            inquiry_content=content,
            privacy_agreed=True,
        )

        self.assertEqual(inquiry_id, 23)
        self.assertEqual(len(db.calls), 1)
        sql, params = db.calls[0]
        self.assertEqual(sql.count("%s"), 7)
        self.assertNotIn(content, sql)
        self.assertEqual(params[5], content)


class InquiryServiceTest(unittest.TestCase):
    """필수값 검증과 성공 반환 구조를 DB 없이 확인한다."""

    def setUp(self) -> None:
        self.db = FakeDB(inserted_id=31)
        self.values = {
            "company_name": " 테스트물류 ",
            "manager_name": " 홍길동 ",
            "email": " test@example.com ",
            "contact": " 010-1234-5678 ",
            "inquiry_type": " 서비스 문의 ",
            "inquiry_content": " 물류 거점의 '점수'가 궁금합니다. ",
            "privacy_agreed": True,
        }

    def test_success_returns_generated_id_and_trims_input(self) -> None:
        result = create_inquiry(db=self.db, **self.values)

        self.assertTrue(result["success"])
        self.assertEqual(result["inquiry_id"], 31)
        _, params = self.db.calls[0]
        self.assertEqual(params[0], "테스트물류")
        self.assertEqual(params[3], "010-1234-5678")
        self.assertEqual(params[5], "물류 거점의 '점수'가 궁금합니다.")

    def test_blank_required_fields_do_not_insert(self) -> None:
        required = (
            "company_name",
            "manager_name",
            "email",
            "inquiry_type",
            "inquiry_content",
        )
        for key in required:
            with self.subTest(key=key):
                db = FakeDB()
                values = dict(self.values)
                values[key] = "   "
                result = create_inquiry(db=db, **values)
                self.assertFalse(result["success"])
                self.assertEqual(db.calls, [])

    def test_contact_is_optional(self) -> None:
        for contact in (None, "   "):
            with self.subTest(contact=contact):
                db = FakeDB()
                values = dict(self.values)
                values["contact"] = contact
                result = create_inquiry(db=db, **values)
                self.assertTrue(result["success"])
                self.assertIsNone(db.calls[0][1][3])

    def test_invalid_email_does_not_insert(self) -> None:
        db = FakeDB()
        values = dict(self.values)
        values["email"] = "invalid-email"
        result = create_inquiry(db=db, **values)
        self.assertFalse(result["success"])
        self.assertEqual(db.calls, [])

    def test_privacy_disagreement_does_not_insert(self) -> None:
        db = FakeDB()
        values = dict(self.values)
        values["privacy_agreed"] = False
        result = create_inquiry(db=db, **values)
        self.assertFalse(result["success"])
        self.assertEqual(db.calls, [])


class InquiryIntegrationTest(unittest.TestCase):
    """실제 MySQL에 문의를 저장·조회하고 생성한 테스트 행만 정리한다."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.db = MySQLDB.from_env()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.db.close()

    def test_insert_fetch_auto_id_and_apostrophe(self) -> None:
        email = f"inquiry-test-{uuid4().hex}@example.com"
        inquiry_id: int | None = None

        try:
            result = create_inquiry(
                db=self.db,
                company_name="테스트물류",
                manager_name="홍길동",
                email=email,
                contact="010-1234-5678",
                inquiry_type="서비스 문의",
                inquiry_content="물류센터의 '입지' 분석을 문의합니다.",
                privacy_agreed=True,
            )
            self.assertTrue(result["success"], result)
            inquiry_id = int(result["inquiry_id"])
            self.assertGreater(inquiry_id, 0)

            row = self.db.fetch_one(
                """SELECT inquiry_id, company_name, manager_name, email, contact,
                          inquiry_type, inquiry_content, privacy_agreed, status, created_at
                FROM inquiry
                WHERE inquiry_id = %s""",
                (inquiry_id,),
            )
            self.assertIsNotNone(row)
            self.assertEqual(row["email"], email)
            self.assertEqual(row["inquiry_content"], "물류센터의 '입지' 분석을 문의합니다.")
            self.assertEqual(row["status"], "접수")
            self.assertIsNotNone(row["created_at"])
        finally:
            if inquiry_id is not None:
                self.db.execute(
                    "DELETE FROM inquiry WHERE inquiry_id = %s",
                    (inquiry_id,),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
