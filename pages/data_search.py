"""
데이터 조회 — 검색 · 지도 드릴다운 · 상세 · 그래프

역할 분담
  오른쪽(4)  이 지역이 어떤 곳인가   지역명 · 유형 · 점수 · 해석 문장
  왼쪽(6)    왜 그 점수인가         지표 12개와 전국 순위

선택(시도/시군구)과 필터(유형/배후인구)를 분리한다.
  선택  어디를 볼지  →  지도 단계와 상세 화면을 결정
  필터  무엇을 볼지  →  지도 색과 목록에서 걸러냄
"""

from pathlib import Path

import admdongkor as adk
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from ui import charts
from ui.layout import setup, html

setup(page="explore", active="데이터 조회")

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "geo"

# 지도를 칠할 지표 — (컬럼, 집계방식, 표시형식)
METRICS = {
    "종합점수": ("종합점수", "mean", "{:.1f}"),
    "산업성": ("점수_산업성", "mean", "{:.1f}"),
    "성장성": ("점수_성장성", "mean", "{:.1f}"),
    "수요성": ("점수_수요성", "mean", "{:.1f}"),
    "화물차": ("화물차", "sum", "{:,.0f}대"),
}

# 근거 카드 — (라벨, 컬럼, 표시형식)
EVIDENCE_FIELDS = {
    "산업성": [
        ("입지계수 LQ", "LQ", "{:.2f}"),
        ("영업용 비중", "영업용비중", "{:.1f}%"),
        ("화물차 비율", "화물차비율", "{:.1f}%"),
        ("화물차 대수", "화물차", "{:,.0f}대"),
    ],
    "성장성": [
        ("화물차 증가율", "화물차_증가율", "{:+.1f}%"),
        ("가속도", "가속도", "{:+.1f}"),
        ("추세 지속성", "추세지속성", "{:.2f}"),
        ("영업용 전환율", "영업용전환율", "{:.2f}"),
    ],
    "수요성": [
        ("배후 인구", "배후인구", "{:,.0f}명"),
        ("자체 인구", "인구수", "{:,.0f}명"),
        ("인구 밀도", "인구밀도", "{:,.0f}명/㎢"),
        ("인구 증가율", "인구_증가율", "{:+.1f}%"),
    ],
}

CATEGORY_CLASS = {"산업성": "industry", "성장성": "growth", "수요성": "demand"}
SCORE_COL = {"산업성": "점수_산업성", "성장성": "점수_성장성", "수요성": "점수_수요성"}

TYPES = ["미개척", "성장 중", "포화", "정체"]
TYPE_DESC = {
    "미개척": "화물 특화도는 낮지만 성장 중입니다. 아직 경쟁이 적은 단계입니다.",
    "성장 중": "이미 화물에 특화되어 있고 계속 커지고 있습니다.",
    "포화": "화물 특화도는 높지만 성장은 둔화됐습니다. 진입이 늦을 수 있습니다.",
    "정체": "특화도와 성장세가 모두 전국 평균을 밑돕니다.",
}
TYPE_CLASS = {"미개척": "t0", "성장 중": "t1", "포화": "t2", "정체": "t3"}

SHADES = ["#E6F1FB", "#B5D4F4", "#85B7EB", "#378ADD", "#185FA5"]
DIMMED = "#EFF2F5"
HIGHLIGHT = "#FF7A45"

SIDO_ALIAS = {"전남광주통합특별시": ["전남광주통합특별시", "광주광역시", "전라남도"]}


# ══ 데이터 ═════════════════════════════════════════
@st.cache_data
def load_mock():
    return pd.read_csv(ASSETS / "mock_regions.csv", encoding="utf-8-sig")


@st.cache_data
def load_geo_sido():
    g = adk.get("20260201", level="sido").to_crs(epsg=4326)
    g["geometry"] = g["geometry"].simplify(0.002)
    return g


@st.cache_data
def load_geo_sgg():
    """249개 폴리곤이라 무겁다. 시도를 선택했을 때만 부른다."""
    g = adk.get("20260201", level="sgg").to_crs(epsg=4326)
    g["geometry"] = g["geometry"].simplify(0.0005)
    return g


@st.cache_data
def build_ranks(data):
    """수치 컬럼의 전국 순위를 미리 계산해둔다."""
    cols = [c for c in data.columns
            if pd.api.types.is_numeric_dtype(data[c]) and c != "순위"]
    r = pd.DataFrame(index=data.index)
    for c in cols:
        r[c] = data[c].rank(ascending=False, method="min").astype(int)
    return r


df = load_mock()
ranks = build_ranks(df)
N = len(df)


# ══ 이름 맞추기 ════════════════════════════════════
def is_matching_sido(geo_nm, df_sido):
    if geo_nm == df_sido:
        return True
    for ours, theirs in SIDO_ALIAS.items():
        if df_sido in theirs and geo_nm == ours:
            return True
        if geo_nm in theirs and df_sido == ours:
            return True
    return False


def sido_display_name(geo_nm):
    options = df["시도"].unique()
    if geo_nm in options:
        return geo_nm
    for opt in options:
        if is_matching_sido(geo_nm, opt):
            return opt
    return geo_nm


def sgg_display_name(sido_name, geo_nm):
    """'일산동구' → '고양시 일산동구' 처럼 CSV 표기로 되돌린다."""
    candidates = df[df["시도"] == sido_name]["시군구"].unique()
    target = geo_nm.replace(" ", "")
    for c in candidates:
        if c.replace(" ", "") == target:
            return c
    for c in candidates:
        nc = c.replace(" ", "")
        if target in nc or nc in target:
            return c
    return geo_nm


# ══ 선택 상태 ══════════════════════════════════════
for k, v in [("sido_select", "전체"), ("sgg_select", "전체")]:
    st.session_state.setdefault(k, v)

# 위젯 생성 후에는 session_state 를 직접 못 바꾼다.
# 지도 클릭·뒤로가기는 pending_* 에 적어두고 rerun 하며,
# 위젯 생성 전인 여기서 실제 값에 반영한다.
if "pending_sido" in st.session_state:
    st.session_state.sido_select = st.session_state.pop("pending_sido")
    st.session_state.sgg_select = "전체"
if "pending_sgg" in st.session_state:
    st.session_state.sgg_select = st.session_state.pop("pending_sgg")


def _on_sido_change():
    st.session_state.sgg_select = "전체"


# ══ 검색 바 ════════════════════════════════════════
c1, c2, c3, c4, c5 = st.columns([1.5, 1.8, 2.0, 2.4, 1.4], vertical_alignment="center")

with c1:
    sido = st.selectbox(
        "시도", ["전체"] + sorted(df["시도"].unique()),
        key="sido_select", on_change=_on_sido_change,
        label_visibility="collapsed",
    )

with c2:
    sgg_opts = ["전체"] if sido == "전체" else \
        ["전체"] + sorted(df[df["시도"] == sido]["시군구"])
    sgg = st.selectbox(
        "시군구", sgg_opts, disabled=(sido == "전체"),
        key="sgg_select", label_visibility="collapsed",
    )

with c3:
    picked = st.multiselect(
        "유형", TYPES, placeholder="유형 전체",
        label_visibility="collapsed",
    )

with c4:
    lo, hi = int(df["배후인구"].min()), int(df["배후인구"].max())
    pop = st.slider(
        "배후 인구", lo, hi, (lo, hi), step=10_000,
        label_visibility="collapsed",
    )

with c5:
    metric_label = st.selectbox(
        "지표", list(METRICS), label_visibility="collapsed",
    )

metric_col, metric_how, metric_fmt = METRICS[metric_label]


# ══ 필터와 선택 분리 ═══════════════════════════════
passed = df[(df["배후인구"] >= pop[0]) & (df["배후인구"] <= pop[1])]
if picked:
    passed = passed[passed["유형"].isin(picked)]

scoped = passed if sido == "전체" else passed[passed["시도"] == sido]
scoped = scoped.sort_values(metric_col, ascending=False)

sel_row = None
sel_rank = None
filtered_out = False
if sgg != "전체":
    hit = df[(df["시도"] == sido) & (df["시군구"] == sgg)]
    if not hit.empty:
        sel_row = hit.iloc[0]
        sel_rank = ranks.loc[hit.index[0]]
        filtered_out = not (
            (passed["시도"] == sido) & (passed["시군구"] == sgg)
        ).any()

scope_txt = "전국" if sido == "전체" else sido
denom = len(df) if sido == "전체" else len(df[df["시도"] == sido])

html(f'<div class="wl-meta">{scope_txt} '
     f'<b>{len(scoped)}개</b> / {denom}개 지역 '
     f'&#183; 지도는 <b>{metric_label}</b> 기준</div>')


# ══ 해석 문장 ══════════════════════════════════════
def story_lines(row):
    """숫자를 사람이 읽는 문장으로."""
    lines = []

    car, popr = row["화물차_증가율"], row["인구_증가율"]
    gap = car - popr
    if popr < 0 <= car:
        lines.append(f"인구는 12개월간 {abs(popr):.1f}% 줄었지만 "
                     f"화물차는 {car:+.1f}% 늘었습니다.")
    elif gap > 0:
        lines.append(f"화물차가 인구보다 {gap:.1f}%p 빠르게 늘고 있습니다.")
    else:
        lines.append(f"화물차 증가율 {car:+.1f}%가 "
                     f"인구 증가율 {popr:+.1f}%를 밑돕니다.")

    lq = row["LQ"]
    if lq >= 1:
        lines.append(f"화물차 구성비가 전국 평균의 {lq:.2f}배로, "
                     f"물류에 특화된 지역입니다.")
    else:
        lines.append(f"화물차 구성비가 전국 평균의 {lq:.2f}배로, "
                     f"아직 물류 특화도는 낮습니다.")

    lines.append(f"자체 인구 {row['인구수']/10000:,.1f}만이지만 "
                 f"배후 인구는 {row['배후인구']/10000:,.0f}만입니다.")
    return lines


# ══ 왼쪽 : 근거 ════════════════════════════════════
def render_evidence(row, rank_row):
    """오른쪽에 그리는 근거 목록. 값마다 전국 순위를 붙인다.

    html() 을 여러 번 나눠 부르면 Streamlit 이 호출마다 자체
    컨테이너로 감싸서 <div> 가 열린 채 끝나버린다. 문자열을
    전부 만들어두고 마지막에 한 번만 그린다.
    """
    groups = ""

    for category, fields in EVIDENCE_FIELDS.items():
        score = row[SCORE_COL[category]]
        cat_rank = int(rank_row[SCORE_COL[category]])

        cards = ""
        for ev_label, ev_col, ev_fmt in fields:
            r = int(rank_row[ev_col])
            top = "wl-top" if r <= N * 0.2 else ""
            cards += (
                f'<div class="wl-evidence-card">'
                f'<span class="wl-evidence-label">{ev_label}</span>'
                f'<b class="wl-evidence-value">{ev_fmt.format(row[ev_col])}</b>'
                f'<span class="wl-evidence-rank {top}">전국 {r}위</span>'
                f'</div>'
            )

        groups += (
            f'<div class="wl-evidence-group wl-cat-{CATEGORY_CLASS[category]}">'
            f'<div class="wl-evidence-title">'
            f'<span>{category}</span>'
            f'<b>{score:.1f}</b>'
            f'<em>전국 {cat_rank}위 / {N}</em>'
            f'</div>'
            f'<div class="wl-evidence-grid">{cards}</div>'
            f'</div>'
        )

    html(f'<div class="wl-evidence-head">근거 데이터</div>{groups}')


# ══ 왼쪽 : 요약 ════════════════════════════════════
def render_head(row, sido_name, sgg_name, total_rank):
    """왼쪽 상단 — 지역명과 유형 뱃지. 근거 카드 위에 놓인다."""
    with st.container(key="detail_back_btn"):
        if st.button("← 지도로", key="btn_back_to_map"):
            st.session_state.pending_sgg = "전체"
            st.rerun()

    tcls = TYPE_CLASS.get(row["유형"], "t3")
    note = ('<div class="wl-note">현재 필터 조건에는 포함되지 않는 지역입니다.</div>'
            if filtered_out else "")

    html(f"""
    {note}
    <div class="wl-sum-head">
      <div class="wl-sum-sido">{sido_name}</div>
      <h1 class="wl-sum-name">{sgg_name}</h1>
      <div class="wl-sum-tags">
        <span class="wl-tag {tcls}">{row['유형']}</span>
        <span class="wl-tag-out">LQ {row['LQ']:.2f}</span>
        <span class="wl-tag-out">종합 전국 {total_rank}위 / {N}</span>
      </div>
      <p class="wl-sum-typedesc">{TYPE_DESC.get(row['유형'], '')}</p>
    </div>
    """)


def render_score(row, rank_row):
    """오른쪽 패널 — 종합점수 · 세 축 막대 · 해석 문장."""
    total_rank = int(rank_row["종합점수"])

    bars = ""
    for label, col, cls in [("산업성", "점수_산업성", "industry"),
                            ("성장성", "점수_성장성", "growth"),
                            ("수요성", "점수_수요성", "demand")]:
        bars += (
            f'<div class="wl-sbar">'
            f'<div class="wl-sbar-head">'
            f'<span>{label}</span>'
            f'<b>{row[col]:.1f}</b>'
            f'<em>{int(rank_row[col])}위</em>'
            f'</div>'
            f'<div class="wl-sbar-track">'
            f'<i class="{cls}" style="width:{row[col]}%"></i>'
            f'</div></div>'
        )

    story = "".join(f"<li>{t}</li>" for t in story_lines(row))

    html(f"""
    <div class="wl-panel wl-scorepanel">
      <div class="wl-sum-total">
        <span class="wl-sum-total-label">종합점수</span>
        <span class="wl-sum-total-value">{row['종합점수']:.1f}</span>
        <span class="wl-sum-total-rank">전국 {total_rank}위 / {N}</span>
      </div>
      <div class="wl-sbars">{bars}</div>
      <ul class="wl-story">{story}</ul>
    </div>
    """)


# ══ 지도 ═══════════════════════════════════════════
TOOLTIP_STYLE = ("background:#fff; border:1px solid #DDE4EB; border-radius:6px;"
                 "padding:8px 10px; font-family:sans-serif; font-size:12.5px;")


def _shade(v, vmin, vmax):
    if v is None or pd.isna(v):
        return DIMMED
    i = int((v - vmin) / (vmax - vmin + 1e-9) * len(SHADES))
    return SHADES[min(i, len(SHADES) - 1)]


def build_map(sido_name):
    m = folium.Map(
        location=[36.3, 127.8], zoom_start=7,
        tiles=None, zoom_control=True,
        scrollWheelZoom=True, dragging=True,
    )

    if sido_name == "전체":
        # ── 1단계 : 시도 17개 ──────────────────────
        agg = passed.groupby("시도", as_index=False).agg(값=(metric_col, metric_how))
        name2val = dict(zip(agg["시도"], agg["값"]))

        def lookup(nm):
            if nm in name2val:
                return name2val[nm]
            for ours, theirs in SIDO_ALIAS.items():
                if nm in theirs and ours in name2val:
                    return name2val[ours]
            return None

        layer = load_geo_sido().copy()
        layer["값"] = layer["sidonm"].map(lookup)

        vals = layer["값"].dropna()
        vmin, vmax = (vals.min(), vals.max()) if len(vals) else (0, 1)

        folium.GeoJson(
            layer,
            style_function=lambda f: {
                "fillColor": _shade(f["properties"]["값"], vmin, vmax),
                "color": "#FFFFFF", "weight": 1.2, "fillOpacity": 0.9,
            },
            highlight_function=lambda f: {"weight": 2.5, "color": "#14293D",
                                          "fillOpacity": 1.0},
            tooltip=folium.GeoJsonTooltip(
                fields=["sidonm", "값"], aliases=["", f"{metric_label} "],
                sticky=True, style=TOOLTIP_STYLE,
            ),
        ).add_to(m)
        return m

    # ── 2단계 : 선택한 시도의 시군구 ─────────────────
    geo_sgg = load_geo_sgg()
    layer = geo_sgg[
        geo_sgg["sidonm"].apply(lambda nm: is_matching_sido(nm, sido_name))
    ][["sidonm", "sggnm", "geometry"]].copy()

    layer["표시명"] = layer["sggnm"].apply(
        lambda nm: sgg_display_name(sido_name, nm)
    )

    # 시도 안에서 색을 다시 나눈다. 전국 스케일이면 지방은 전부 옅어진다.
    in_sido = passed[passed["시도"] == sido_name]
    name2val = dict(zip(in_sido["시군구"], in_sido[metric_col]))
    vals = list(name2val.values())
    vmin, vmax = (min(vals), max(vals)) if vals else (0, 1)

    layer["값"] = layer["표시명"].map(name2val)

    def style(f):
        p = f["properties"]
        if p["표시명"] == sgg:
            return {"fillColor": HIGHLIGHT, "color": "#14293D",
                    "weight": 2.5, "fillOpacity": 0.85}
        return {"fillColor": _shade(p.get("값"), vmin, vmax),
                "color": "#FFFFFF", "weight": 1.0, "fillOpacity": 0.9}

    folium.GeoJson(
        layer, style_function=style,
        highlight_function=lambda f: {"weight": 2.5, "color": "#14293D",
                                      "fillOpacity": 1.0},
        tooltip=folium.GeoJsonTooltip(
            fields=["표시명", "값"], aliases=["", f"{metric_label} "],
            sticky=True, style=TOOLTIP_STYLE,
        ),
    ).add_to(m)

    if not layer.empty:
        minx, miny, maxx, maxy = layer.total_bounds
        # 좌표 두 쌍을 하나의 리스트로 묶어야 한다.
        # 따로 넘기면 두 번째가 max_zoom 자리로 들어가 지도가 안 보인다.
        m.fit_bounds([[miny, minx], [maxy, maxx]])

    return m


def handle_click(out, sido_name):
    if not out or not out.get("last_active_drawing"):
        return
    props = out["last_active_drawing"].get("properties", {})

    if sido_name == "전체":
        clicked = sido_display_name(props.get("sidonm", ""))
        if clicked and clicked != st.session_state.sido_select:
            st.session_state.pending_sido = clicked
            st.rerun()
    else:
        raw = props.get("sggnm", "")
        if raw:
            clicked = sgg_display_name(sido_name, raw)
            if clicked != st.session_state.sgg_select:
                st.session_state.pending_sgg = clicked
                st.rerun()


# ══ 렌더 ═══════════════════════════════════════════
col_left, col_right = st.columns([6, 4], gap="medium")

with col_left:
    if sel_row is not None:
        render_head(sel_row, sido, sgg, int(sel_rank["종합점수"]))
        render_evidence(sel_row, sel_rank)
    else:
        out = st_folium(build_map(sido), height=560, use_container_width=True,
                        returned_objects=["last_active_drawing"])
        handle_click(out, sido)

        swatches = "".join(f'<i style="background:{c}"></i>' for c in SHADES)
        html(f"""
        <div class="wl-legend">
        <span>{metric_label}</span>
        <span class="wl-legend-min">낮음</span>
        {swatches}
        <span class="wl-legend-max">높음</span>
        </div>
        """)


with col_right:
    if sel_row is not None:
        render_score(sel_row, sel_rank)

    elif scoped.empty:
        html('<div class="wl-panel wl-panel-empty">'
             '조건에 맞는 지역이 없습니다<br>필터를 넓혀 보세요</div>')

    else:
        rows = "".join(
            f'<div class="wl-rank-row">'
            f'<span class="wl-rank-no">{i}</span>'
            f'<span class="wl-rank-name">{r["시도"]} {r["시군구"]}</span>'
            f'<b class="wl-rank-val">{metric_fmt.format(r[metric_col])}</b>'
            f'</div>'
            for i, (_, r) in enumerate(scoped.head(14).iterrows(), 1)
        )
        html(f"""
        <div class="wl-panel">
          <div class="wl-rank-head">{scope_txt} &#183; {metric_label} 순</div>
          <div class="wl-rank">{rows}</div>
        </div>
        """)


# ══ 그래프 ═════════════════════════════════════════
# 위쪽에서 이미 답한 것(종합점수·세 축·지표 12개)을 반복하지 않는다.
#   추이   시간축 — 위쪽 숫자는 전부 한 시점이라 방향을 못 보여준다
#   산점도 위치 — 유형 라벨을 249개 안에서의 좌표로 보여준다
mode = st.radio(
    "보기", ["이 지역만", "전국 평균과 비교"],
    horizontal=True, label_visibility="collapsed",
)

if sel_row is None:
    html("""
    <div class="wl-chart-ph">
    지역을 선택하면 그래프가 표시됩니다
    <span>추이와 경합도 산점도</span>
    </div>
    """)
elif mode == "전국 평균과 비교":
    html("""
    <div class="wl-chart-ph">
    비교 모드는 준비 중입니다
    <span>전국 평균선을 겹쳐 그릴 예정</span>
    </div>
    """)
else:
    g1, g2 = st.columns(2, gap="medium")

    with g1:
        html(f'<div class="wl-chart-title">{sgg} &#183; 37개월 추이</div>')
        # TODO: 월별 원자료가 준비되면 charts.trend_chart(...) 로 교체
        html("""
        <div class="wl-chart-ph">
        추이 차트
        <span>월별 원자료 준비 중</span>
        </div>
        """)

    with g2:
        html('<div class="wl-chart-title">경합도 · 전국 249개 중 위치</div>')
        charts.quadrant_chart(df, selected=sel_row["지역"], key="quadrant")