"""FAQ 검색과 문의 등록 화면."""

import streamlit as st
from pymysql import MySQLError

from ui.backend import get_db
from ui.layout import html, setup
from web.backend import create_inquiry


INQUIRY_TYPES = ("서비스 이용 문의", "데이터 문의", "지표 해석 문의", "기타 문의")
FAQS = (
    {"category": "지표 해석", "question": "증가율은 어떻게 계산하나요?", "answer": "증가율은 이전 기준 시점 대비 현재 값의 변화 비율로 계산합니다. 이전 값이 0이거나 데이터가 없는 경우에는 증가율을 제공하지 않을 수 있습니다."},
    {"category": "데이터", "question": "화물차 등록대수는 어떤 기준으로 집계되나요?", "answer": "화물차 등록대수는 자동차 등록 통계의 지역별·용도별 등록 자료를 기준으로 집계합니다. 화면에 표시된 기준 월과 행정구역을 함께 확인해 주세요."},
    {"category": "지표 해석", "question": "종합점수가 높으면 반드시 좋은 입지인가요?", "answer": "종합점수는 산업성, 성장성, 수요성 지표를 비교하기 위한 참고값입니다. 실제 입지 결정에는 비용, 접근성, 규제, 현장 조건 등 추가 검토가 필요합니다."},
    {"category": "데이터", "question": "데이터는 언제 갱신되나요?", "answer": "원천 데이터의 최신 공표 자료가 확보되고 검증이 끝난 뒤 갱신됩니다. 각 화면에 표시된 기준 월을 통해 현재 반영 시점을 확인할 수 있습니다."},
    {"category": "서비스 이용", "question": "중요도 진단을 다시 할 수 있나요?", "answer": "네. 유망지역 추천 화면에서 중요도 진단을 다시 진행하면 선택한 조건을 기준으로 추천 결과를 새로 확인할 수 있습니다."},
    {"category": "서비스 이용", "question": "시군구는 몇 개인가요?", "answer": "서비스에서 제공하는 시군구 수는 현재 분석 DB에 적재된 행정구역을 기준으로 하며, 행정구역 개편과 데이터 기준 시점에 따라 달라질 수 있습니다."},
)


def _set_view(view: str) -> None:
    """같은 페이지에서 FAQ와 문의 탭을 전환한다."""
    if view == "faq":
        st.query_params.clear()
    else:
        st.query_params["view"] = view


def _advance_form_generation() -> None:
    """새 위젯 키를 사용하게 해 문의 입력값을 초기화한다."""
    st.session_state.inquiry_form_generation = st.session_state.get("inquiry_form_generation", 0) + 1


def _render_tabs(view: str) -> None:
    with st.container(key="support_tabs"):
        faq_col, inquiry_col, rest = st.columns([0.7, 0.95, 8.35], gap="small")
        faq_col.button("① FAQ", key="faq_tab", type="primary" if view == "faq" else "secondary", on_click=_set_view, args=("faq",))
        inquiry_col.button("② 문의하기", key="inquiry_tab", type="primary" if view == "inquiry" else "secondary", on_click=_set_view, args=("inquiry",))


def _render_faq() -> None:
    html("""
    <section class="wl-page-head">
      <h1>자주 묻는 질문</h1>
      <p>질문을 선택하면 답변을 확인할 수 있습니다.</p>
    </section>
    """)

    with st.container(key="faq_list"):
        for faq in FAQS:
            with st.expander(faq["question"]):
                st.write(faq["answer"] or "답변을 준비하고 있습니다.")


def _render_inquiry() -> None:
    html("""
    <section class="wl-page-head">
      <h1>문의하기</h1>
      <p>문의 내용을 등록하면 관리자가 확인한 뒤 입력하신 연락처로 답변드립니다.</p>
    </section>
    """)
    if success_message := st.session_state.pop("inquiry_success_message", None):
        st.success(success_message)

    form_col, guide_col = st.columns([1, 1], gap="small")
    generation = st.session_state.get("inquiry_form_generation", 0)
    key = lambda name: f"inquiry_{name}_{generation}"

    with form_col:
        with st.form(f"inquiry_form_{generation}"):
            company_col, manager_col = st.columns(2, gap="medium")
            company_name = company_col.text_input("회사명 :red[필수]", max_chars=100, key=key("company"))
            manager_name = manager_col.text_input("담당자명 :red[필수]", max_chars=50, key=key("manager"))
            email_col, contact_col = st.columns(2, gap="medium")
            email = email_col.text_input("이메일 :red[필수]", max_chars=255, key=key("email"))
            contact = contact_col.text_input("연락처 :gray[선택]", max_chars=30, key=key("contact"))
            inquiry_type = st.selectbox("문의 유형 :red[필수]", ("선택해 주세요", *INQUIRY_TYPES), key=key("type"))
            inquiry_content = st.text_area("문의 내용 :red[필수]", max_chars=1000, height=130, key=key("content"))
            privacy_agreed = st.checkbox("개인정보 수집 및 이용에 동의합니다 (필수)", key=key("privacy"))
            cancel_col, submit_col = st.columns(2, gap="small")
            cancelled = cancel_col.form_submit_button("취소", use_container_width=True)
            submitted = submit_col.form_submit_button("문의 보내기", type="primary", use_container_width=True)

        if cancelled:
            _advance_form_generation()
            st.rerun()
        if submitted:
            selected_type = "" if inquiry_type == "선택해 주세요" else inquiry_type
            try:
                result = create_inquiry(
                    db=get_db(), company_name=company_name, manager_name=manager_name,
                    email=email, contact=contact, inquiry_type=selected_type,
                    inquiry_content=inquiry_content, privacy_agreed=privacy_agreed,
                )
            except (MySQLError, OSError, ValueError):
                result = {"success": False, "message": "문의 등록 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}
            if result["success"]:
                st.session_state.inquiry_success_message = result["message"]
                _advance_form_generation()
                st.rerun()
            else:
                st.error(result["message"])

    with guide_col:
        faq_examples = "".join(f"<li>{faq['question']}</li>" for faq in FAQS[:3])
        html(f"""
        <aside class="wl-guide-card wl-guide-card-blue">
          <h2>답변은 이렇게 진행됩니다</h2>
          <div class="wl-guide-step"><b>1</b><div><strong>문의 접수</strong><span>작성하신 내용이 관리자에게 전달됩니다</span></div></div>
          <div class="wl-guide-step"><b>2</b><div><strong>관리자 확인</strong><span>접수된 내용을 확인하고 답변을 준비합니다</span></div></div>
          <div class="wl-guide-step"><b>3</b><div><strong>답변 등록</strong><span>입력하신 이메일 또는 연락처로 안내드립니다</span></div></div>
        </aside>
        <aside class="wl-guide-card wl-guide-faq">
          <h2>자주 묻는 질문 먼저 확인</h2>
          <p>비슷한 질문이 이미 등록되어 있을 수 있습니다</p>
          <ul>{faq_examples}</ul>
        </aside>
        """)


setup(page="inquiry", active="FAQ · 문의", title="FAQ · 문의")
view = st.query_params.get("view", "faq")
_render_tabs(view)
if view == "inquiry":
    _render_inquiry()
else:
    _render_faq()
