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

RADAR_AXES = ["종합점수", "산업성", "성장성", "수요성"]

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


def radar_chart(scores: dict[str, float], key: str | None = None) -> None:
    """네 개 점수를 레이더 차트로 그린다.

    scores 예시: {"종합점수": 82.4, "산업성": 78.1, "성장성": 85.0, "수요성": 84.2}
    """
    missing = [a for a in RADAR_AXES if a not in scores]
    if missing:
        st.warning(f"레이더 차트에 필요한 값이 없습니다: {', '.join(missing)}")
        return

    values = [scores[a] for a in RADAR_AXES]
    values.append(values[0])          # 도형을 닫기 위해 첫 값을 한 번 더
    axes = RADAR_AXES + [RADAR_AXES[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values, theta=axes, fill="toself",
        fillcolor=FILL, line=dict(color=LINE, width=2),
        hovertemplate="%{theta}: %{r:.1f}<extra></extra>",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(size=10)),
            angularaxis=dict(tickfont=dict(size=12)),
        ),
    )
    _base(fig)
    st.plotly_chart(fig, use_container_width=True, key=key)


def quadrant_chart(df: pd.DataFrame, selected: str | None = None,
                   x_col: str = "LQ", y_col: str = "화물차_증가율",
                   name_col: str = "지역", key: str | None = None) -> None:
    """경합도 4분면 산점도.

    전체 지역을 점으로 뿌리고 선택한 지역만 크게 표시한다.
    가로 기준선은 LQ 1.0, 세로 기준선은 전국 평균 증가율이다.
    유형 라벨(미개척·성장 중·포화·정체)이 위치로 이해되게 하는 것이 목적.
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


def trend_chart(df: pd.DataFrame, x_col: str = "연월",
                series: dict[str, str] | None = None,
                key: str | None = None) -> None:
    """37개월 추이. 화물차와 인구를 겹쳐 그려 디커플링을 보이게 한다.

    series 예시: {"화물차수": "화물차", "인구수": "인구"}
    값이 두 개면 두 번째를 보조 y축에 놓는다. 단위가 달라도
    같은 그림에서 방향을 비교할 수 있다.
    """
    if df.empty:
        st.warning("추이 데이터가 없습니다.")
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
        hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>",
    ))

    if len(cols) > 1:
        fig.add_trace(go.Scatter(
            x=x, y=df[cols[1]], mode="lines", name=series[cols[1]],
            line=dict(color=MUTE, width=1.6, dash="dot"),
            yaxis="y2",
            hovertemplate="%{x}<br>%{y:,.0f}<extra></extra>",
        ))
        fig.update_layout(
            yaxis2=dict(overlaying="y", side="right",
                        gridcolor="rgba(0,0,0,0)",
                        tickfont=dict(size=10, color=MUTE)),
        )

    fig.update_xaxes(gridcolor="rgba(0,0,0,0)", tickfont=dict(size=10),
                     nticks=8)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, tickfont=dict(size=10))
    _base(fig, legend=len(cols) > 1)
    st.plotly_chart(fig, use_container_width=True, key=key)