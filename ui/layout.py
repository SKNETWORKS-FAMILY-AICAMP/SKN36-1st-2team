"""WAYLOGI 공통 레이아웃"""

import base64
from pathlib import Path

import streamlit as st

ROOT    = Path(__file__).resolve().parent.parent
CSS_DIR = ROOT / "assets" / "css"
IMG_DIR = ROOT / "assets" / "img"

NAV_LINKS = [
    ("서비스 소개",   "/"),
    ("데이터 조회",   "/data_search"),
    ("맞춤지역 추천", "/recommend"),
    ("FAQ · 문의",   "/inquiry"),
]


def html(s: str) -> None:
    """HTML 을 그린다. 마크다운이 4칸 이상 들여쓰기를 코드로 보므로 앞 공백을 제거한다."""
    st.markdown("\n".join(l.lstrip() for l in s.splitlines()),
                unsafe_allow_html=True)


def _bg_var(gif: str | None) -> str:
    """배경 GIF 를 base64 로 심어 CSS 변수로 돌려준다. 파일이 없으면 빈 문자열."""
    if not gif:
        return ""
    path = IMG_DIR / gif
    if not path.exists():
        return ""
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f':root {{ --hero-gif: url("data:image/gif;base64,{b64}"); }}'


def setup(page: str = "", active: str = "",
          title: str = "WAYLOGI", hero_gif=None, navpad: bool = True) -> None:
    """페이지의 첫 Streamlit 호출이어야 한다.

    page     : base.css 뒤에 덧붙일 CSS 이름 ("main", "explore" …)
    active   : 현재 메뉴 라벨. NAV_LINKS 와 같으면 밑줄 표시가 들어간다.
    hero_gif : assets/img/ 안의 배경 GIF 파일명
    """
    st.set_page_config(
        page_title=f"{title} | 물류 거점 예측 분석",
        page_icon=str(IMG_DIR / "waylogi-logo.png"),
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # ── CSS : base + 공용 컴포넌트 + 페이지별 + 배경 변수 ──
    # components.css 는 시군구 상세 패널처럼 여러 페이지에서 재사용할
    # 컴포넌트 스타일을 모아둔 시트다. base.css 의 색상 토큰(--brand 등)을
    # 그대로 참조하므로 반드시 base.css 다음, 페이지별 css 이전에 온다.
    css = (CSS_DIR / "base.css").read_text(encoding="utf-8")
    components_css = CSS_DIR / "components.css"
    if components_css.exists():
        css += "\n" + components_css.read_text(encoding="utf-8")
    if page:
        css += "\n" + (CSS_DIR / f"{page}.css").read_text(encoding="utf-8")
    css += "\n" + _bg_var(hero_gif)
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

    # ── 상단 바 ──
    links = "".join(
        f'<a href="{href}" target="_self"'
        + (' class="on"' if label == active else "")
        + f">{label}</a>"
        for label, href in NAV_LINKS
    )

    logo_b64 = base64.b64encode((IMG_DIR / "waylogi.png").read_bytes()).decode()
    mark = (
        '<a class="wl-mark" href="/" target="_self">'
        f'<img src="data:image/png;base64,{logo_b64}" class="wl-logo-img" '
        'alt="웨이로지"/>'
        '</a>'
    )
    pad = '<div class="wl-navpad"></div>' if navpad else ''
    st.markdown(
        f'<div class="wl-nav">{mark}'
        f'<nav class="wl-navlinks">{links}</nav>'
        f'</div>{pad}',
        unsafe_allow_html=True,
    )


def footer() -> None:
    """읽고 끝나는 페이지에서만 부른다. 지도처럼 도구형 화면에는 넣지 않는다."""
    html("""
    <footer class="wl-foot">
    <div class="wl-foot-in">
    <span>WAYLOGI &#183; SKNetworks Family AI Camp</span>
    <span>36기 2team 1st part project</span>
    <span>나지인 임성경 문희영 차용우 &#183; 2026</span>
    </div>
    </footer>
    """)
