"""
유망지역 추천 — 선호도 설문 · 가중치 산출 · 맞춤 순위

두 단계로 나눈다.
  ① 중요도 진단   5문항 이지선다로 산업성·성장성·수요성 배분을 잡는다
  ② 유망지역 순위 실제 DB 지역 전체를 다시 채점해 상위를 보여준다

결과 화면은 좌우로 나누지 않고 전폭 띠를 위에서 아래로 쌓는다.
  기준 조정 → 현재 배분 → 추천 목록 → 8곳 비교 그래프
목록에서 지역을 누르면 그 줄 바로 아래에 근거가 펼쳐진다.

표의 칸 너비는 Streamlit 컬럼이 아니라 CSS grid 로 잡는다.
st.columns 로 셀을 나누면 칸마다 컨테이너가 생겨 줄 간격이
벌어지고 버튼만 높아진다.

Streamlit 은 클릭할 때마다 스크립트를 처음부터 다시 돌리므로
막대가 자라나는 과정을 그대로 보여줄 수 없다. 직전 값을
session_state 에 남겨두고 이전값 → 새값 구간의 @keyframes 를
매번 새로 찍어 브라우저가 애니메이션을 재생하게 했다.
"""

import pandas as pd
import streamlit as st
from pymysql import MySQLError

from ui import charts
from ui.backend import get_db
from ui.layout import setup, html
from web.backend import (
    get_dashboard_summary,
    get_logistics_ranking,
    get_national_population_history,
    get_national_vehicle_metrics,
    get_supplemental_logistics_metrics,
)

setup(page="recommend", active="맞춤지역 추천")

TARGET_MONTH, TREND_START, TREND_END = "2026-07", "2023-07", "2026-07"
TOP_N = 8

AXES = ["산업성", "성장성", "수요성"]
AXIS_COL = {"산업성": "점수_산업성", "성장성": "점수_성장성", "수요성": "점수_수요성"}
AXIS_CLASS = {"산업성": "industry", "성장성": "growth", "수요성": "demand"}

# 슬라이더를 올릴 때 무엇이 올라가는지 알려준다.
# 숫자만 보이면 조작은 되지만 판단은 안 된다.
AXIS_DESC = {
    "산업성": "영업용 화물 비중 · 입지계수 LQ · 화물차 비율 · 인구 1천명당 화물차",
    "성장성": "인구-화물 디커플링 · 12개월 가속도 · 추세 지속성 · 영업용 전환율 · 화물차 YoY · 안정성",
    "수요성": "인접권 인구(데이터 준비 중) · 자체 인구 · 인구 밀도 · 인구 증가율",
}

# 프리셋 — 슬라이더를 직접 만지는 대신 방향을 통째로 바꾼다.
# 균등 배분은 넣지 않는다. 종합점수 순위와 같아져서
# 데이터 조회에서 정렬만 바꾼 화면이 되어버린다.
PRESETS = {
    "지금 당장 들어갈 곳": {"산업성": 55, "성장성": 20, "수요성": 25},
    "3년 뒤를 보고": {"산업성": 20, "성장성": 60, "수요성": 20},
    "물량이 많은 곳": {"산업성": 30, "성장성": 15, "수요성": 55},
}

TYPE_CLASS = {"미개척": "t0", "성장 중": "t1", "포화": "t2", "정체": "t3"}

QUESTIONS = [
    {
        "id": "growth_style",
        "title": "어떤 성장을 원하시나요?",
        "options": [
            {"label": "몇 년째 꾸준히 늘어온 곳",
             "desc": "안정적인 추세를 중요하게 봅니다",
             "w": {"성장성": 2, "산업성": 1}},
            {"label": "최근 급격히 늘어난 곳",
             "desc": "최근 변화의 속도를 중요하게 봅니다",
             "w": {"성장성": 3}},
        ],
    },
    {
        "id": "market",
        "title": "어느 쪽이 편하신가요?",
        "options": [
            {"label": "경쟁이 있어도 검증된 시장",
             "desc": "이미 물류가 발달한 지역을 선호합니다",
             "w": {"산업성": 3}},
            {"label": "경쟁이 적은 조용한 지역",
             "desc": "아직 덜 알려진 지역을 선호합니다",
             "w": {"성장성": 2, "수요성": 1}},
        ],
    },
    {
        "id": "demand_source",
        "title": "물량은 어디서 나온다고 보시나요?",
        "options": [
            {"label": "사람이 많은 곳에서",
             "desc": "소비지 배송 물량을 중심으로 봅니다",
             "w": {"수요성": 3}},
            {"label": "공장과 창고가 많은 곳에서",
             "desc": "산업 물량을 중심으로 봅니다",
             "w": {"산업성": 2, "성장성": 1}},
        ],
    },
    {
        "id": "horizon",
        "title": "언제를 보고 계신가요?",
        "options": [
            {"label": "지금 당장 들어갈 곳",
             "desc": "현재 여건이 갖춰진 지역을 찾습니다",
             "w": {"산업성": 2, "수요성": 1}},
            {"label": "3년 뒤를 보고 미리 잡을 곳",
             "desc": "앞으로 커질 지역을 찾습니다",
             "w": {"성장성": 3}},
        ],
    },
    {
        "id": "scale",
        "title": "어느 규모를 생각하시나요?",
        "options": [
            {"label": "배후 인구가 넉넉한 곳",
             "desc": "넓은 권역을 한 번에 덮고 싶습니다",
             "w": {"수요성": 3}},
            {"label": "작아도 화물이 몰리는 곳",
             "desc": "규모보다 밀도를 봅니다",
             "w": {"산업성": 2, "성장성": 1}},
        ],
    },
]


# ══ 데이터 ═════════════════════════════════════════
def split_region_name(name: str) -> tuple[str, str]:
    sido, _, sgg = name.partition(" ")
    return sido, sgg or sido


def classify_region(density, growth, density_mean, growth_mean) -> str:
    """PDF의 화물차 밀도·YoY 4분면으로 경합도 라벨을 계산한다."""
    if any(pd.isna(value) for value in (density, growth, density_mean, growth_mean)):
        return "분류 불가"
    specialized, growing = density >= density_mean, growth >= growth_mean
    return {
        (False, True): "미개척",
        (True, True): "성장 중",
        (True, False): "포화",
        (False, False): "정체",
    }[(specialized, growing)]


@st.cache_data(ttl=3600)
def load_region_count() -> int:
    return get_dashboard_summary(get_db(), TARGET_MONTH)["region_count"]


@st.cache_data(ttl=3600)
def load_supplemental_data() -> dict[str, dict]:
    return {
        row["region_code"]: row
        for row in get_supplemental_logistics_metrics(get_db(), TARGET_MONTH)
    }


@st.cache_data(ttl=3600)
def load_recommendation_data(
    industry_weight: float,
    growth_weight: float,
    demand_weight: float,
) -> tuple[pd.DataFrame, int]:
    """backend가 계산한 사용자 가중 순위와 상세 표시용 실제 값을 합친다."""
    db = get_db()
    region_count = load_region_count()
    ranking = get_logistics_ranking(
        db,
        TARGET_MONTH,
        industry_weight=industry_weight,
        growth_weight=growth_weight,
        demand_weight=demand_weight,
        limit=max(region_count, 1),
    )
    supplemental = load_supplemental_data()
    rows = []
    for result in ranking:
        scores = result.get("scores", {})
        raw = result.get("raw", {})
        if any(scores.get(key) is None for key in ("industry", "growth", "demand", "total")):
            continue
        region_name = result.get("region_name", result["region_code"])
        sido, sgg = split_region_name(region_name)
        extra = supplemental.get(result["region_code"], {}).get("raw", {})
        rows.append({
            "region_code": result["region_code"],
            "지역": region_name,
            "시도": sido,
            "시군구": sgg,
            "맞춤점수": scores["total"],
            "점수_산업성": scores["industry"],
            "점수_성장성": scores["growth"],
            "점수_수요성": scores["demand"],
            "화물차": raw.get("truck_count"),
            "인구수": raw.get("population"),
            "화물차_증가율": raw.get("yoy_growth"),
            "LQ": extra.get("location_quotient"),
            "화물차밀도": extra.get("freight_density"),
        })
    data = pd.DataFrame(rows)
    if not data.empty:
        growth_mean = data["화물차_증가율"].mean()
        density_mean = data["화물차밀도"].mean()
        data["유형"] = data.apply(
            lambda row: classify_region(row["화물차밀도"], row["화물차_증가율"], density_mean, growth_mean),
            axis=1,
        )
    return data, region_count


# ══ 상태 ═══════════════════════════════════════════
ss = st.session_state
ss.setdefault("rec_idx", 0)          # 지금 몇 번째 문항인가
ss.setdefault("rec_answers", {})     # {문항id: 선택지index}
ss.setdefault("rec_prev_w", None)    # 직전 가중치 — 애니메이션 시작점
ss.setdefault("rec_prev_pg", 0.0)    # 직전 진행률
ss.setdefault("rec_tick", 0)         # @keyframes 이름을 매번 바꾸기 위한 값
ss.setdefault("rec_done", False)     # 결과 화면으로 넘어갔는가
ss.setdefault("rec_manual", None)    # 프리셋으로 덮어쓴 값
ss.setdefault("rec_mver", 0)         # 슬라이더를 새로 만들기 위한 값
ss.setdefault("rec_open", None)      # 목록에서 펼친 지역

@st.cache_data(ttl=3600)
def load_freight_trend(region_code: str) -> pd.DataFrame:
    """실제 월별 화물차·인구를 결합해 지역값과 전국값을 반환한다."""
    months = pd.period_range(TREND_START, TREND_END, freq="M").astype(str).tolist()
    vehicles = pd.DataFrame(get_national_vehicle_metrics(get_db(), months))
    populations = pd.DataFrame(
        get_national_population_history(get_db(), TREND_START, TREND_END)
    )
    if vehicles.empty or populations.empty:
        return pd.DataFrame()
    vehicle_columns = {"region_code", "date", "truck_count"}
    population_columns = {"region_code", "date", "population"}
    if not vehicle_columns.issubset(vehicles.columns) or not population_columns.issubset(populations.columns):
        return pd.DataFrame()
    merged = vehicles.merge(populations, on=["region_code", "date"], how="inner")
    merged = merged[merged["population"].notna() & (merged["population"] > 0)].copy()
    if merged.empty:
        return pd.DataFrame()
    merged["인구천명당_화물차"] = merged["truck_count"] / merged["population"] * 1000
    national = merged.groupby("date", as_index=False).agg(
        truck_count=("truck_count", "sum"), population=("population", "sum")
    )
    national["전국평균"] = national["truck_count"] / national["population"] * 1000
    selected = merged[merged["region_code"] == region_code][
        ["date", "인구천명당_화물차"]
    ]
    trend = selected.merge(national[["date", "전국평균"]], on="date", how="left")
    trend["연월라벨"] = trend["date"].str[2:4] + "." + trend["date"].str[5:7]
    return trend.sort_values("date")

def survey_weights() -> dict[str, float]:
    """답한 문항의 점수를 축별로 더하고 합이 1이 되게 나눈다.

    셋 다 1에서 출발하는 이유는 건너뛰기로 아무것도 안 골랐을 때
    0 으로 나누는 것을 막고, 한 축이 0% 가 되는 극단을 피하기 위함이다.
    """
    acc = {a: 1.0 for a in AXES}
    for q in QUESTIONS:
        idx = ss.rec_answers.get(q["id"])
        if idx is None:
            continue
        for axis, pt in q["options"][idx]["w"].items():
            acc[axis] += pt
    total = sum(acc.values())
    return {a: v / total for a, v in acc.items()}


def answer(qid: str, idx: int) -> None:
    ss.rec_answers[qid] = idx
    ss.rec_idx += 1
    if ss.rec_idx >= len(QUESTIONS):
        ss.rec_done = True


def skip() -> None:
    ss.rec_idx += 1
    if ss.rec_idx >= len(QUESTIONS):
        ss.rec_done = True


def restart() -> None:
    ss.rec_idx = 0
    ss.rec_answers = {}
    ss.rec_prev_w = None
    ss.rec_prev_pg = 0.0
    ss.rec_done = False
    ss.rec_manual = None
    ss.rec_open = None
    ss.rec_mver += 1


def apply_preset(name: str) -> None:
    """프리셋을 누르면 슬라이더도 그 값으로 다시 만들어진다.

    위젯이 만들어진 뒤에는 key 로 값을 바꿀 수 없으므로
    버전 번호를 올려 key 자체를 새것으로 만든다.
    """
    ss.rec_manual = dict(PRESETS[name])
    ss.rec_mver += 1


def toggle(region: str) -> None:
    ss.rec_open = None if ss.rec_open == region else region


# ══ 진행바 ═════════════════════════════════════════
def render_progress(done: int, total: int) -> None:
    """이전 진행률에서 지금 진행률까지 자라나는 막대.

    rerun 으로 요소가 새로 만들어지면 transition 은 재생되지 않는다.
    이전값을 시작 프레임으로 하는 keyframes 를 매번 새 이름으로
    찍어야 브라우저가 애니메이션으로 인식한다.
    """
    now = done / total
    prev = ss.rec_prev_pg
    ss.rec_prev_pg = now
    ss.rec_tick += 1
    anim = f"wlgrow{ss.rec_tick}"

    html(f"""
    <style>
    @keyframes {anim} {{
      from {{ width: {prev*100:.1f}%; }}
      to   {{ width: {now*100:.1f}%; }}
    }}
    </style>
    <div class="wl-q-progress">
      <i style="width:{now*100:.1f}%;
                animation:{anim} .55s cubic-bezier(.4,0,.2,1)"></i>
    </div>
    """)


# ══ 가중치 패널 ════════════════════════════════════
def render_weights(w: dict[str, float], compact: bool = False) -> None:
    """세 축의 현재 배분.

    설문 중에는 세로로 세 줄(compact=False), 결과 화면에서는
    가로 한 줄(compact=True)로 접는다. 결과 화면에서는 이미
    정해진 값이라 자리를 크게 차지할 이유가 없다.
    """
    prev = ss.rec_prev_w
    ss.rec_prev_w = dict(w)
    ss.rec_tick += 1

    styles, bars = "", ""
    for i, axis in enumerate(AXES):
        pct = w[axis] * 100
        start = prev[axis] * 100 if prev else 0.0
        anim = f"wlw{ss.rec_tick}_{i}"
        styles += (f"@keyframes {anim}{{from{{width:{start:.1f}%}}"
                   f"to{{width:{pct:.1f}%}}}}")

        delta = ""
        if prev is not None:
            d = pct - prev[axis] * 100
            if abs(d) >= 0.5:
                cls = "up" if d > 0 else "down"
                delta = f'<em class="{cls}">{d:+.0f}%p</em>'

        bars += (
            f'<div class="wl-wbar">'
            f'<span class="wl-wbar-label">{axis}</span>'
            f'<div class="wl-wbar-track">'
            f'<i class="{AXIS_CLASS[axis]}" style="width:{pct:.1f}%;'
            f'animation:{anim} .55s cubic-bezier(.4,0,.2,1)"></i></div>'
            f'<b class="wl-wbar-pct">{pct:.0f}%</b>{delta}'
            f'</div>'
        )

    cls = "wl-wpanel wl-wpanel-row" if compact else "wl-wpanel"
    head = "" if compact else (
        '<div class="wl-wpanel-head"><span>현재 내 기준</span>'
        '<em>바꿀 때마다 순위가 다시 계산됩니다</em></div>'
    )
    html(f'<style>{styles}</style><div class="{cls}">{head}{bars}</div>')


# ══ ① 중요도 진단 ══════════════════════════════════
def render_survey() -> None:
    q = QUESTIONS[ss.rec_idx]

    render_progress(ss.rec_idx, len(QUESTIONS))

    meta_l, meta_r = st.columns([4, 1], vertical_alignment="center")
    with meta_l:
        html(f'<div class="wl-q-count">{len(QUESTIONS)}문항 중 '
             f'{ss.rec_idx + 1}번째</div>')
    with meta_r:
        st.button("건너뛰기", key=f"skip_{q['id']}", on_click=skip,
                  use_container_width=True)

    html(f"""
    <div class="wl-q-head">
      <h2>{q['title']}</h2>
      <p>선택에 따라 산업성 · 성장성 · 수요성의 가중치가 즉시 바뀝니다</p>
    </div>
    """)

    cols = st.columns(2, gap="medium")
    for col, (i, opt) in zip(cols, enumerate(q["options"])):
        with col:
            st.button(
                f"**{opt['label']}**  \n{opt['desc']}",
                key=f"{q['id']}_{i}", on_click=answer, args=(q["id"], i),
                use_container_width=True,
            )

    render_weights(survey_weights())


# ══ 기준 조정 ══════════════════════════════════════
def render_tuner(base: dict[str, float]) -> dict[str, float]:
    """프리셋 3개와 슬라이더 3개를 한 줄씩 전폭으로 놓는다.

    슬라이더만 두면 숫자를 만질 뿐 무엇이 달라지는지 알기 어렵다.
    프리셋으로 방향을 먼저 고르게 하고, 각 축이 어떤 지표를
    보는지 슬라이더 아래에 적어둔다.
    """
    html('<div class="wl-sec-head"><b>기준 바꿔보기</b>'
         '<em>자주 쓰는 기준을 고르거나 직접 조정하세요</em></div>')

    pcols = st.columns(len(PRESETS), gap="medium")
    for col, name in zip(pcols, PRESETS):
        with col:
            st.button(name, key=f"preset_{name}", on_click=apply_preset,
                      args=(name,), use_container_width=True)

    start = ss.rec_manual or {a: int(round(base[a] * 100)) for a in AXES}

    scols = st.columns(3, gap="large")
    manual = {}
    for col, axis in zip(scols, AXES):
        with col:
            manual[axis] = st.slider(
                axis, 0, 100, int(start[axis]), step=5,
                key=f"manual_{axis}_{ss.rec_mver}",
            )
            html(f'<div class="wl-tune-desc">{AXIS_DESC[axis]}</div>')

    total = sum(manual.values())
    return base if total <= 0 else {a: v / total for a, v in manual.items()}


# ══ 목록 한 줄 ═════════════════════════════════════
def render_row(
    rank: int,
    row,
    w: dict[str, float],
    is_open: bool,
    nationwide: pd.DataFrame,
    region_count: int,
) -> None:
    """왼쪽 셀들은 HTML grid 한 덩어리, 오른쪽에 버튼 하나.

    셀마다 st.columns 를 쓰면 컨테이너가 생겨 줄 높이가 들쭉날쭉해진다.
    """
    left, right = st.columns([9, 1], vertical_alignment="center")

    tcls = TYPE_CLASS.get(row["유형"], "t3")
    with left:
        html(f"""
        <div class="wl-t-row {'open' if is_open else ''}">
          <span class="wl-t-no">{rank}</span>
          <span class="wl-t-name">{row['시도']} {row['시군구']}
            <span class="wl-tag {tcls}">{row['유형']}</span></span>
          <b class="wl-t-score">{row['맞춤점수']:.1f}</b>
          <span class="wl-t-val">{row['점수_산업성']:.1f}</span>
          <span class="wl-t-val">{row['점수_성장성']:.1f}</span>
          <span class="wl-t-val">{row['점수_수요성']:.1f}</span>
        </div>
        """)

    with right:
        st.button("닫기" if is_open else "근거",
                  key=f"open_{row['지역']}", on_click=toggle,
                  args=(row["지역"],), use_container_width=True)

    if not is_open:
        return

    # ── 펼친 근거 ──────────────────────────────────
    terms = " &nbsp;|&nbsp; ".join(
        f'{a} {row[AXIS_COL[a]]:.1f} × {w[a]:.2f} = {row[AXIS_COL[a]]*w[a]:.1f}'
        for a in AXES
    )
    bars = "".join(
        f'<div class="wl-d-bar">'
        f'<span>{a}</span>'
        f'<div class="wl-d-track"><i class="{AXIS_CLASS[a]}" '
        f'style="width:{row[AXIS_COL[a]]:.1f}%"></i></div>'
        f'<b>{row[AXIS_COL[a]]:.1f}</b></div>'
        for a in AXES
    )

    truck_text = f'{row["화물차"]:,.0f}대' if pd.notna(row["화물차"]) else "데이터 없음"
    population_text = f'{row["인구수"]:,.0f}명' if pd.notna(row["인구수"]) else "데이터 없음"
    growth_text = f'{row["화물차_증가율"]:+.1f}%' if pd.notna(row["화물차_증가율"]) else "데이터 없음"
    html(f"""
    <div class="wl-d-panel">
      <div class="wl-d-formula">{terms}
        &nbsp;→&nbsp; <b>종합 {row['맞춤점수']:.1f}점</b></div>
      {bars}
      <div class="wl-d-foot">화물차 {truck_text} &#183;
        인구 {population_text} &#183;
        전년 동월 대비 {growth_text}</div>
    </div>
    """)

    try:
        tr = load_freight_trend(row["region_code"])
    except (MySQLError, OSError, ValueError, KeyError, TypeError):
        tr = pd.DataFrame()
    
    d1, d2 = st.columns(2, gap="medium")

    with d1:
        with st.container(border=True):
            html('<div class="wl-chart-sub">인구 1천명당 화물차 · 37개월</div>')
            charts.trend_chart(
                tr, x_col="연월라벨",
                series={"인구천명당_화물차": row["시군구"],
                        "전국평균": "전국 평균"},
                height=210, key=f"tr_{row['지역']}",
            )
    
    with d2:
        with st.container(border=True):
            html(f'<div class="wl-chart-sub">전국 {region_count}개 지역 중 위치</div>')
            charts.quadrant_chart(
                nationwide, selected=row["지역"], height=210,
                key=f"qd_{row['지역']}",
            )

# ══ ② 유망지역 순위 ════════════════════════════════
def render_result() -> None:
    base = survey_weights()

    head_l, head_r = st.columns([4, 1], vertical_alignment="center")
    with head_l:
        html('<div class="wl-r-head"><h2>이 기준에 맞는 지역입니다</h2>'
             '<p>기준을 바꾸면 순위가 즉시 다시 계산됩니다</p></div>')
    with head_r:
        st.button("다시 진단하기", key="restart", on_click=restart,
                  use_container_width=True)

    w = render_tuner(base)
    render_weights(w, compact=True)

    backend_weights = {axis: w[axis] * 100 for axis in AXES}
    try:
        ranked, region_count = load_recommendation_data(
            backend_weights["산업성"],
            backend_weights["성장성"],
            backend_weights["수요성"],
        )
    except (MySQLError, OSError, ValueError) as error:
        st.error("추천 데이터를 불러오지 못했습니다. .env와 DB 실행 상태를 확인해주세요.")
        st.caption(str(error))
        return
    if ranked.empty:
        st.warning(f"{TARGET_MONTH}에 추천 점수를 계산할 수 있는 지역 데이터가 없습니다.")
        return
    top = ranked.head(TOP_N)
    picks = top["지역"].tolist()

    # ── 목록 ───────────────────────────────────────
    html(f'<div class="wl-sec-head"><b>전국 {region_count}개 지역 중 상위 {len(top)}곳</b>'
         f'<em>근거를 누르면 계산 과정이 펼쳐집니다</em></div>')

    hl, hr = st.columns([9, 1])
    with hl:
        html("""
        <div class="wl-t-row wl-t-head">
          <span>순위</span><span>지역명</span><span>맞춤점수</span>
          <span>산업성</span><span>성장성</span><span>수요성</span>
        </div>
        """)

    for i, row in top.iterrows():
        render_row(
            i + 1, row, w, ss.rec_open == row["지역"], ranked, region_count
        )

    # # ── 8곳 비교 ───────────────────────────────────
    # html('<div class="wl-sec-head"><b>추천 8곳 견주어 보기</b>'
    #      '<em>왼쪽은 전국 안에서의 자리, 오른쪽은 축별 강약</em></div>')

    # g1, g2 = st.columns(2, gap="medium")
    # with g1:
    #     with st.container(border=True):
    #         html('<div class="wl-chart-sub">경합도 위치</div>')
    #         charts.quadrant_chart(df, selected=picks, key="rec_quad")
    # with g2:
    #     with st.container(border=True):
    #         html('<div class="wl-chart-sub">세 축 비교</div>')
    #         charts.group_bar(top, name_col="시군구", key="rec_group")


# ══ 렌더 ═══════════════════════════════════════════
html(f"""
<div class="wl-r-tabs">
  <span class="{'on' if not ss.rec_done else ''}">① 중요도 진단</span>
  <span class="{'on' if ss.rec_done else ''}">② 맞춤지역 순위</span>
</div>
""")

if ss.rec_done:
    render_result()
else:
    render_survey()
