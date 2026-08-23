"""여러 페이지에서 재사용할 그래프 컴포넌트 모음.

입력은 dict/DataFrame, 반환 없이 st.plotly_chart 로 바로 렌더링한다.
전부 plotly 하나로 통일해서 라이브러리를 여러 개 설치하지 않아도 되게 했다.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ── 공통 색 ─────────────────────────────────────────
LINE = "#378ADD"
FILL = "rgba(55, 138, 221, 0.22)"
INK = "#14293D"
MUTE = "#8B97A4"
GRID = "#EDF1F5"
POINT = "#C9D6E2"        # 배경 점 (나머지 지역)
HIGHLIGHT = "#FF7A45"    # 선택한 지역
GREEN = "#3B9E6B"
AMBER = "#F2B705"
RED = "#E2574C"

RADAR_AXES = ["종합점수", "산업성", "성장성", "수요성"]

# 차량 구성비에 쓰는 색 — 화물차만 진하게 해서 눈이 먼저 가게 한다
COMPO_COLORS = {
    "화물차": LINE,
    "승용차": "#B9CEE4",
    "승합차": "#D6E3EF",
    "특수차": "#EDF2F7",
}

# 경합도 4분면 라벨 — LQ 1.0 과 전국 평균 증가율로 자른다
QUADRANT_LABEL = {
    (False, True): "미개척",
    (True, True): "성장 중",
    (True, False): "포화",
    (False, False): "정체",
}


def _base(fig, height=320, legend=False):
    """모든 차트에 공통으로 먹이는 레이아웃."""
    fig.update_layout(
        height=height,
        margin=dict(l=30, r=24, t=20, b=28),
        font=dict(family="IBM Plex Sans KR, sans-serif", size=12, color=INK),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0,
                    xanchor="right", x=1, font=dict(size=11)),
        hoverlabel=dict(font_family="IBM Plex Sans KR, sans-serif"),
    )
    return fig


def _empty(msg: str, height: int = 320) -> None:
    """데이터가 없을 때 자리를 유지하기 위한 빈 박스.

    st.warning 을 쓰면 높이가 달라서 3분할 레이아웃이 흔들린다.
    """
    st.markdown(
        f"""<div style="height:{height}px;display:flex;align-items:center;
        justify-content:center;border:1px dashed #E3E8EE;border-radius:12px;
        color:#A5AFBA;font-size:13px">{msg}</div>""",
        unsafe_allow_html=True,
    )


# ── 지표 카드 ───────────────────────────────────────
def metric_row(metrics: list[dict]) -> None:
    """상단 지표 카드 한 줄.

    metrics 예시:
        [{"label": "종합점수", "value": "73.6", "delta": "+12.4"},
         {"label": "인구", "value": "30.2만", "delta": "-1.8만"}]

    delta 는 문자열 그대로 넘긴다. 부호로 색이 자동으로 갈린다.
    비교 모드가 아니면 delta 키를 빼면 된다.
    """
    if not metrics:
        return
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(
                label=m.get("label", ""),
                value=m.get("value", "-"),
                delta=m.get("delta"),
                help=m.get("help"),
            )


# ── 레이더 ──────────────────────────────────────────
def radar_chart(scores: dict[str, float], avg: dict[str, float] | None = None,
                key: str | None = None) -> None:
    """네 개 점수를 레이더 차트로 그린다.

    scores 예시: {"종합점수": 82.4, "산업성": 78.1, "성장성": 85.0, "수요성": 84.2}
    avg 를 넘기면 전국 평균을 점선으로 뒤에 깔아 비교한다.
    """
    if not scores:
        _empty("지역을 선택하면 표시됩니다")
        return

    missing = [a for a in RADAR_AXES if a not in scores]
    if missing:
        st.warning(f"레이더 차트에 필요한 값이 없습니다: {', '.join(missing)}")
        return

    axes = RADAR_AXES + [RADAR_AXES[0]]
    fig = go.Figure()

    # 전국 평균을 먼저 그려야 선택 지역 도형이 위로 올라온다
    if avg:
        avg_vals = [avg.get(a, 0) for a in RADAR_AXES]
        avg_vals.append(avg_vals[0])
        fig.add_trace(go.Scatterpolar(
            r=avg_vals, theta=axes, fill=None, name="전국 평균",
            line=dict(color=MUTE, width=1.5, dash="dot"),
            hovertemplate="전국 평균 %{theta}: %{r:.1f}<extra></extra>",
        ))

    values = [scores[a] for a in RADAR_AXES]
    values.append(values[0])          # 도형을 닫기 위해 첫 값을 한 번 더
    fig.add_trace(go.Scatterpolar(
        r=values, theta=axes, fill="toself", name="선택 지역",
        fillcolor=FILL, line=dict(color=LINE, width=2),
        hovertemplate="%{theta}: %{r:.1f}<extra></extra>",
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
            angularaxis=dict(tickfont=dict(size=12)),
        ),
    )
    _base(fig, legend=avg is not None)
    st.plotly_chart(fig, use_container_width=True, key=key)


# ── 차량 구성비 ─────────────────────────────────────
def composition_bar(shares: dict[str, float], avg: dict[str, float] | None = None,
                    label: str = "선택 지역", key: str | None = None) -> None:
    """차량 구성비 가로 누적 막대.

    shares 예시: {"승용차": 74.1, "화물차": 18.2, "승합차": 5.4, "특수차": 2.3}
    합이 100 이 아니어도 알아서 비율로 환산한다.
    avg 를 넘기면 전국 평균 막대를 아래에 한 줄 더 그린다.

    파이 대신 이걸 쓰는 이유는 두 막대를 위아래로 붙였을 때
    어느 구간이 더 튀어나왔는지가 길이로 바로 읽히기 때문이다.
    """
    if not shares:
        _empty("지역을 선택하면 표시됩니다")
        return

    rows = [(label, shares)]
    if avg:
        rows.append(("전국 평균", avg))

    cats = [c for c in COMPO_COLORS if c in shares]
    cats += [c for c in shares if c not in COMPO_COLORS]

    fig = go.Figure()
    for cat in cats:
        xs, ys, texts = [], [], []
        for name, data in rows:
            total = sum(data.values()) or 1
            pct = data.get(cat, 0) / total * 100
            xs.append(pct)
            ys.append(name)
            texts.append(f"{pct:.1f}%" if pct >= 7 else "")
        fig.add_trace(go.Bar(
            x=xs, y=ys, name=cat, orientation="h",
            marker=dict(color=COMPO_COLORS.get(cat, POINT),
                        line=dict(color="#fff", width=2)),
            text=texts, textposition="inside",
            insidetextfont=dict(size=11, color="#fff"),
            hovertemplate="%{y} · " + cat + " %{x:.1f}%<extra></extra>",
        ))

    fig.update_xaxes(range=[0, 100], ticksuffix="%", gridcolor=GRID,
                     zeroline=False, tickfont=dict(size=10))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=12))
    _base(fig, legend=True)
    fig.update_layout(legend=dict(orientation="h", yanchor="top", y=-0.15,
                                  xanchor="center", x=0.5))
    st.plotly_chart(fig, use_container_width=True, key=key)


# ── 연도별 증감 ─────────────────────────────────────
def yoy_chart(df: pd.DataFrame, year_col: str = "연도", value_col: str = "화물차수",
              key: str | None = None) -> None:
    """연도별 세로 막대 + 전년 대비 증감률 라벨.

    df 는 연도별로 이미 집계된 형태를 받는다.
        연도    화물차수
        2024    12400
        2025    13180
        2026    13920

    2026 년은 7월까지밖에 없으므로 호출하기 전에 세 해 모두
    1~7월 기준으로 잘라서 넘겨야 막대 높이 비교가 성립한다.
    증가면 파랑, 감소면 빨강으로 칠해 감소 지역이 바로 걸러지게 했다.
    """
    if df is None or df.empty or value_col not in df:
        _empty("지역을 선택하면 표시됩니다")
        return

    d = df.sort_values(year_col).reset_index(drop=True)
    vals = d[value_col].astype(float)
    deltas = vals.pct_change() * 100

    colors, texts = [], []
    for i, dv in enumerate(deltas):
        if pd.isna(dv):
            colors.append(POINT)
            texts.append("기준")
        else:
            colors.append(LINE if dv >= 0 else RED)
            texts.append(f"{dv:+.1f}%")

    fig = go.Figure(go.Bar(
        x=d[year_col].astype(str), y=vals,
        marker=dict(color=colors),
        text=texts, textposition="outside",
        textfont=dict(size=11, color=MUTE),
        width=0.5,
        hovertemplate="%{x}년<br>%{y:,.0f}대<extra></extra>",
    ))

    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=11))
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(size=10),
                     rangemode="tozero")
    fig.update_layout(yaxis=dict(range=[0, float(vals.max()) * 1.18]))
    _base(fig)
    st.plotly_chart(fig, use_container_width=True, key=key)


# ── 4분면 산점도 ────────────────────────────────────
def quadrant_chart(df: pd.DataFrame, selected: str | None = None,
                   x_col: str = "LQ", y_col: str = "화물차_증가율",
                   name_col: str = "지역", key: str | None = None) -> None:
    """경합도 4분면 산점도.

    전체 지역을 점으로 뿌리고 선택한 지역만 크게 표시한다.
    가로 기준선은 LQ 1.0, 세로 기준선은 전국 평균 증가율이다.
    유형 라벨(미개척·성장 중·포화·정체)이 위치로 이해되게 하는 것이 목적.

    상세보기 3분할에서는 빠졌지만 유망지역 추천 쪽에서 쓸 수 있어 남겨둔다.
    """
    if df.empty or x_col not in df or y_col not in df:
        st.warning("산점도에 필요한 컬럼이 없습니다.")
        return

    x_line = 1.0
    y_line = float(df[y_col].mean())

    fig = go.Figure()

    # 배경 : 나머지 지역
    fig.add_trace(go.Scatter(
        x=df[x_col], y=df[y_col], mode="markers",
        marker=dict(size=7, color=POINT, line=dict(width=0)),
        text=df[name_col],
        hovertemplate="%{text}<br>LQ %{x:.2f} · 증가율 %{y:+.1f}%<extra></extra>",
        name="전체",
    ))

    # 기준선
    fig.add_vline(x=x_line, line=dict(color=MUTE, width=1, dash="dash"))
    fig.add_hline(y=y_line, line=dict(color=MUTE, width=1, dash="dash"))

    # 4분면 라벨
    xr = [df[x_col].min(), df[x_col].max()]
    yr = [df[y_col].min(), df[y_col].max()]
    pad_x = (xr[1] - xr[0]) * 0.04
    pad_y = (yr[1] - yr[0]) * 0.06
    for (hi_x, hi_y), label in QUADRANT_LABEL.items():
        fig.add_annotation(
            x=(xr[1] - pad_x) if hi_x else (xr[0] + pad_x),
            y=(yr[1] - pad_y) if hi_y else (yr[0] + pad_y),
            text=label, showarrow=False,
            font=dict(size=11, color=MUTE),
            xanchor="right" if hi_x else "left",
            yanchor="top" if hi_y else "bottom",
        )

    # 선택한 지역
    if selected is not None:
        hit = df[df[name_col] == selected]
        if not hit.empty:
            fig.add_trace(go.Scatter(
                x=hit[x_col], y=hit[y_col], mode="markers+text",
                marker=dict(size=16, color=HIGHLIGHT,
                            line=dict(width=2, color="#fff")),
                text=hit[name_col], textposition="top center",
                textfont=dict(size=12, color=INK),
                hovertemplate="%{text}<br>LQ %{x:.2f} · 증가율 %{y:+.1f}%<extra></extra>",
                name="선택",
            ))

    fig.update_xaxes(title_text="입지계수 LQ", gridcolor=GRID,
                     zeroline=False, title_font=dict(size=11, color=MUTE))
    fig.update_yaxes(title_text="화물차 증가율 (%)", gridcolor=GRID,
                     zeroline=False, title_font=dict(size=11, color=MUTE))
    _base(fig)
    st.plotly_chart(fig, use_container_width=True, key=key)


# ── 추이 ────────────────────────────────────────────
def trend_chart(df: pd.DataFrame, x_col: str = "연월",
                series: dict[str, str] | None = None,
                secondary: bool = False,
                key: str | None = None) -> None:
    """37개월 추이 꺾은선.

    series 예시: {"인구천명당_화물차": "선택 지역", "전국평균": "전국 평균"}

    기본값(secondary=False)은 두 계열을 같은 y축에 그린다.
    단위가 같은 지표끼리 비교할 때 쓴다. 인구 1천명당 화물차처럼
    이미 정규화된 값을 넣어야 지역 규모에 휘둘리지 않는다.

    단위가 다른 두 값을 굳이 겹쳐 봐야 할 때만 secondary=True 를 준다.
    이 경우 두 선의 간격이나 교차점에는 아무 의미가 없다는 점에 주의.
    """
    if df is None or df.empty:
        _empty("지역을 선택하면 표시됩니다", height=300)
        return

    series = series or {"화물차수": "화물차"}
    cols = [c for c in series if c in df.columns]
    if not cols:
        st.warning("추이 차트에 필요한 컬럼이 없습니다.")
        return

    x = df[x_col].astype(str)
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=x, y=df[cols[0]], mode="lines", name=series[cols[0]],
        line=dict(color=LINE, width=2.4),
        hovertemplate="%{x}<br>%{y:,.1f}<extra></extra>",
    ))

    if len(cols) > 1:
        trace_kw = {"yaxis": "y2"} if secondary else {}
        fig.add_trace(go.Scatter(
            x=x, y=df[cols[1]], mode="lines", name=series[cols[1]],
            line=dict(color=MUTE, width=1.6, dash="dot"),
            hovertemplate="%{x}<br>%{y:,.1f}<extra></extra>",
            **trace_kw,
        ))
        if secondary:
            fig.update_layout(
                yaxis2=dict(overlaying="y", side="right",
                            gridcolor="rgba(0,0,0,0)",
                            tickfont=dict(size=10, color=MUTE)),
            )

    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10),
                     nticks=8)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(size=10))
    _base(fig, height=300, legend=len(cols) > 1)
    st.plotly_chart(fig, use_container_width=True, key=key)


def dist_hist(data: pd.DataFrame, col: str = "화물차비율",
              selected_value: float | None = None,
              bins: int = 12, fmt: str = "{:.1f}",
              key: str | None = None) -> None:
    """전국 분포 히스토그램. 선택 지역이 속한 구간만 색을 바꾼다.

    점 249개를 뿌리는 대신 구간으로 묶는다. 분포의 모양(한쪽으로
    쏠렸는지, 두 덩어리인지)과 내 위치를 동시에 보여주는 것이 목적.
    """
    if data is None or data.empty or col not in data:
        _empty("표시할 데이터가 없습니다")
        return

    s = data[col].dropna().astype(float)
    if s.empty:
        _empty("표시할 데이터가 없습니다")
        return

    cut = pd.cut(s, bins=bins)
    counts = cut.value_counts().sort_index()
    edges = [iv.left for iv in counts.index] + [counts.index[-1].right]
    centers = [(counts.index[i].left + counts.index[i].right) / 2
               for i in range(len(counts))]

    hit = -1
    if selected_value is not None:
        for i, iv in enumerate(counts.index):
            if iv.left < selected_value <= iv.right:
                hit = i
                break

    fig = go.Figure(go.Bar(
        x=centers, y=counts.values,
        marker=dict(color=[HIGHLIGHT if i == hit else POINT
                           for i in range(len(counts))]),
        width=(edges[1] - edges[0]) * 0.88,
        hovertemplate=fmt + " 부근 · %{y}개 지역<extra></extra>",
    ))

    if selected_value is not None and hit >= 0:
        fig.add_vline(x=selected_value,
                      line=dict(color=INK, width=1.5, dash="dot"))

    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10),
                     zeroline=False)
    fig.update_yaxes(title_text="지역 수", gridcolor=GRID, zeroline=False,
                     tickfont=dict(size=10),
                     title_font=dict(size=11, color=MUTE))
    _base(fig)
    st.plotly_chart(fig, use_container_width=True, key=key)



TYPE_COLORS = {
    "성장 중": LINE,
    "미개척": GREEN,
    "포화": AMBER,
    "정체": POINT,
}


def type_bar(counts: dict[str, int], selected: str | None = None,
             key: str | None = None) -> None:
    """유형별 지역 수 가로 막대.
 
    counts 예시: {"미개척": 42, "성장 중": 31, "포화": 88, "정체": 88}
 
    4분면 산점도의 분류 로직을 그대로 쓰되 점 249개를 뿌리는 대신
    네 개로 세어서 보여준다. 전국 구도가 한 줄로 읽히는 것이 목적이다.
 
    selected 를 주면 그 유형만 주황으로 칠한다. 시군구를 골랐을 때
    소속 시도 안에서 이 지역이 어느 무리에 속하는지 보여준다.
    """
    if not counts:
        _empty("표시할 지역이 없습니다")
        return
 
    items = sorted(counts.items(), key=lambda kv: kv[1])
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    total = sum(values) or 1
 
    if selected is not None:
        colors = [HIGHLIGHT if l == selected else POINT for l in labels]
    else:
        colors = [TYPE_COLORS.get(l, POINT) for l in labels]
 
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(color=colors),
        text=[f"{v}개 · {v/total*100:.0f}%" for v in values],
        textposition="outside",
        textfont=dict(size=11, color=MUTE),
        width=0.55,
        hovertemplate="%{y} %{x}개<extra></extra>",
    ))
 
    fig.update_xaxes(gridcolor=GRID, zeroline=False, tickfont=dict(size=10),
                     range=[0, max(values) * 1.28])
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=12))
    _base(fig)
    st.plotly_chart(fig, use_container_width=True, key=key)