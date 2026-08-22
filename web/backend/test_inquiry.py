"""문의 등록의 입력 검증과 파라미터 바인딩을 DB 없이 확인하는 테스트."""

from __future__ import annotations

import unittest

from .queries import insert_inquiry
from .services import create_inquiry


class FakeDB:
    """실제 INSERT 대신 전달받은 SQL과 파라미터를 기록한다."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, sql: str, params: tuple[object, ...] = ()) -> int:
        self.calls.append((sql, params))
        return 1


class InquiryQueryTest(unittest.TestCase):
    def test_insert_uses_bound_parameters(self) -> None:
        db = FakeDB()
        inquiry_id = insert_inquiry(
            db, "테스트물류", "홍길동", "test@example.com", "010-1234-5678",
            "서비스 문의", "문의 내용", True,
        )
        self.assertEqual(inquiry_id, 1)
        sql, params = db.calls[0]
        self.assertEqual(sql.count("%s"), 7)
        self.assertNotIn("테스트물류", sql)
        self.assertEqual(params[0], "테스트물류")


class InquiryServiceTest(unittest.TestCase):
    def valid_values(self) -> dict:
        return {
            "company_name": " 테스트물류 ",
            "manager_name": " 홍길동 ",
            "email": " test@example.com ",
            "contact": " 010-1234-5678 ",
            "inquiry_type": " 서비스 문의 ",
            "inquiry_content": " 물류 거점 분석 서비스 관련 문의입니다. ",
            "privacy_agreed": True,
        }

    def test_success_and_whitespace_normalization(self) -> None:
        db = FakeDB()
        result = create_inquiry(db=db, **self.valid_values())
        self.assertEqual(result, {"success": True, "message": "문의가 정상적으로 등록되었습니다."})
        self.assertEqual(db.calls[0][1][0], "테스트물류")
        self.assertEqual(db.calls[0][1][3], "010-1234-5678")

    def test_blank_required_fields_do_not_insert(self) -> None:
        for field in ("company_name", "manager_name", "email", "inquiry_type", "inquiry_content"):
            with self.subTest(field=field):
                db = FakeDB()
                values = self.valid_values()
                values[field] = "   "
                result = create_inquiry(db=db, **values)
                self.assertFalse(result["success"])
                self.assertEqual(db.calls, [])

    def test_contact_is_optional(self) -> None:
        for contact in (None, "   "):
            with self.subTest(contact=contact):
                db = FakeDB()
                values = self.valid_values()
                values["contact"] = contact
                self.assertTrue(create_inquiry(db=db, **values)["success"])
                self.assertIsNone(db.calls[0][1][3])

    def test_invalid_email_does_not_insert(self) -> None:
        db = FakeDB()
        values = self.valid_values()
        values["email"] = "invalid-email"
        self.assertFalse(create_inquiry(db=db, **values)["success"])
        self.assertEqual(db.calls, [])

    def test_privacy_disagreement_does_not_insert(self) -> None:
        db = FakeDB()
        values = self.valid_values()
        values["privacy_agreed"] = False
        self.assertFalse(create_inquiry(db=db, **values)["success"])
        self.assertEqual(db.calls, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
