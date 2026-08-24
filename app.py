import streamlit as st
from pymysql import MySQLError
from ui.backend import get_db
from ui.layout import setup
from ui.layout import setup,html
from ui.layout import footer
from web.backend import get_dashboard_summary
# setup(page="main", active="서비스 소개", hero_gif="hero.gif")

setup(page="main", active="서비스 소개",navpad=False)

TARGET_MONTH = "2026-07"


@st.cache_data(ttl=3600)
def load_dashboard_summary():
    return get_dashboard_summary(get_db(), TARGET_MONTH)


try:
    dashboard = load_dashboard_summary()
except (MySQLError, OSError, ValueError):
    dashboard = {
        "national_freight_count": None,
        "year_over_year_growth_rate": None,
        "region_count": None,
    }


def display_number(value, suffix="", decimals=0):
    if value is None:
        return "데이터 없음"
    return f"{value:,.{decimals}f}{suffix}"


freight_count = display_number(dashboard["national_freight_count"])
growth_rate = display_number(dashboard["year_over_year_growth_rate"], "%", decimals=1)
region_count = display_number(dashboard["region_count"])

HERO = f"""
<section class="wl-hero">
<div class="wl-hero-inner">

<h1 class="wl-h1">
데이터로 찾는<br>우리 회사의 다음 물류 거점
</h1>

<p class="wl-sub">
전국 {region_count}개 시군구의 화물차&#183;인구 데이터를 분석해,
기업이 어디에 거점을 두면 좋을지 알려드립니다.
</p>

<div class="wl-cta-row">
<a class="wl-btn wl-btn-primary" href="/유망지역_추천" target="_self">유망지역 추천 받기</a>
<a class="wl-btn wl-btn-ghost"   href="/데이터_조회"   target="_self">데이터 먼저 보기</a>
</div>

<div class="wl-stats">
<div class="wl-stat">
<div class="wl-stat-l">전국 화물차 등록대수</div>
<div class="wl-stat-n">{freight_count}</div>
<div class="wl-stat-s">2026년 7월 기준</div>
</div>
<div class="wl-stat">
<div class="wl-stat-l">전년 동월 대비 증가율</div>
<div class="wl-stat-n">{growth_rate}</div>
<div class="wl-stat-s">2025.07 &#8594; 2026.07</div>
</div>
<div class="wl-stat">
<div class="wl-stat-l">분석 대상 지역</div>
<div class="wl-stat-n">{region_count}</div>
<div class="wl-stat-s">시군구 단위 &#183; 37개월</div>
</div>
</div>

</div>
</section>




"""



st.markdown(HERO, unsafe_allow_html=True)

# 지도 실루엣 위에 상위 지역이 점등되는 그림
MAP_SVG = """
<svg viewBox="0 0 300 380" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
<path d="M118 22 L150 14 L176 30 L188 58 L182 84 L196 104 L216 112 L226 136
L218 160 L232 176 L228 202 L206 216 L212 240 L196 262 L200 286 L182 306
L186 330 L164 344 L140 336 L126 316 L104 322 L84 306 L88 282 L70 264
L78 240 L62 220 L72 196 L58 176 L70 152 L60 128 L76 104 L70 78 L88 56
L96 32 Z"
fill="rgba(255,255,255,.07)" stroke="rgba(255,255,255,.22)" stroke-width="1.4"
stroke-linejoin="round"/>
<circle cx="128" cy="96"  r="9" fill="#4A90E2" opacity=".95"/>
<circle cx="128" cy="96"  r="17" fill="none" stroke="#4A90E2" stroke-width="1.2" opacity=".45"/>
<circle cx="152" cy="150" r="7" fill="#7FB2F0" opacity=".9"/>
<circle cx="106" cy="176" r="6" fill="#7FB2F0" opacity=".75"/>
<circle cx="172" cy="212" r="5" fill="#9BC4F2" opacity=".6"/>
<circle cx="140" cy="256" r="5" fill="#9BC4F2" opacity=".55"/>
<circle cx="96"  cy="240" r="4" fill="#9BC4F2" opacity=".45"/>
<g stroke="rgba(122,178,240,.35)" stroke-width="1" stroke-dasharray="3 4">
<path d="M128 96 L152 150"/><path d="M152 150 L106 176"/>
<path d="M152 150 L172 212"/><path d="M172 212 L140 256"/>
</g>
</svg>
"""

WHY = f"""
<section class="wl-why">
  <div class="wl-why-inner">

    <div>
      <div class="wl-why-tag">WHY WAYLOGI</div>
      <h2 class="wl-why-title">웨이로지가 다른 이유</h2>

      <div class="wl-why-list">

        <div class="wl-why-item">
          <div class="wl-why-no">01</div>
          <div>
            <div class="wl-why-h">창고가 아니라 지역 가능성을 봅니다</div>
            <div class="wl-why-d">
              부동산 매물은 지금 나와 있는 창고만 보여줍니다.
              웨이로지는 {region_count}개 시군구의 차량 등록과 인구를 겹쳐,
              <b>아직 창고가 없는 곳</b>까지 후보에 올립니다.
            </div>
          </div>
        </div>

        <div class="wl-why-item">
          <div class="wl-why-no">02</div>
          <div>
            <div class="wl-why-h">한 시점이 아니라 37개월의 방향을 봅니다</div>
            <div class="wl-why-d">
              지금 순위는 이미 비싼 곳을 알려줄 뿐입니다.
              전년 동월 대비 증가율과 <b>가속도</b>를 함께 봐서,
              포화된 곳과 지금 크는 곳을 구분합니다.
            </div>
          </div>
        </div>

        <div class="wl-why-item">
          <div class="wl-why-no">03</div>
          <div>
            <div class="wl-why-h">계산 과정을 전부 공개합니다</div>
            <div class="wl-why-d">
              어떤 지표를 어떤 가중치로 더했는지 화면에서 펼쳐볼 수 있습니다.
              점수를 믿으라고 하지 않고, <b>판단 근거</b>를 드립니다.
            </div>
          </div>
        </div>

      </div>
    </div>

    <div class="wl-why-visual">
      {MAP_SVG}
      <div class="wl-why-cap">2026.07 &#183; 종합점수 상위 지역</div>
    </div>

  </div>
</section>
"""

html(WHY)

# ── 단계별 미리보기 SVG ──
FIG_MAP = """
<svg viewBox="0 0 120 90" fill="none" xmlns="http://www.w3.org/2000/svg">
<path d="M46 8 L60 5 L70 12 L74 26 L82 34 L86 50 L78 60 L80 74 L66 82
L54 78 L44 84 L34 74 L38 60 L28 48 L34 32 L28 20 L38 12 Z"
fill="rgba(127,178,240,.14)" stroke="rgba(127,178,240,.5)" stroke-width="1.2"/>
<circle cx="52" cy="30" r="5" fill="#4A90E2"/>
<circle cx="62" cy="52" r="3.5" fill="#7FB2F0" opacity=".8"/>
<circle cx="46" cy="64" r="3" fill="#7FB2F0" opacity=".55"/>
</svg>
"""

FIG_SURVEY = """
<svg viewBox="0 0 120 90" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="14" y="14" width="92" height="15" rx="3" fill="rgba(255,255,255,.10)"/>
<rect x="14" y="35" width="92" height="15" rx="3" fill="#3D7FB0"/>
<rect x="14" y="56" width="92" height="15" rx="3" fill="rgba(255,255,255,.10)"/>
<circle cx="24" cy="42.5" r="4" fill="#fff"/>
<circle cx="24" cy="21.5" r="4" fill="none" stroke="rgba(255,255,255,.4)" stroke-width="1.3"/>
<circle cx="24" cy="63.5" r="4" fill="none" stroke="rgba(255,255,255,.4)" stroke-width="1.3"/>
<rect x="14" y="79" width="52" height="4" rx="2" fill="#7FB2F0"/>
<rect x="66" y="79" width="40" height="4" rx="2" fill="rgba(255,255,255,.14)"/>
</svg>
"""

FIG_RANK = """
<svg viewBox="0 0 120 90" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="14" y="16" width="78" height="9" rx="2" fill="#4A90E2"/>
<rect x="14" y="32" width="62" height="9" rx="2" fill="#5C9BE0" opacity=".85"/>
<rect x="14" y="48" width="48" height="9" rx="2" fill="#7FB2F0" opacity=".7"/>
<rect x="14" y="64" width="34" height="9" rx="2" fill="#9BC4F2" opacity=".55"/>
<circle cx="102" cy="20.5" r="6" fill="#F2B705"/>
</svg>
"""

FIG_WHY = """
<svg viewBox="0 0 120 90" fill="none" xmlns="http://www.w3.org/2000/svg">
<polygon points="60,12 96,34 82,74 38,74 24,34"
fill="rgba(127,178,240,.10)" stroke="rgba(127,178,240,.35)" stroke-width="1"/>
<polygon points="60,24 84,38 74,64 46,64 36,38"
fill="rgba(74,144,226,.30)" stroke="#4A90E2" stroke-width="1.6"/>
<circle cx="60" cy="24" r="3" fill="#fff"/>
<circle cx="84" cy="38" r="3" fill="#fff"/>
<circle cx="74" cy="64" r="3" fill="#fff"/>
<circle cx="46" cy="64" r="3" fill="#fff"/>
<circle cx="36" cy="38" r="3" fill="#fff"/>
</svg>
"""

FLOW = f"""
<section class="wl-flow">
  <div class="wl-flow-inner">

    <div class="wl-flow-tag">HOW IT WORKS</div>
    <h2 class="wl-flow-title">네 단계면 후보 지역이 나옵니다</h2>

    <div class="wl-steps">

      <div class="wl-step">
        <div class="wl-step-no">STEP 01</div>
        <div class="wl-step-h">지역 탐색</div>
        <div class="wl-step-d">
          전국 {region_count}개 시군구가 지표별로 색칠된 지도에서
          어디가 짙은지 먼저 봅니다.
        </div>
        <div class="wl-step-fig">{FIG_MAP}</div>
      </div>

      <div class="wl-step">
        <div class="wl-step-no">STEP 02</div>
        <div class="wl-step-h">진단 4문항</div>
        <div class="wl-step-d">
          어떤 화물을 다루는지 답하면
          세 축의 가중치가 회사에 맞게 조정됩니다.
        </div>
        <div class="wl-step-fig">{FIG_SURVEY}</div>
      </div>

      <div class="wl-step">
        <div class="wl-step-no">STEP 03</div>
        <div class="wl-step-h">맞춤 순위</div>
        <div class="wl-step-d">
          조정된 가중치로 {region_count}개 지역을 다시 계산해
          상위 후보를 정렬합니다.
        </div>
        <div class="wl-step-fig">{FIG_RANK}</div>
      </div>

      <div class="wl-step">
        <div class="wl-step-no">STEP 04</div>
        <div class="wl-step-h">근거 확인</div>
        <div class="wl-step-d">
          왜 이 순위인지 지표별 점수와
          37개월 추이로 확인합니다.
        </div>
        <div class="wl-step-fig">{FIG_WHY}</div>
      </div>

    </div>

  </div>
</section>
"""

html(FLOW)

CONTACT = f"""
<section class="wl-contact">
  <div class="wl-contact-inner">

    <div class="wl-contact-tag">CONTACT</div>
    <h2 class="wl-contact-title">이 순위만으로 결정할 수는 없습니다</h2>
    <div class="wl-contact-d">
      순위에 담기지 않은 것들 &#8212; 임대 시세, 인허가, 인접 물류망은
      웨이로지가 답하지 못합니다. 무엇이 더 필요한지 알려주시면
      다음 버전에 반영합니다.
    </div>

    <div class="wl-contact-cta">
      <a class="wl-btn wl-btn-primary" href="/문의" target="_self">문의 남기기</a>
      <a class="wl-btn wl-btn-ghost-lt" href="/문의" target="_self">자주 묻는 질문</a>
    </div>

    <div class="wl-faq-peek">
      <div class="wl-faq-q">
        <div class="wl-faq-q-t">점수는 어떻게 계산되나요?</div>
        <div class="wl-faq-q-a">
          지표별 전국 백분위를 세 축으로 묶고 가중 평균합니다.
          화면에서 지표별 순위까지 펼쳐볼 수 있습니다.
        </div>
      </div>
      <div class="wl-faq-q">
        <div class="wl-faq-q-t">화물차 등록지가 실제 운행지와 다르지 않나요?</div>
        <div class="wl-faq-q-a">
          맞습니다. 등록은 차고지 기준이라 대리 지표입니다.
          그래서 순위를 결론이 아니라 후보로 씁니다.
        </div>
      </div>
      <div class="wl-faq-q">
        <div class="wl-faq-q-t">데이터는 언제까지인가요?</div>
        <div class="wl-faq-q-a">
          2023년 7월부터 2026년 7월까지 37개월,
          전국 {region_count}개 시군구를 월 단위로 봅니다.
        </div>
      </div>
    </div>

  </div>
</section>
"""

html(CONTACT)
footer()
