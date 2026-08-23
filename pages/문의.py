"""FAQ · 문의 랜딩, FAQ 목록, 문의 등록 폼."""

import streamlit as st
from pymysql import MySQLError

from ui.backend import get_db
from ui.layout import footer, html, setup
from web.backend import create_inquiry

INQUIRY_TYPES = ("서비스 이용 문의", "데이터 문의", "지표 해석 문의", "기타 문의")
FAQS = (
    ("증가율은 어떻게 계산하나요?", "증가율은 이전 기준 시점 대비 현재 값의 변화 비율로 계산합니다. 이전 값이 0이거나 데이터가 없는 경우에는 증가율을 제공하지 않을 수 있습니다."),
    ("화물차 등록대수는 어떤 기준으로 집계되나요?", "화물차 등록대수는 자동차 등록 통계의 지역별·용도별 등록 자료를 기준으로 집계합니다. 화면에 표시된 기준 월과 행정구역을 함께 확인해 주세요."),
    ("종합점수가 높으면 반드시 좋은 입지인가요?", "종합점수는 산업성, 성장성, 수요성 지표를 비교하기 위한 참고값입니다. 실제 입지 결정에는 비용, 접근성, 규제, 현장 조건 등 추가 검토가 필요합니다."),
    ("데이터는 언제 갱신되나요?", "원천 데이터의 최신 공표 자료가 확보되고 검증이 끝난 뒤 갱신됩니다. 각 화면에 표시된 기준 월을 통해 현재 반영 시점을 확인할 수 있습니다."),
    ("중요도 진단을 다시 할 수 있나요?", "네. 유망지역 추천 화면에서 중요도 진단을 다시 진행하면 선택한 조건을 기준으로 추천 결과를 새로 확인할 수 있습니다."),
    ("시군구는 몇 개인가요?", "서비스에서 제공하는 시군구 수는 현재 분석 DB에 적재된 행정구역을 기준으로 하며, 행정구역 개편과 데이터 기준 시점에 따라 달라질 수 있습니다."),
)


def _set_view(view: str) -> None:
    """URL의 view 값으로 같은 페이지 안의 표시 섹션을 전환한다."""
    if view == "landing":
        st.query_params.clear()
    else:
        st.query_params["view"] = view


def _advance_form_generation() -> None:
    """새 위젯 키를 사용하게 해 문의 입력값을 초기화한다."""
    st.session_state.inquiry_form_generation = st.session_state.get("inquiry_form_generation", 0) + 1


def _render_landing() -> None:
    html("""
    <section class="wl-support-hero">
      <div class="wl-support-eyebrow">CONTACT</div>
      <h1>이 순위만으로<br class="wl-mobile-break"> 결정할 수는 없습니다</h1>
      <p>순위에 담기지 않은 것들 — 임대 시세, 인허가, 인접 물류망은 웨이로지가 답하지 못합니다.<br>무엇이 더 필요한지 알려주시면 다음 버전에 반영합니다.</p>
    </section>
    """)
    with st.container(key="support_actions"):
        _, inquiry_col, faq_col, _ = st.columns([1.25, 1, 1, 1.25], gap="small")
        inquiry_col.button("문의 남기기", type="primary", use_container_width=True, on_click=_set_view, args=("inquiry",))
        faq_col.button("자주 묻는 질문", use_container_width=True, on_click=_set_view, args=("faq",))
    html("""
    <section class="wl-faq-preview" aria-label="자주 묻는 질문 미리보기">
      <article><h2>점수는 어떻게 계산되나요?</h2><p>지표별 전국 백분위를 세 축으로 묶고 가중 평균합니다. 화면에서 지표별 순위까지 펼쳐볼 수 있습니다.</p></article>
      <article><h2>화물차 등록지가 실제 운행지와 다르지 않나요?</h2><p>맞습니다. 등록은 차고지 기준이라 대리 지표입니다. 따라서 순위를 결론이 아니라 후보로 활용합니다.</p></article>
      <article><h2>데이터는 언제까지인가요?</h2><p>2023년 7월부터 2026년 7월까지의 월 단위 데이터를 기준으로 제공합니다.</p></article>
    </section>
    """)


def _render_faq() -> None:
    html("""
    <section class="wl-inner-head">
      <div class="wl-support-eyebrow">FAQ</div><h1>궁금한 내용을 확인해 보세요</h1>
      <p>웨이로지의 데이터와 분석 결과에 대해 자주 묻는 질문입니다.</p>
    </section>
    """)
    with st.container(key="support_back"):
        st.button("← 처음으로", on_click=_set_view, args=("landing",))
    with st.container(key="faq_list"):
        for question, answer in FAQS:
            with st.expander(question):
                st.write(answer)


def _render_inquiry() -> None:
    html("""
    <section class="wl-inner-head">
      <div class="wl-support-eyebrow">CONTACT</div><h1>필요한 것을 들려주세요</h1>
      <p>남겨주신 내용은 서비스를 더 나은 방향으로 만드는 데 소중히 활용됩니다.</p>
    </section>
    """)
    with st.container(key="support_back"):
        st.button("← 처음으로", on_click=_set_view, args=("landing",))
    if success_message := st.session_state.pop("inquiry_success_message", None):
        st.success(success_message)

    generation = st.session_state.get("inquiry_form_generation", 0)
    key = lambda name: f"inquiry_{name}_{generation}"
    _, form_col, _ = st.columns([0.12, 1, 0.12])
    with form_col:
        html('<div class="wl-form-intro"><h2>문의 정보</h2><p><span>*</span> 표시는 필수 입력 항목입니다.</p></div>')
        with st.form(f"inquiry_form_{generation}"):
            company_col, manager_col = st.columns(2, gap="medium")
            company_name = company_col.text_input("회사명 *", max_chars=100, key=key("company"))
            manager_name = manager_col.text_input("담당자명 *", max_chars=50, key=key("manager"))
            email_col, contact_col = st.columns(2, gap="medium")
            email = email_col.text_input("이메일 *", max_chars=255, placeholder="name@company.com", key=key("email"))
            contact = contact_col.text_input("연락처 (선택)", max_chars=30, placeholder="010-0000-0000", key=key("contact"))
            inquiry_type = st.selectbox("문의 유형 *", ("선택해주세요", *INQUIRY_TYPES), key=key("type"))
            inquiry_content = st.text_area("문의 내용 *", max_chars=1000, height=180, key=key("content"))
            privacy_agreed = st.checkbox("개인정보 수집 및 이용에 동의합니다. *", key=key("privacy"))
            cancel_col, submit_col = st.columns(2, gap="medium")
            cancelled = cancel_col.form_submit_button("취소", use_container_width=True)
            submitted = submit_col.form_submit_button("문의 보내기", type="primary", use_container_width=True)

        if cancelled:
            _advance_form_generation()
            _set_view("landing")
            st.rerun()
        if submitted:
            selected_type = "" if inquiry_type == "선택해주세요" else inquiry_type
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


setup(page="inquiry", active="FAQ · 문의", title="FAQ · 문의")
view = st.query_params.get("view", "landing")
if view == "faq":
    _render_faq()
elif view == "inquiry":
    _render_inquiry()
else:
    _render_landing()
footer()
