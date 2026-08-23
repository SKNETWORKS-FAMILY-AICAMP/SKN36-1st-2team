"""데이터 조회 — 기존 지도·상세 레이아웃에 MySQL backend 데이터를 연결한다."""
import admdongkor as adk
import folium
import pandas as pd
import streamlit as st
from pymysql import MySQLError
from streamlit_folium import st_folium

from ui import charts
from ui.backend import get_db
from ui.layout import setup, html
from web.backend import (get_logistics_ranking, get_logistics_score,
    get_province_freight_counts, get_region_detail, get_region_trend,
    get_regions, get_regions_by_province, get_supplemental_logistics_metrics)

setup(page="explore", active="데이터 조회")
TARGET_MONTH, TREND_START, TREND_END = "2026-07", "2023-07", "2026-07"
METRICS = {
    "종합점수": ("종합점수", "mean", "{:.1f}"), "산업성": ("점수_산업성", "mean", "{:.1f}"),
    "성장성": ("점수_성장성", "mean", "{:.1f}"), "수요성": ("점수_수요성", "mean", "{:.1f}"),
    "화물차": ("화물차", "sum", "{:,.0f}대")}
EVIDENCE_FIELDS = {
    "산업성": [
        ("입지계수 LQ", "LQ", "{:.2f}"),
        ("영업용 비중", "영업용비중", "{:.1f}%"),
        ("화물차 비율", "화물차비율", "{:.1f}%"),
        ("화물차 대수", "화물차", "{:,.0f}대"),
    ],
    "성장성": [
        ("화물차 증가율", "화물차_증가율", "{:+.1f}%"),
        ("가속도", "가속도", "{:+.1f}%p"),
        ("추세 지속성", "추세지속성", "{:.2f}"),
        ("영업용 전환율", "영업용전환율", "{:.2f}"),
    ],
    "수요성": [
        ("인구 성장 지속성", "인구_성장지속성", "{:.1f}%"),
        ("자체 인구", "인구수", "{:,.0f}명"),
        ("인구 밀도", "인구밀도", "{:,.1f}명/km²"),
        ("인구 증가율", "인구_증가율", "{:+.1f}%"),
    ],
}
CATEGORY_CLASS = {"산업성": "industry", "성장성": "growth", "수요성": "demand"}
SCORE_COL = {"산업성": "점수_산업성", "성장성": "점수_성장성", "수요성": "점수_수요성"}
SHADES, DIMMED, HIGHLIGHT = ["#E6F1FB", "#B5D4F4", "#85B7EB", "#378ADD", "#185FA5"], "#EFF2F5", "#FF7A45"
SIDO_ALIAS = {"전남광주통합특별시": ["전남광주통합특별시", "광주광역시", "전라남도"]}

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
            "LQ": extra.get("location_quotient"),
            "영업용비중": extra.get("commercial_truck_share"),
            "추세지속성": extra.get("trend_persistence"),
            "영업용전환율": extra.get("commercial_conversion_rate"),
            "인구_증가율": extra.get("population_yoy_growth"),
            "인구_성장지속성": extra.get("population_trend_persistence"),
            "면적_km2": extra.get("area_km2"),
            "인구밀도": extra.get("population_density")})
    return pd.DataFrame(rows), get_province_freight_counts(get_db(), TARGET_MONTH)

@st.cache_data(ttl=3600)
def load_province_regions(province): return get_regions_by_province(get_db(), province)

@st.cache_data(ttl=3600)
def load_selected_detail(code):
    return get_region_detail(get_db(), code, TARGET_MONTH), get_logistics_score(get_db(), code, TARGET_MONTH)

@st.cache_data(ttl=3600)
def load_trend(code): return get_region_trend(get_db(), code, TREND_START, TREND_END)

@st.cache_data
def load_geo_sido():
    g = adk.get("20260201", level="sido").to_crs(epsg=4326); g["geometry"] = g["geometry"].simplify(0.002); return g

@st.cache_data
def load_geo_sgg():
    g = adk.get("20260201", level="sgg").to_crs(epsg=4326); g["geometry"] = g["geometry"].simplify(0.0005); return g

try:
    df, province_freight_rows = load_region_data()
except (MySQLError, OSError, ValueError) as error:
    st.error("MySQL 데이터를 불러오지 못했습니다. .env와 DB 실행 상태를 확인해주세요.")
    st.caption(str(error)); st.stop()
if df.empty:
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
    # 유형은 원본 UI 자리를 유지하되, 실제 DB에 근거 컬럼이 없으므로 가짜 옵션을 만들지 않는다.
    picked = st.multiselect(
        "유형", [], placeholder="유형 전체", label_visibility="collapsed"
    )
with c4:
    # 원본의 slider 위치를 유지하고 실제 DB 자체 인구로 필터링한다.
    lo, hi = int(df["인구수"].min()), int(df["인구수"].max())
    pop = st.slider(
        "인구", lo, hi, (lo, hi), step=10_000, label_visibility="collapsed"
    )
with c5:
    metric_label = st.selectbox("지표", list(METRICS), label_visibility="collapsed")
metric_col, metric_how, metric_fmt = METRICS[metric_label]
passed = df[(df["인구수"] >= pop[0]) & (df["인구수"] <= pop[1])]
scoped = (passed if sido == "전체" else passed[passed["시도"] == sido]).sort_values(metric_col, ascending=False)
sel_row = sel_rank = None
if sgg != "전체":
    hit = df[(df["시도"] == sido) & (df["시군구"] == sgg)]
    if not hit.empty: sel_row, sel_rank = hit.iloc[0], ranks.loc[hit.index[0]]
scope_txt, denom = ("전국" if sido == "전체" else sido), (N if sido == "전체" else len(df[df["시도"] == sido]))
html(f'<div class="wl-meta">{scope_txt} <b>{len(scoped)}개</b> / {denom}개 지역 &#183; 지도는 <b>{metric_label}</b> 기준 &#183; {TARGET_MONTH}</div>')

def story_lines(row):
    lines = []
    if pd.notna(row["화물차_증가율"]):
        word = "늘었습니다" if row["화물차_증가율"] >= 0 else "줄었습니다"
        lines.append(f"화물차가 전년 동월보다 {abs(row['화물차_증가율']):.1f}% {word}.")
    if pd.notna(row["화물차비율"]): lines.append(f"전체 등록 차량 중 화물차 비율은 {row['화물차비율']:.1f}%입니다.")
    if pd.notna(row["인구수"]): lines.append(f"기준월 자체 인구는 {row['인구수']:,.0f}명입니다.")
    return lines

def render_evidence(row, rank_row):
    groups = ""
    for category, fields in EVIDENCE_FIELDS.items():
        col, cards = SCORE_COL[category], ""
        for label, ev_col, fmt in fields:
            available = ev_col is not None and pd.notna(row[ev_col])
            if available:
                rank = int(rank_row[ev_col])
                top = "wl-top" if rank <= N * .2 else ""
                value_text = fmt.format(row[ev_col])
                rank_text = f"전국 {rank}위"
                unavailable = ""
            else:
                top = ""
                value_text = "데이터 없음"
                rank_text = "순위 없음"
                unavailable = " wl-unavailable"
            cards += (
                f'<div class="wl-evidence-card{unavailable}">'
                f'<span class="wl-evidence-label">{label}</span>'
                f'<b class="wl-evidence-value">{value_text}</b>'
                f'<span class="wl-evidence-rank {top}">{rank_text}</span>'
                f'</div>'
            )
        groups += f'<div class="wl-evidence-group wl-cat-{CATEGORY_CLASS[category]}"><div class="wl-evidence-title"><span>{category}</span><b>{row[col]:.1f}</b><em>전국 {int(rank_row[col])}위 / {N}</em></div><div class="wl-evidence-grid">{cards}</div></div>'
    html(groups)

def render_head(row, total_rank):
    with st.container(key="detail_back_btn"):
        if st.button("← 지도로", key="btn_back_to_map"):
            st.session_state.pending_sgg = "전체"; st.rerun()
    html(f'<div class="wl-sum-head"><div class="wl-sum-sido">{row["시도"]}</div><h1 class="wl-sum-name">{row["시군구"]}</h1><div class="wl-sum-tags"><span class="wl-tag-out">종합 전국 {total_rank}위 / {N}</span><span class="wl-tag-out">DB 지역코드 {row["region_code"]}</span></div></div>')

def render_score(row, rank_row):
    bars = ""
    for label, col, cls in [("산업성", "점수_산업성", "industry"), ("성장성", "점수_성장성", "growth"), ("수요성", "점수_수요성", "demand")]:
        bars += f'<div class="wl-sbar"><div class="wl-sbar-head"><span>{label}</span><b>{row[col]:.1f}</b><em>{int(rank_row[col])}위</em></div><div class="wl-sbar-track"><i class="{cls}" style="width:{row[col]}%"></i></div></div>'
    story = "".join(f"<li>{line}</li>" for line in story_lines(row))
    html(f'<div class="wl-panel wl-scorepanel"><div class="wl-sum-total"><span class="wl-sum-total-label">종합점수</span><span class="wl-sum-total-value">{row["종합점수"]:.1f}</span><span class="wl-sum-total-rank">전국 {int(rank_row["종합점수"])}위 / {N}</span></div><div class="wl-sbars">{bars}</div><ul class="wl-story">{story}</ul></div>')

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
        layer = load_geo_sido().copy(); layer["값"] = layer["sidonm"].map(lookup); vals = layer["값"].dropna()
        vmin, vmax = (vals.min(), vals.max()) if len(vals) else (0, 1)
        folium.GeoJson(layer, style_function=lambda f: {"fillColor": _shade(f["properties"]["값"],vmin,vmax),"color":"#FFFFFF","weight":1.2,"fillOpacity":.9}, highlight_function=lambda f:{"weight":2.5,"color":"#14293D","fillOpacity":1}, tooltip=folium.GeoJsonTooltip(fields=["sidonm","값"],aliases=["",f"{metric_label} "],sticky=True,style=TOOLTIP_STYLE)).add_to(m); return m
    geo = load_geo_sgg(); layer = geo[geo["sidonm"].apply(lambda n:is_matching_sido(n,sido_name))][["sidonm","sggnm","geometry"]].copy()
    layer["표시명"] = layer["sggnm"].apply(lambda n:sgg_display_name(sido_name,n)); name2val=dict(zip(scoped["시군구"],scoped[metric_col])); vals=[v for v in name2val.values() if pd.notna(v)]; vmin,vmax=(min(vals),max(vals)) if vals else (0,1); layer["값"]=layer["표시명"].map(name2val)
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

col_left,col_right=st.columns([6,4],gap="medium")
with col_left:
    if sel_row is not None:
        detail,score=load_selected_detail(sel_row["region_code"])
        if detail["region"] is None or score is None: st.warning("선택 지역의 상세 데이터를 찾을 수 없습니다.")
        render_head(sel_row,int(sel_rank["종합점수"])); render_evidence(sel_row,sel_rank)
    else:
        out=st_folium(build_map(sido),height=560,use_container_width=True,returned_objects=["last_active_drawing"]); handle_click(out,sido)
        swatches="".join(f'<i style="background:{c}"></i>' for c in SHADES); html(f'<div class="wl-legend"><span>{metric_label}</span><span class="wl-legend-min">낮음</span>{swatches}<span class="wl-legend-max">높음</span></div>')
with col_right:
    if sel_row is not None: render_score(sel_row,sel_rank)
    elif scoped.empty: html('<div class="wl-panel wl-panel-empty">표시할 지역 데이터가 없습니다</div>')
    else:
        rows="".join(f'<div class="wl-rank-row"><span class="wl-rank-no">{i}</span><span class="wl-rank-name">{r["시도"]} {r["시군구"]}</span><b class="wl-rank-val">{metric_fmt.format(r[metric_col])}</b></div>' for i,(_,r) in enumerate(scoped.head(14).iterrows(),1)); html(f'<div class="wl-panel"><div class="wl-rank-head">{scope_txt} &#183; {metric_label} 순</div><div class="wl-rank">{rows}</div></div>')

mode = st.radio(
    "보기", ["이 지역만", "전국 평균과 비교"],
    horizontal=True, label_visibility="collapsed",
)

if sel_row is None:
    html('<div class="wl-chart-ph">지역을 선택하면 그래프가 표시됩니다<span>추이와 경합도 산점도</span></div>')
elif mode == "전국 평균과 비교":
    html('<div class="wl-chart-ph">비교 모드는 준비 중입니다<span>전국 평균선을 겹쳐 그릴 예정</span></div>')
else:
    g1, g2 = st.columns(2, gap="medium")
    with g1:
        html(f'<div class="wl-chart-title">{sgg} &#183; 37개월 추이</div>')
        trend = load_trend(sel_row["region_code"])
        vehicles = pd.DataFrame(trend["vehicle_history"]).rename(
            columns={"date": "연월", "vehicle_count": "차량등록대수"}
        )
        population = pd.DataFrame(trend["population_history"]).rename(
            columns={"date": "연월", "population": "인구수"}
        )
        if vehicles.empty and population.empty:
            html('<div class="wl-chart-ph">추이 데이터가 없습니다</div>')
        else:
            trend_df = pd.merge(vehicles, population, on="연월", how="outer").sort_values("연월")
            charts.trend_chart(
                trend_df,
                series={"차량등록대수": "차량 등록", "인구수": "인구"},
                key="region_trend",
            )
    with g2:
        html('<div class="wl-chart-title">경합도 · 전국 249개 중 위치</div>')
        html('<div class="wl-chart-ph">경합도 산점도는 표시하지 않습니다<span>화물차 밀도 계산에 필요한 면적 데이터가 없습니다</span></div>')
