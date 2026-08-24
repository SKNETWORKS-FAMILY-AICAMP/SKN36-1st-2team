"""FAQ 검색과 문의 등록 화면."""

import streamlit as st
from pymysql import MySQLError

from ui.backend import get_db
from ui.layout import html, setup
from web.backend import create_inquiry


INQUIRY_TYPES = ("서비스 이용 문의", "데이터 문의", "지표 해석 문의", "기타 문의")
INQUIRY_GUIDE_QUESTIONS = (
    "증가율은 어떻게 계산하나요?",
    "화물차 등록대수는 어떤 기준으로 집계되나요?",
    "종합점수가 높으면 반드시 좋은 입지인가요?",
)
FAQS = (
    {
        "category": "지표 해석",
        "question": "지역 추천 결과는 어떻게 계산되나요?",
        "answer": "지역별 데이터를 **산업성·성장성·수요성** 세 가지 기준으로 분석합니다. 각 세부지표를 전국 지역 기준의 백분위 점수로 변환한 뒤 기준별 점수를 계산하고, 사용자가 설정한 중요도를 반영해 최종 추천 점수와 순위를 산출합니다.",
    },
    {
        "category": "지표 해석",
        "question": "산업성·성장성·수요성은 각각 무엇을 의미하나요?",
        "answer": "**산업성**은 현재 해당 지역의 물류 산업 기반과 특화 정도를 나타내며, 영업용 화물 비중·입지계수(LQ)·인구 1천 명당 화물차를 활용합니다.\n\n**성장성**은 앞으로 물류 수요가 성장할 가능성을 나타내며, 인구-화물 디커플링·12개월 가속도·추세 지속성·영업용 전환율·화물차 전년동월비·안정성을 활용합니다.\n\n**수요성**은 해당 지역의 잠재적인 물류 수요 규모를 나타내며, 자체 인구·인구 밀도·인구 증가율을 활용합니다.",
    },
    {
        "category": "지표 해석",
        "question": "기준을 바꾸면 추천 순위가 달라지는 이유는 무엇인가요?",
        "answer": "지역마다 산업성·성장성·수요성 점수가 다르기 때문입니다. 사용자가 어떤 기준을 더 중요하게 설정하느냐에 따라 각 점수의 반영 비율이 달라지고, 이에 따라 최종 점수와 추천 순위도 다시 계산됩니다.\n\n예를 들어 성장성을 높게 설정하면 현재 규모가 큰 지역보다 **최근 성장 흐름이 좋은 지역**이 더 높은 순위에 나타날 수 있습니다.",
    },
    {
        "category": "지표 해석",
        "question": "추천 점수가 높으면 무조건 물류 거점으로 좋은 지역인가요?",
        "answer": "아닙니다. 추천 점수는 화물차 등록과 인구 등 공공데이터를 기반으로 지역을 비교하기 위한 **의사결정 참고 지표**입니다. 실제 물류 거점 선정 시에는 토지 가격, 교통망, 물류시설 현황, 기업별 운영 조건 등 추가적인 요소도 함께 검토하는 것이 좋습니다.",
    },
    {
        "category": "데이터",
        "question": "화물차 등록대수에는 어떤 차량이 포함되나요?",
        "answer": "WAYLOGI에서는 차량등록 데이터 중 **화물 관용·화물 자가용·화물 영업용** 차량을 합산하여 화물차 등록대수를 계산합니다. 이를 활용해 지역별 화물차 규모와 비율, 증가 추이 등을 분석합니다.",
    },
    {
        "category": "지표 해석",
        "question": "지역별 추천 결과가 크게 다른 이유는 무엇인가요?",
        "answer": "지역마다 화물차 등록 현황, 영업용 화물 비중, 물류 특화도, 인구 규모와 밀도, 최근 성장 추이 등이 서로 다르기 때문입니다. 동일한 기준을 적용해도 각 지역의 데이터 특성이 다르므로 점수와 순위에 차이가 발생합니다.",
    },
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
            company_name = company_col.text_input(
                "회사명 :red[필수]", max_chars=100, key=key("company"),
                help="한글, 영문, 숫자와 일반적인 회사명 기호만 입력할 수 있습니다.",
            )
            manager_name = manager_col.text_input(
                "담당자명 :red[필수]", max_chars=50, key=key("manager"),
                help="한글, 영문, 공백, 하이픈(-), 작은따옴표(')만 입력할 수 있습니다.",
            )
            email_col, contact_col = st.columns(2, gap="medium")
            email = email_col.text_input(
                "이메일 :red[필수]", max_chars=255, key=key("email"),
                help="예: name@example.com",
            )
            contact = contact_col.text_input(
                "연락처 :gray[선택]", max_chars=30, key=key("contact"),
                help="숫자, 공백, 하이픈(-), 괄호, 국가번호(+)를 사용할 수 있습니다.",
            )
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
        faq_examples = "".join(f"<li>{question}</li>" for question in INQUIRY_GUIDE_QUESTIONS)
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
