"""데이터 조회 — 기존 지도·상세 레이아웃에 MySQL backend 데이터를 연결한다."""
import admdongkor as adk
import folium
import pandas as pd
import streamlit as st
from pymysql import MySQLError
from streamlit_folium import st_folium

from ui import charts
from ui.backend import get_db
from ui.layout import html, load_logo_b64, setup
from web.backend import (get_freight_per_population_trend,
    get_logistics_ranking, get_logistics_score,
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

loading_ph = st.empty()
with loading_ph.container():
    html(f"""
    <div class="wl-loading">
      <img src="data:image/png;base64,{load_logo_b64()}" class="wl-loading-logo" alt=""/>
      <p class="wl-loading-title">전국 249개 지역을 계산하고 있습니다</p>
      <p class="wl-loading-sub">화물차 등록 현황과 인구 통계를 결합해<br>산업성 · 성장성 · 수요성 지수를 산출합니다</p>
    </div>
    """)

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

loading_ph.empty()

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
    picked = st.multiselect(
        "유형", ["미개척", "성장 중", "포화", "정체"],
        placeholder="유형 전체", label_visibility="collapsed"
    )
with c4:
    # 원본의 slider 위치를 유지하고 실제 DB 자체 인구로 필터링한다.
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

TYPES = ["미개척", "성장 중", "포화", "정체"]


def ph(title, sub, height=320):
    html(f'<div class="wl-chart-ph" style="height:{height}px">{title}<span>{sub}</span></div>')


level = "시군구" if sel_row is not None else ("시도" if sido != "전체" else "전국")
scope_name = sgg if level == "시군구" else (sido if level == "시도" else "전국")
scope_df = passed[passed["시도"] == sido] if level == "시군구" else scoped
if scope_df.empty:
    scope_df = df if level == "전국" else df[df["시도"] == sido]

mode = st.radio(
    "보기", ["이대로 보기", "전국 평균과 비교"], horizontal=True,
    label_visibility="collapsed", disabled=(level == "전국"),
)
compare = mode == "전국 평균과 비교" and level != "전국"
html(f'<div class="wl-chart-title">{scope_name} &#183; 상세 분석</div>')


def build_metrics():
    if level == "시군구":
        row = sel_row
        per_k = row["화물차"] / row["인구수"] * 1000 if row["인구수"] else 0
        nat_per_k = (df["화물차"].sum() / df["인구수"].sum() * 1000)

        def delta(col):
            return f'{row[col] - df[col].mean():+.1f}' if compare else None

        return [
            {"label": "종합점수", "value": f'{row["종합점수"]:.1f}',
             "delta": delta("종합점수"), "help": f'전국 {int(sel_rank["종합점수"])}위 / {N}'},
            {"label": "화물차 비율", "value": f'{row["화물차비율"]:.1f}%',
             "delta": delta("화물차비율")},
            {"label": "인구 1천명당 화물차", "value": f"{per_k:,.1f}대",
             "delta": f"{per_k - nat_per_k:+.1f}" if compare else None},
            {"label": "자체 인구", "value": f'{row["인구수"] / 10000:,.1f}만'},
        ]

    def avg_delta(col):
        return f'{scope_df[col].mean() - df[col].mean():+.1f}' if compare else None

    return [
        {"label": "지역 수", "value": f"{len(scope_df):,}개"},
        {"label": "평균 종합점수", "value": f'{scope_df["종합점수"].mean():.1f}',
         "delta": avg_delta("종합점수")},
        {"label": "평균 화물차 비율", "value": f'{scope_df["화물차비율"].mean():.1f}%',
         "delta": avg_delta("화물차비율")},
        {"label": "화물차 합계", "value": f'{scope_df["화물차"].sum():,.0f}대'},
    ]


charts.metric_row(build_metrics())

detail = None
if sel_row is not None:
    detail, _ = load_selected_detail(sel_row["region_code"])

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
                charts.composition_bar(shares, avg=avg if compare else None, label=sgg, key="compo")
        else:
            freight = scope_df["화물차"].sum() / scope_df["차량총"].sum() * 100
            national_freight = df["화물차"].sum() / df["차량총"].sum() * 100
            charts.composition_bar(
                {"화물": freight, "그 외 차량": 100 - freight},
                avg={"화물": national_freight, "그 외 차량": 100 - national_freight} if compare else None,
                label=f"{scope_name} 합계", key="compo",
            )

with a2:
    with st.container(border=True):
        sub = "유형별 지역 수" if level != "시군구" else f"{sido} 유형 분포"
        html(f'<div class="wl-chart-sub">{sub}</div>')
        counts = scope_df["유형"].value_counts()
        charts.type_bar(
            {name: int(counts.get(name, 0)) for name in TYPES},
            selected=sel_row["유형"] if level == "시군구" else None,
            key="typebar",
        )

b1, b2 = st.columns(2, gap="medium")
freight_trend = load_freight_trend(
    code=sel_row["region_code"] if sel_row is not None else None,
    province=sido if level == "시도" else None,
)
with b1:
    with st.container(border=True):
        html('<div class="wl-chart-sub">화물차 전년 대비 증감률</div>')
        if freight_trend.empty:
            ph("연도별 증감", "월별 화물차 데이터 없음")
        else:
            yearly = freight_trend.copy()
            yearly["연도"] = yearly["연월"].str[:4]
            yearly["월"] = yearly["연월"].str[5:7].astype(int)
            cutoff = int(TARGET_MONTH[-2:])
            # 등록대수는 흐름량이 아닌 월말 재고이므로 합산하지 않고
            # 각 연도의 동일 기준월(7월) 스냅샷끼리 비교한다.
            yearly = yearly[yearly["월"] == cutoff][["연도", "화물차수"]]
            charts.yoy_chart(yearly, key="yoy")
with b2:
    with st.container(border=True):
        html('<div class="wl-chart-sub">인구 1천명당 화물차 · 37개월</div>')
        series = {"인구천명당_화물차": scope_name}
        if compare:
            series["전국평균"] = "전국 평균"
        charts.trend_chart(
            freight_trend, x_col="연월", series=series, key="trend",
            data_palette=True,
        )
