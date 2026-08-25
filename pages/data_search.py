"""데이터 조회 — 기존 지도·상세 레이아웃에 MySQL backend 데이터를 연결한다."""
from html import escape
from urllib.parse import urlencode

import streamlit as st
from ui.layout import html, load_logo_b64, setup

setup(page="explore", active="데이터 조회")

loading_ph = st.empty()
with loading_ph.container():
    html(f"""
    <div class="wl-loading">
      <img src="data:image/png;base64,{load_logo_b64()}" class="wl-loading-logo" alt=""/>
      <p class="wl-loading-title">전국 249개 지역을 계산하고 있습니다</p>
      <p class="wl-loading-sub">화물차 등록 현황과 인구 통계를 결합해<br>산업성 · 성장성 · 수요성 지수를 산출합니다</p>
    </div>
    """)

import admdongkor as adk
import folium
import pandas as pd
from pymysql import MySQLError
from streamlit_folium import st_folium

from ui import charts
from ui.backend import get_db
from web.backend import (get_freight_per_population_trend,
    get_logistics_ranking, get_logistics_score,
    get_province_freight_counts, get_region_detail, get_region_trend,
    get_regions, get_regions_by_province, get_supplemental_logistics_metrics)

TARGET_MONTH, TREND_START, TREND_END = "2026-07", "2023-07", "2026-07"
METRICS = {
    "종합점수": ("종합점수", "mean", "{:.1f}"), "산업성": ("점수_산업성", "mean", "{:.1f}"),
    "성장성": ("점수_성장성", "mean", "{:.1f}"), "수요성": ("점수_수요성", "mean", "{:.1f}"),
    "화물차": ("화물차", "sum", "{:,.0f}대")}
EVIDENCE_FIELDS = {
    "산업성": [
        ("영업용 비중", "영업용비중", "{:.1f}%"),
        ("입지계수 LQ", "LQ", "{:.2f}"),
        ("화물차 비율", "화물차비율", "{:.1f}%"),
        ("인구 1천명당 화물차", "인구1천명당화물차", "{:,.1f}대"),
    ],
    "성장성": [
        ("인구-화물 디커플링", "디커플링", "{:+.1f}%p"),
        ("12개월 가속도", "가속도", "{:+.1f}%p"),
        ("추세 지속성", "추세지속성", "{:.2f}"),
        ("영업용 전환율", "영업용전환율", "{:.2f}"),
        ("화물차 전년동월비", "화물차_증가율", "{:+.1f}%"),
        ("안정성", "안정성", "{:.3f}"),
    ],
    "수요성": [
        ("인접권 인구", "인접권인구", "{:,.0f}명"),
        ("자체 인구", "인구수", "{:,.0f}명"),
        ("인구 밀도", "인구밀도", "{:,.1f}명/km²"),
        ("인구 증가율", "인구_증가율", "{:+.1f}%"),
    ],
}
CATEGORY_CLASS = {"산업성": "industry", "성장성": "growth", "수요성": "demand"}
SCORE_COL = {"산업성": "점수_산업성", "성장성": "점수_성장성", "수요성": "점수_수요성"}
SHADES, DIMMED, HIGHLIGHT = ["#E6F1FB", "#B5D4F4", "#85B7EB", "#378ADD", "#185FA5"], "#EFF2F5", "#FF7A45"
SIDO_ALIAS = {"전남광주통합특별시": ["전남광주통합특별시", "광주광역시", "전라남도"]}

# 하단 근거지표 레이더에 쓰는 8개 축 — EVIDENCE_FIELDS 중 스케일이 안정적인 지표만 선별
RADAR_FIELDS = [
    ("입지계수 LQ", "LQ"), ("화물차 비율", "화물차비율"),
    ("1천명당 화물차", "인구1천명당화물차"), ("디커플링", "디커플링"),
    ("안정성", "안정성"), ("자체 인구", "인구수"),
    ("인구 밀도", "인구밀도"), ("영업용 비중", "영업용비중"),
]

def split_region_name(name):
    sido, _, sgg = name.partition(" ")
    return sido, sgg or sido

@st.cache_data(ttl=3600)
def load_region_data():
    regions = get_regions(get_db())
    scored = {r["region_code"]: r for r in get_logistics_ranking(
        get_db(), TARGET_MONTH, limit=max(len(regions), 1))}
    supplemental = {
        r["region_code"]: r
        for r in get_supplemental_logistics_metrics(get_db(), TARGET_MONTH)
    }
    rows = []
    for region in regions:
        result = scored.get(region["region_code"])
        if result is None:
            continue
        sido, sgg = split_region_name(region["region_name"])
        raw, scores = result["raw"], result["scores"]
        extra = supplemental.get(region["region_code"], {}).get("raw", {})
        rows.append({"region_code": region["region_code"], "지역": region["region_name"], "시도": sido,
            "시군구": sgg, "종합점수": scores["total"], "점수_산업성": scores["industry"],
            "점수_성장성": scores["growth"], "점수_수요성": scores["demand"],
            "화물차": raw["truck_count"], "차량총": raw["total_vehicle_count"],
            "화물차비율": raw["truck_ratio"], "화물차_증가율": raw["yoy_growth"],
            "가속도": raw["acceleration"], "인구수": raw["population"],
            "인구1만명당화물차": raw["truck_per_10000"],
            "인구1천명당화물차": raw.get("truck_per_1000"),
            "LQ": extra.get("location_quotient"),
            "영업용비중": extra.get("commercial_truck_share"),
            "추세지속성": extra.get("trend_persistence"),
            "영업용전환율": extra.get("commercial_conversion_rate"),
            "디커플링": extra.get("decoupling"),
            "안정성": extra.get("stability"),
            "인접권인구": extra.get("adjacent_population"),
            "인구_증가율": extra.get("population_yoy_growth"),
            "인구_성장지속성": extra.get("population_trend_persistence"),
            "면적_km2": extra.get("area_km2"),
            "인구밀도": extra.get("population_density"),
            "화물차밀도": extra.get("freight_density")})
    data = pd.DataFrame(rows)
    if not data.empty:
        growth_mean = data["화물차_증가율"].mean()
        density_mean = data["화물차밀도"].mean()
        data["유형"] = data.apply(
            lambda row: classify_region(row["화물차밀도"], row["화물차_증가율"], density_mean, growth_mean),
            axis=1,
        )
    return data, get_province_freight_counts(get_db(), TARGET_MONTH)


def classify_region(density, growth, density_mean, growth_mean):
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
def load_province_regions(province): return get_regions_by_province(get_db(), province)

@st.cache_data(ttl=3600)
def load_selected_detail(code):
    return get_region_detail(get_db(), code, TARGET_MONTH), get_logistics_score(get_db(), code, TARGET_MONTH)

@st.cache_data(ttl=3600)
def load_trend(code): return get_region_trend(get_db(), code, TREND_START, TREND_END)


@st.cache_data(ttl=3600)
def load_freight_trend(code=None, province=None):
    rows = get_freight_per_population_trend(
        get_db(), TREND_START, TREND_END,
        province_name=province, region_code=code,
    )
    return pd.DataFrame(rows).rename(columns={
        "date": "연월", "truck_count": "화물차수",
        "truck_per_1000": "인구천명당_화물차",
        "national_truck_per_1000": "전국평균",
    })

@st.cache_data
def load_geo_sido():
    g = adk.get("20260201", level="sido").to_crs(epsg=4326); g["geometry"] = g["geometry"].simplify(0.002); return g

@st.cache_data
def load_geo_sgg():
    g = adk.get("20260201", level="sgg").to_crs(epsg=4326); g["geometry"] = g["geometry"].simplify(0.0005); return g

try:
    df, province_freight_rows = load_region_data()
except (MySQLError, OSError, ValueError) as error:
    loading_ph.empty()
    st.error("MySQL 데이터를 불러오지 못했습니다. .env와 DB 실행 상태를 확인해주세요.")
    st.caption(str(error)); st.stop()

if df.empty:
    loading_ph.empty()
    st.warning(f"{TARGET_MONTH}에 점수를 계산할 수 있는 지역 데이터가 없습니다."); st.stop()

ranks = df.select_dtypes(include="number").rank(ascending=False, method="min", na_option="bottom").astype(int)
N = len(df)

def is_matching_sido(geo_name, db_name):
    return geo_name == db_name or any(geo_name in names and db_name in names for names in SIDO_ALIAS.values())

def sido_display_name(geo_name):
    return next((name for name in df["시도"].unique() if is_matching_sido(geo_name, name)), geo_name)

def sgg_display_name(sido, geo_name):
    target = geo_name.replace(" ", "")
    for candidate in df[df["시도"] == sido]["시군구"].unique():
        normalized = candidate.replace(" ", "")
        if normalized == target or target in normalized or normalized in target: return candidate
    return geo_name

for key, value in [("sido_select", "전체"), ("sgg_select", "전체")]: st.session_state.setdefault(key, value)
qp = st.query_params
if "sido" in qp and "sgg" in qp:
    st.session_state.pending_sido = qp["sido"]
    st.session_state.pending_sgg = qp["sgg"]
    st.query_params.clear()
if "pending_sido" in st.session_state:
    st.session_state.sido_select = st.session_state.pop("pending_sido"); st.session_state.sgg_select = "전체"
if "pending_sgg" in st.session_state: st.session_state.sgg_select = st.session_state.pop("pending_sgg")
def _on_sido_change(): st.session_state.sgg_select = "전체"

c1, c2, c3, c4, c5 = st.columns(
    [1.5, 1.8, 2.0, 2.4, 1.4], vertical_alignment="center"
)
with c1:
    sido = st.selectbox("시도", ["전체"] + sorted(df["시도"].unique()), key="sido_select",
                        on_change=_on_sido_change, label_visibility="collapsed")
with c2:
    if sido == "전체": sgg_opts = ["전체"]
    else:
        codes = {r["region_code"] for r in load_province_regions(sido)}
        sgg_opts = ["전체"] + sorted(df[df["region_code"].isin(codes)]["시군구"])
    sgg = st.selectbox("시군구", sgg_opts, disabled=sido == "전체", key="sgg_select", label_visibility="collapsed")
with c3:
    picked = st.multiselect(
        "유형", ["미개척", "성장 중", "포화", "정체"],
        placeholder="유형 전체", label_visibility="collapsed"
    )
with c4:
    lo, hi = int(df["인구수"].min()), int(df["인구수"].max())
    html('<div class="wl-pop-filter-label">인구 배후</div>')
    pop = st.slider(
        "인구", lo, hi, (lo, hi), step=10_000, label_visibility="collapsed"
    )
with c5:
    metric_label = st.selectbox("지표", list(METRICS), label_visibility="collapsed")
metric_col, metric_how, metric_fmt = METRICS[metric_label]
passed = df[(df["인구수"] >= pop[0]) & (df["인구수"] <= pop[1])]
if picked:
    passed = passed[passed["유형"].isin(picked)]
scoped = (passed if sido == "전체" else passed[passed["시도"] == sido]).sort_values(metric_col, ascending=False)
sel_row = sel_rank = None
if sgg != "전체":
    hit = df[(df["시도"] == sido) & (df["시군구"] == sgg)]
    if not hit.empty: sel_row, sel_rank = hit.iloc[0], ranks.loc[hit.index[0]]
scope_txt, denom = ("전국" if sido == "전체" else sido), (N if sido == "전체" else len(df[df["시도"] == sido]))

# 시군구를 선택하면 지도/필터 메타 안내는 더 이상 의미가 없으므로 상세보기에서는 생략한다.
if sel_row is None:
    html(f'<div class="wl-meta">{scope_txt} <b>{len(scoped)}개</b> / {denom}개 지역 &#183; 지도는 <b>{metric_label}</b> 기준 &#183; {TARGET_MONTH}</div>')

def story_lines(row):
    lines = []
    if pd.notna(row["화물차_증가율"]):
        word = "늘었습니다" if row["화물차_증가율"] >= 0 else "줄었습니다"
        lines.append(f"화물차가 전년 동월보다 {abs(row['화물차_증가율']):.1f}% {word}.")
    if pd.notna(row["화물차비율"]): lines.append(f"전체 등록 차량 중 화물차 비율은 {row['화물차비율']:.1f}%입니다.")
    if pd.notna(row["인구수"]): lines.append(f"기준월 자체 인구는 {row['인구수']:,.0f}명입니다.")
    return lines

def render_head(row, total_rank, n):
    """뒤로가기 + 지역명 타이틀."""
    with st.container(key="detail_back_btn"):
        if st.button("← 지도로", key="btn_back_to_map"):
            st.session_state.pending_sgg = "전체"; st.rerun()
    html(
        f'<div class="wl-sum-head">'
        f'<div class="wl-sum-sido">{row["시도"]}</div><h1 class="wl-sum-name">{row["시군구"]}</h1>'
        f'<div class="wl-sum-tags">'
        f'<span class="wl-tag-out">종합 전국 {total_rank}위 / {n}</span>'
        f'</div></div>'
    )

def render_hero(row, rank_row, n):
    """종합점수(도넛 게이지) + 3개 카테고리 점수바를 한 줄에 — 진입 즉시 전체 그림."""
    bars = ""
    for label, col, cls in [("산업성", "점수_산업성", "industry"), ("성장성", "점수_성장성", "growth"), ("수요성", "점수_수요성", "demand")]:
        bars += (
            f'<div class="wl-hbar">'
            f'<div class="wl-hbar-head"><span>{label}</span><b>{row[col]:.1f}</b><em>{int(rank_row[col])}위</em></div>'
            f'<div class="wl-hbar-track"><i class="{cls}" style="width:{row[col]}%"></i></div>'
            f'</div>'
        )
    html(
        f'<div class="wl-detail-hero">'
        f'<div class="wl-gauge" style="--pct:{row["종합점수"]}">'
        f'<span class="wl-gauge-value">{row["종합점수"]:.1f}</span>'
        f'</div>'
        f'<div class="wl-detail-hero-info">'
        f'<span class="wl-detail-hero-label">종합점수</span>'
        f'<span class="wl-detail-hero-rank">전국 {int(rank_row["종합점수"])}위 / {n}</span>'
        f'</div>'
        f'<div class="wl-detail-hero-bars">{bars}</div>'
        f'</div>'
    )

def render_insight_chips(row):
    """스토리 문장을 가로 알약 형태로 — 공간 최소, 핵심 즉시 전달."""
    lines = story_lines(row)
    if not lines:
        return
    chips = "".join(f'<span class="wl-chip">{line}</span>' for line in lines)
    html(f'<div class="wl-chip-row">{chips}</div>')

def render_evidence_grid(row, rank_row, n):
    """카테고리 3개를 가로로. 지표마다 값 + 퍼센타일 바로 상대적 위치를 시각화."""
    groups = ""
    for category, fields in EVIDENCE_FIELDS.items():
        score_col = SCORE_COL[category]
        cards = ""
        for label, ev_col, fmt in fields:
            available = ev_col is not None and pd.notna(row[ev_col])
            if available:
                rank = int(rank_row[ev_col])
                percentile = max(0, min(100, (n - rank + 1) / n * 100))
                top = "wl-top" if rank <= n * 0.2 else ""
                value_text = fmt.format(row[ev_col])
                rank_text = f"전국 {rank}위"
            else:
                percentile, top = 0, ""
                value_text, rank_text = "데이터 없음", "순위 없음"
            cards += (
                f'<div class="wl-metric-card">'
                f'<span class="wl-metric-label">{label}</span>'
                f'<b class="wl-metric-value">{value_text}</b>'
                f'<div class="wl-metric-bar-track">'
                f'<div class="wl-metric-bar-fill {top}" style="width:{percentile:.0f}%"></div>'
                f'</div>'
                f'<span class="wl-metric-rank">{rank_text}</span>'
                f'</div>'
            )
        groups += (
            f'<div class="wl-evidence-group wl-cat-{CATEGORY_CLASS[category]}">'
            f'<div class="wl-evidence-title"><span>{category}</span><b>{row[score_col]:.1f}</b>'
            f'<em>전국 {int(rank_row[score_col])}위 / {n}</em></div>'
            f'<div class="wl-metric-grid">{cards}</div></div>'
        )
    html(f'<div class="wl-evidence-row">{groups}</div>')

TOOLTIP_STYLE = "background:#fff; border:1px solid #DDE4EB; border-radius:6px;padding:8px 10px; font-family:sans-serif; font-size:12.5px;"
def _shade(value, vmin, vmax):
    if value is None or pd.isna(value): return DIMMED
    return SHADES[min(int((value-vmin)/(vmax-vmin+1e-9)*len(SHADES)), len(SHADES)-1)]

def build_map(sido_name):
    m = folium.Map(location=[36.3, 127.8], zoom_start=7, tiles=None, zoom_control=True, scrollWheelZoom=True, dragging=True)
    if sido_name == "전체":
        if metric_label == "화물차": name2val = {r["province_name"]: r["vehicle_count"] for r in province_freight_rows}
        else:
            agg = df.groupby("시도", as_index=False).agg(값=(metric_col, metric_how)); name2val = dict(zip(agg["시도"], agg["값"]))
        def lookup(name): return name2val.get(name, next((v for k, v in name2val.items() if is_matching_sido(name, k)), None))
        layer = load_geo_sido().copy(); layer["값"] = layer["sidonm"].map(lookup); layer["값"] = layer["값"].round(2)
        vals = layer["값"].dropna()
        vmin, vmax = (vals.min(), vals.max()) if len(vals) else (0, 1)
        folium.GeoJson(layer, style_function=lambda f: {"fillColor": _shade(f["properties"]["값"],vmin,vmax),"color":"#FFFFFF","weight":1.2,"fillOpacity":.9}, highlight_function=lambda f:{"weight":2.5,"color":"#14293D","fillOpacity":1}, tooltip=folium.GeoJsonTooltip(fields=["sidonm","값"],aliases=["",f"{metric_label} "],sticky=True,style=TOOLTIP_STYLE)).add_to(m); return m
    geo = load_geo_sgg(); layer = geo[geo["sidonm"].apply(lambda n:is_matching_sido(n,sido_name))][["sidonm","sggnm","geometry"]].copy()
    layer["표시명"] = layer["sggnm"].apply(lambda n:sgg_display_name(sido_name,n)); name2val=dict(zip(scoped["시군구"],scoped[metric_col])); vals=[v for v in name2val.values() if pd.notna(v)]; vmin,vmax=(min(vals),max(vals)) if vals else (0,1); layer["값"]=layer["표시명"].map(name2val)
    layer["값"]=layer["값"].round(2)
    def style(f):
        p=f["properties"]
        return {"fillColor":HIGHLIGHT,"color":"#14293D","weight":2.5,"fillOpacity":.85} if p["표시명"]==sgg else {"fillColor":_shade(p.get("값"),vmin,vmax),"color":"#FFFFFF","weight":1,"fillOpacity":.9}
    folium.GeoJson(layer,style_function=style,highlight_function=lambda f:{"weight":2.5,"color":"#14293D","fillOpacity":1},tooltip=folium.GeoJsonTooltip(fields=["표시명","값"],aliases=["",f"{metric_label} "],sticky=True,style=TOOLTIP_STYLE)).add_to(m)
    if not layer.empty:
        minx,miny,maxx,maxy=layer.total_bounds; m.fit_bounds([[miny,minx],[maxy,maxx]])
    return m

def handle_click(out,sido_name):
    if not out or not out.get("last_active_drawing"): return
    props=out["last_active_drawing"].get("properties",{})
    if sido_name=="전체":
        clicked=sido_display_name(props.get("sidonm",""))
        if clicked and clicked!=st.session_state.sido_select: st.session_state.pending_sido=clicked; st.rerun()
    else:
        clicked=sgg_display_name(sido_name,props.get("sggnm",""))
        if clicked and clicked!=st.session_state.sgg_select: st.session_state.pending_sgg=clicked; st.rerun()

# ---------------------------------------------------------------------------
# 메인 레이아웃 분기
# 시군구를 선택한 경우: 지도가 필요 없으므로 6:4 분할을 버리고 풀폭 상세보기로 전환.
# 시군구 미선택(전국/시도만): 기존처럼 지도(6) + 랭킹(4) 유지.
# ---------------------------------------------------------------------------
if sel_row is not None:
    detail, score = load_selected_detail(sel_row["region_code"])
    if detail["region"] is None or score is None:
        st.warning("선택 지역의 상세 데이터를 찾을 수 없습니다.")
    render_head(sel_row, int(sel_rank["종합점수"]), N)
    render_hero(sel_row, sel_rank, N)
    render_insight_chips(sel_row)
    render_evidence_grid(sel_row, sel_rank, N)
else:
    col_left, col_right = st.columns([6, 4], gap="medium")
    with col_left:
        out = st_folium(build_map(sido), height=560, use_container_width=True, returned_objects=["last_active_drawing"])
        handle_click(out, sido)
        swatches = "".join(f'<i style="background:{c}"></i>' for c in SHADES)
        html(f'<div class="wl-legend"><span>{metric_label}</span><span class="wl-legend-min">낮음</span>{swatches}<span class="wl-legend-max">높음</span></div>')
    with col_right:
        if scoped.empty:
            html('<div class="wl-panel wl-panel-empty">표시할 지역 데이터가 없습니다</div>')
        else:
            rows = "".join(
                f'<a class="wl-rank-row" href="?{urlencode({"sido": str(r["시도"]), "sgg": str(r["시군구"])})}" target="_self">'
                f'<span class="wl-rank-no">{i}</span>'
                f'<span class="wl-rank-name">{escape(str(r["시도"]))} {escape(str(r["시군구"]))}</span>'
                f'<b class="wl-rank-val">{escape(metric_fmt.format(r[metric_col]))}</b></a>'
                for i, (_, r) in enumerate(scoped.head(10).iterrows(), 1)
            )
            html(f'<div class="wl-panel wl-rank-panel"><div class="wl-rank-head">{scope_txt} &#183; {metric_label} 순</div><div class="wl-rank">{rows}</div></div>')

TYPES = ["미개척", "성장 중", "포화", "정체"]

def ph(title, sub, height=320):
    html(f'<div class="wl-chart-ph" style="height:{height}px">{title}<span>{sub}</span></div>')

level = "시군구" if sel_row is not None else ("시도" if sido != "전체" else "전국")
scope_name = sgg if level == "시군구" else (sido if level == "시도" else "전국")
scope_df = passed[passed["시도"] == sido] if level == "시군구" else scoped
if scope_df.empty:
    scope_df = df if level == "전국" else df[df["시도"] == sido]

# 시군구 상세는 이미 히어로+근거지표에서 종합점수·화물차비율·인구 등을 전부 보여줬으므로
# 아래 차트 섹션 제목도 "요약 지표"가 아니라 "추이·구성" 성격임을 분명히 한다.
chart_title = "차량 구성 · 추이" if level == "시군구" else f"{scope_name} · 상세 분석"
html(f'<div class="wl-chart-title">{chart_title}</div>')

def build_metrics():
    """전국/시도 스코프 요약 KPI. 시군구는 위 히어로+근거지표와 중복이라 호출하지 않는다.

    라디오 버튼을 없앤 뒤로는 전국이 아닌 모든 스코프에서 항상 전국 평균 대비
    delta 를 함께 보여준다.
    """
    def avg_delta(col):
        return f'{scope_df[col].mean() - df[col].mean():+.1f}' if level != "전국" else None

    return [
        {"label": "지역 수", "value": f"{len(scope_df):,}개"},
        {"label": "평균 종합점수", "value": f'{scope_df["종합점수"].mean():.1f}',
         "delta": avg_delta("종합점수")},
        {"label": "평균 화물차 비율", "value": f'{scope_df["화물차비율"].mean():.1f}%',
         "delta": avg_delta("화물차비율")},
        {"label": "화물차 합계", "value": f'{scope_df["화물차"].sum():,.0f}대'},
    ]

def build_radar_values(row, rank_row, n):
    """근거지표 8개를 전국 percentile(0~100)로 변환 — 단위가 달라 원값을 그대로 못 쓴다."""
    values = {}
    for label, col in RADAR_FIELDS:
        if pd.notna(row[col]):
            rank = int(rank_row[col])
            values[label] = max(0, min(100, (n - rank + 1) / n * 100))
    return values

def build_compare_df():
    """시도/시군구 스코프에서 산업성·성장성·수요성 그룹 막대용 비교 데이터.

    시군구는 [해당 지역, 소속 시도 평균, 전국 평균] 3행,
    시도는 [해당 시도 평균, 전국 평균] 2행을 만든다.
    """
    cols = ["점수_산업성", "점수_성장성", "점수_수요성"]
    if level == "시군구":
        province_df = df[df["시도"] == sido]
        rows = [
            {"지역": sel_row["시군구"], **{c: sel_row[c] for c in cols}},
            {"지역": f"{sido} 평균", **{c: province_df[c].mean() for c in cols}},
            {"지역": "전국 평균", **{c: df[c].mean() for c in cols}},
        ]
        return pd.DataFrame(rows), sel_row["시군구"]
    rows = [
        {"지역": scope_name, **{c: scope_df[c].mean() for c in cols}},
        {"지역": "전국 평균", **{c: df[c].mean() for c in cols}},
    ]
    return pd.DataFrame(rows), scope_name

# 시군구 상세에서는 히어로+근거지표가 이미 요약을 다 보여줬으므로 중복 KPI 줄을 생략한다.
if level != "시군구":
    charts.metric_row(build_metrics())

detail = None
if sel_row is not None:
    detail, _ = load_selected_detail(sel_row["region_code"])

with st.container(key="chart_grid_narrow"):
    a1, a2 = st.columns(2, gap="medium")
    with a1:
        with st.container(border=True):
            html('<div class="wl-chart-sub">차량 구성비</div>')
            if level == "시군구" and detail:
                category_df = pd.DataFrame(detail["vehicle_categories"])
                if category_df.empty:
                    ph("차량 구성비", "기준월 카테고리 데이터 없음")
                else:
                    shares = category_df.groupby("category_main")["vehicle_count"].sum().to_dict()
                    national_freight = df["화물차"].sum() / df["차량총"].sum() * 100
                    avg = {"화물": national_freight, "그 외 차량": 100 - national_freight}
                    charts.composition_bar(shares, avg=avg, label=sgg, key="compo")
            else:
                freight = scope_df["화물차"].sum() / scope_df["차량총"].sum() * 100
                national_freight = df["화물차"].sum() / df["차량총"].sum() * 100
                charts.composition_bar(
                    {"화물": freight, "그 외 차량": 100 - freight},
                    avg={"화물": national_freight, "그 외 차량": 100 - national_freight},
                    label=f"{scope_name} 합계", key="compo",
                )

    with a2:
        with st.container(border=True):
            if level == "전국":
                html('<div class="wl-chart-sub">유형별 지역 수</div>')
                counts = scope_df["유형"].value_counts()
                charts.type_bar(
                    {name: int(counts.get(name, 0)) for name in TYPES}, key="typebar",
                )
            else:
                html('<div class="wl-chart-sub">산업성 · 성장성 · 수요성 비교</div>')
                compare_df, highlight = build_compare_df()
                charts.group_bar(compare_df, name_col="지역", selected=highlight, key="groupbar")

    b1, b2 = st.columns(2, gap="medium")
    freight_trend = load_freight_trend(
        code=sel_row["region_code"] if sel_row is not None else None,
        province=sido if level == "시도" else None,
    )
    with b1:
        with st.container(border=True):
            if level == "시군구":
                html('<div class="wl-chart-sub">근거지표 프로파일</div>')
                radar_values = build_radar_values(sel_row, sel_rank, N)
                charts.evidence_radar_chart(radar_values, key="evidence_radar")
            else:
                html('<div class="wl-chart-sub">화물차 전년 대비 증감률</div>')
                if freight_trend.empty:
                    ph("연도별 증감", "월별 화물차 데이터 없음")
                else:
                    yearly = freight_trend.copy()
                    yearly["연도"] = yearly["연월"].str[:4]
                    yearly["월"] = yearly["연월"].str[5:7].astype(int)
                    cutoff = int(TARGET_MONTH[-2:])
                    yearly = yearly[yearly["월"] == cutoff][["연도", "화물차수"]]
                    charts.yoy_chart(yearly, key="yoy")
    with b2:
        with st.container(border=True):
            html('<div class="wl-chart-sub">인구 1천명당 화물차 · 37개월</div>')
            series = {"인구천명당_화물차": scope_name, "전국평균": "전국 평균"}
            charts.trend_chart(
                freight_trend, x_col="연월", series=series, key="trend",
                data_palette=True,
            )

loading_ph.empty()