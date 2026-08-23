from pathlib import Path

import pandas as pd
import streamlit as st
import admdongkor as adk
import folium
from streamlit_folium import st_folium
from ui.layout import setup, html
setup(page="explore", active="데이터 조회")


GEO = Path(__file__).resolve().parent.parent / "assets" / "geo"
 
 


# 지도를 칠할 지표 — (컬럼, 집계방식, 표시형식)
METRICS = {
    "종합점수": ("종합점수", "mean", "{:.1f}"),
    "산업성": ("점수_산업성", "mean", "{:.1f}"),
    "성장성": ("점수_성장성", "mean", "{:.1f}"),
    "화물차": ("화물차", "sum", "{:,.0f}대"),
}
SHADES = ["#E6F1FB", "#B5D4F4", "#85B7EB", "#378ADD", "#185FA5"]
# 2026.07 개편이 지도 데이터에 반영됐는지에 따라 시도명이 다를 수 있다
SIDO_ALIAS = {"전남광주통합특별시": ["전남광주통합특별시", "광주광역시", "전라남도"]}

# @st.cache_data
# def load():
#     return pd.read_csv(
#         Path(__file__).resolve().parent / "assets" / "mock_regions.csv",
#         encoding="utf-8-sig",
#     ) 


@st.cache_data
def load_mock():
    return pd.read_csv(GEO / "mock_regions.csv", encoding="utf-8-sig")
 
 
@st.cache_data
def load_geo():
    g = adk.get("20260201", level="sido").to_crs(epsg=4326)
    # 시도 단위라 단순화해도 형태가 유지된다. 렌더가 훨씬 빨라진다.
    g["geometry"] = g["geometry"].simplify(0.002)
    return g
 
 
df = load_mock()
geo = load_geo()
 
if "sel" not in st.session_state:
    st.session_state.sel = None       # 선택한 시도명

html('<div class="wl-searchbar">')

c1, c2, c3, c4, c5 = st.columns([1.5, 1.8, 2.0, 2.4, 1.4])
 
with c1:
    sido = st.selectbox(
        "시도", ["전체"] + sorted(df["시도"].unique()),
        label_visibility="collapsed",
    )
 
with c2:
    sgg_opts = ["전체"] if sido == "전체" else \
        ["전체"] + sorted(df[df["시도"] == sido]["시군구"])
    sgg = st.selectbox(
        "시군구", sgg_opts, disabled=(sido == "전체"),
        label_visibility="collapsed",
    )
 
with c3:
    picked = st.multiselect(
        "유형", ["미개척", "성장 중", "포화", "정체"],
        placeholder="유형 전체", label_visibility="collapsed",
    )
 
with c4:
    lo, hi = int(df["배후인구"].min()), int(df["배후인구"].max())
    pop = st.slider(
        "배후 인구", lo, hi, (lo, hi), step=10_000,
        label_visibility="collapsed",
    )
 
with c5:
    sort_by = st.selectbox(
        "정렬", list(METRICS), label_visibility="collapsed",
    )
 

# ══ 조건 적용 ═════════════════════════════════════
view = df.copy()
if sido != "전체":
    view = view[view["시도"] == sido]
if sgg != "전체":
    view = view[view["시군구"] == sgg]
if picked:
    view = view[view["유형"].isin(picked)]
view = view[(view["배후인구"] >= pop[0]) & (view["배후인구"] <= pop[1])]
 
col, how, fmt = METRICS[sort_by]
view = view.sort_values(col, ascending=False)
 
html(f'<div class="wl-meta"><b>{len(view)}개</b> / {len(df)}개 지역 '
     f'&#183; 지도는 <b>{sort_by}</b> 기준</div>')
 
 
# ══ 지도(6) + 패널(4) ═════════════════════════════
col_map, col_side = st.columns([6, 4], gap="medium")
 
with col_map:
    agg = view.groupby("시도", as_index=False).agg(값=(col, how))
    name2val = dict(zip(agg["시도"], agg["값"]))
 
    def lookup(nm):
        if nm in name2val:
            return name2val[nm]
        for ours, theirs in SIDO_ALIAS.items():
            if nm in theirs and ours in name2val:
                return name2val[ours]
        return None
 
    geo = geo.copy()
    geo["값"] = geo["sidonm"].map(lookup)
 
    vals = geo["값"].dropna()
    vmin, vmax = (vals.min(), vals.max()) if len(vals) else (0, 1)
 
    def color_of(v):
        if pd.isna(v):
            return "#EFF2F5"          # 조건에서 빠진 시도
        i = int((v - vmin) / (vmax - vmin + 1e-9) * len(SHADES))
        return SHADES[min(i, len(SHADES) - 1)]
 
    m = folium.Map(
        location=[36.3, 127.8], zoom_start=7,
        tiles=None, zoom_control=True,
        scrollWheelZoom=True, dragging=True,
    )
 
    folium.GeoJson(
        geo,
        style_function=lambda f: {
            "fillColor": color_of(f["properties"]["값"]),
            "color": "#FFFFFF",
            "weight": 1.2,
            "fillOpacity": 0.9,
        },
        highlight_function=lambda f: {
            "weight": 2.5, "color": "#14293D", "fillOpacity": 1.0,
        },
        tooltip=folium.GeoJsonTooltip(
            fields=["sidonm", "값"],
            aliases=["", f"{sort_by} "],
            sticky=True,
            style=("background:#fff; border:1px solid #DDE4EB; border-radius:6px;"
                   "padding:8px 10px; font-family:sans-serif; font-size:12.5px;"),
        ),
    ).add_to(m)
 
    out = st_folium(m, height=560, use_container_width=True,
                    returned_objects=["last_active_drawing"])
 
    if out and out.get("last_active_drawing"):
        st.session_state.sel = out["last_active_drawing"]["properties"]["sidonm"]
 
    # 범례
    swatches = "".join(f'<i style="background:{c}"></i>' for c in SHADES)
    html(f"""
    <div class="wl-legend">
    <span>{sort_by}</span>
    <span class="wl-legend-min">낮음</span>
    {swatches}
    <span class="wl-legend-max">높음</span>
    </div>
    """)
 
 
with col_side:
    sel = st.session_state.sel
 
    if sel is None:
        html("""
        <div class="wl-panel">
        <div class="wl-panel-ph">
        지도에서 시도를 클릭하세요
        <span>전국 요약이 들어갈 자리</span>
        </div>
        </div>
        """)
    else:
        html(f"""
        <div class="wl-panel">
        <div class="wl-panel-sido">선택</div>
        <div class="wl-panel-name">{sel}</div>
        <div class="wl-panel-ph">
        지역 상세가 들어갈 자리
        <span>세 축 점수 · 근거 문장 · 지표 요약</span>
        </div>
        </div>
        """)
 
 
# ══ 그래프 자리 ═══════════════════════════════════
mode = st.radio(
    "그래프", ["추이", "레이더", "구성비", "순위"],
    horizontal=True, label_visibility="collapsed",
)
 
html(f"""
<div class="wl-chart-ph">
{mode} 차트가 들어갈 자리
<span>{st.session_state.sel or "전국"} 기준</span>
</div>
""")


html("</div>")