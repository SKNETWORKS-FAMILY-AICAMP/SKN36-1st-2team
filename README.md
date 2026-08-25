---
marp: true
theme: default
paginate: true
size: 16:9
style: |
  /* ══════════════════════════════════════════
     WAYLOGI 발표자료 — SKN 36기 2팀
     색상 대비를 모두 4.5 이상으로 검증했습니다
     ══════════════════════════════════════════ */

  section {
    font-family: "맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
    background: #F7FAFC;
    color: #24404F;
    font-size: 24px;
    line-height: 1.7;
    padding: 52px 64px;
  }

  h1 { font-size: 44px; color: #1B5878; letter-spacing: -0.03em; margin: 0; }
  h2 { font-size: 36px; color: #1B5878; letter-spacing: -0.03em; margin: 0 0 6px; }
  h3 { font-size: 25px; color: #1B5878; margin: 0 0 8px; }
  p  { margin: 0 0 14px; }
  strong { color: #1B5878; font-weight: 700; }

  /* 제목 아래 부제 */
  .sub { font-size: 19px; color: #5A6C77; margin: 0 0 30px; }

  /* 카드 묶음 */
  .cards { display: flex; gap: 20px; align-items: stretch; }
  .card {
    flex: 1; background: #EBF4FA; border: 1px solid #D3E5F0;
    border-radius: 14px; padding: 24px 26px;
  }
  .card .t { font-size: 22px; font-weight: 700; color: #1B5878; margin-bottom: 14px; }
  .card .d { font-size: 18px; color: #33454F; line-height: 1.85; }
  .card .n { font-size: 17px; font-weight: 700; color: #4A87AE; margin-bottom: 6px; }
  /* 큰 숫자 카드 — 내용을 세로 가운데로 모아 빈 아래쪽을 없앱니다 */
  .card.stat {
    display: flex; flex-direction: column; justify-content: center;
    text-align: center; gap: 6px;
  }
  .card.stat .big { font-size: 46px; font-weight: 800; color: #1B5878; line-height: 1.2; }
  .card.stat .cap { font-size: 16px; color: #4A87AE; }
  .card.stat .memo { font-size: 15px; color: #5A6C77; line-height: 1.7; }

  .card.warm { background: #FDF3E8; border-color: #EFD8B4; }
  .card.warm .t { color: #9A5F1C; }
  .card.warm .d { color: #6B4A22; }
  .card.warm .n { color: #B07A35; }

  /* 번호 붙은 세로 목록 */
  .rows { display: flex; flex-direction: column; gap: 14px; }
  .row {
    display: flex; align-items: flex-start; gap: 20px;
    background: #EBF4FA; border: 1px solid #D3E5F0;
    border-radius: 12px; padding: 20px 26px;
  }
  .row.warm { background: #FDF3E8; border-color: #EFD8B4; }
  .row .num {
    flex: none; width: 38px; height: 38px; border-radius: 19px;
    background: #4A87AE; color: #FFFFFF; font-size: 18px; font-weight: 700;
    display: flex; align-items: center; justify-content: center;
  }
  .row.warm .num { background: #C08A3E; }
  .row .body .t { font-size: 21px; font-weight: 700; color: #1B5878; }
  .row .body .d { font-size: 18px; color: #33454F; margin-top: 4px; }
  .row.warm .body .t { color: #9A5F1C; }
  .row.warm .body .d { color: #6B4A22; }

  /* 세로 목록이 4개 이상이라 한 화면을 넘칠 때 — 슬라이드에 _class: tight 적용 */
  section.tight .sub { margin-bottom: 16px; }
  section.tight .rows { gap: 10px; }
  section.tight .row { padding: 14px 26px; }

  /* 하단 강조 문구 */
  .note { margin-top: 30px; text-align: center; font-size: 21px; font-weight: 700; color: #1B5878; }
  .note.warm { color: #9A5F1C; }

  /* 강조 배너 */
  .banner {
    margin-top: 26px; background: #4A76A3; color: #FFFFFF;
    border-radius: 12px; padding: 20px 28px;
    font-size: 20px; font-weight: 700; text-align: center;
  }

  section table {
    border-collapse: collapse; font-size: 20px;
    width: 100% !important; display: table !important; table-layout: fixed;
    margin: 0;
  }
  section th {
    background: #3D6288; color: #FFFFFF; padding: 14px 18px;
    text-align: left; border: none; font-weight: 700;
  }
  section td {
    padding: 14px 18px; background: #FFFFFF; color: #24404F;
    border-bottom: 1px solid #DCE6EC; border-left: none; border-right: none;
  }
  section tr:nth-child(even) td { background: #F2F7FB; }
  section td strong { color: #1B5878; }

  img { border-radius: 10px; }
  footer, header { color: #5A6C77; font-size: 14px; }

  /* ══════════ 간지 · 진한 파랑 ══════════
     모든 자식 요소 색을 명시하고, 이름은 인라인으로 한 번 더 고정합니다 */
  section.lead {
    background: #4A76A3;
    color: #FFFFFF;
    position: relative;
    overflow: hidden;
  }
  section.lead::before {
    content: ""; position: absolute; right: -140px; top: -190px;
    width: 560px; height: 560px; border-radius: 50%;
    background: rgba(255,255,255,0.10);
  }
  section.lead::after {
    content: ""; position: absolute; right: -80px; bottom: -260px;
    width: 420px; height: 420px; border-radius: 50%;
    background: rgba(255,255,255,0.08);
  }
  section.lead h1, section.lead h2, section.lead h3 { color: #FFFFFF; }
  section.lead p, section.lead li, section.lead .d { color: #FFFFFF; }
  section.lead strong, section.lead b { color: #FFFFFF; }
  section.lead .label {
    font-size: 17px; color: #FFFFFF; letter-spacing: 0.18em; margin-bottom: 26px;
  }
  section.lead .rule {
    width: 120px; height: 2px; background: rgba(255,255,255,0.55);
    margin: 34px 0 18px;
  }
  section.lead .team { font-size: 19px; color: #FFFFFF; }
  section.lead table { color: #FFFFFF; }
  section.lead th { background: rgba(255,255,255,0.18); color: #FFFFFF; }
  section.lead td {
    background: transparent; color: #FFFFFF;
    border-bottom: 1px solid rgba(255,255,255,0.28);
  }
  section.lead tr:nth-child(even) td { background: rgba(0,0,0,0.10); }
  section.lead footer, section.lead header { color: #FFFFFF; }
  section.lead .cards .card {
    background: #3D6288; border-color: rgba(255,255,255,0.30);
  }
  section.lead .card .t { color: #FFFFFF; }
  section.lead .card .d { color: #FFFFFF; }
---

<!-- _class: lead -->
<!-- _paginate: false -->

<div class="label">SKN 36기 · 1ST 프로젝트</div>

# 상권이 아니라<br>화물의 흐름을 봅니다

<p style="font-size:23px;color:#FFFFFF;margin-top:20px">화물차 등록 데이터 기반 물류 거점 분석 서비스 · WAYLOGI</p>

<div class="rule"></div>

<div class="team"><b style="color:#FFFFFF">SKN 36기 2TEAM</b></div>

---

<!-- _class: lead -->

<div class="label">TEAM</div>

## SKN 36기 2TEAM

<div class="cards" style="margin-top:34px">
<div class="card">
<div class="t" style="color:#FFFFFF">나지인</div>
<div class="d" style="color:#FFFFFF">팀장<br>데이터 전처리 · DB 구축<br>백엔드</div>
</div>
<div class="card">
<div class="t" style="color:#FFFFFF">문희영</div>
<div class="d" style="color:#FFFFFF">시장 조사<br>요구사항 정의서<br>화면 시각화</div>
</div>
<div class="card">
<div class="t" style="color:#FFFFFF">임성경</div>
<div class="d" style="color:#FFFFFF">발표<br>시장 조사<br>요구사항 정의서<br>화면 시각화</div>
</div>
<div class="card">
<div class="t" style="color:#FFFFFF">차용우</div>
<div class="d" style="color:#FFFFFF">데이터 전처리 · ERD 제작<br>프론트엔드</div>
</div>
</div>

---

## 목차

<div class="sub">서론 → 본론 → 결론 순으로 진행합니다</div>

<div class="rows">
<div class="row"><div class="num">1</div><div class="body">
<div class="t">서론</div><div class="d">문제인식 · 시장분석 · 경쟁사 분석</div></div></div>
<div class="row"><div class="num">2</div><div class="body">
<div class="t">본론</div><div class="d">타겟 정의 · 프로젝트 개요 · 해결 방안 · 화면 시연</div></div></div>
<div class="row"><div class="num">3</div><div class="body">
<div class="t">결론</div><div class="d">향후 개선 방향 · Q&amp;A</div></div></div>
</div>

---

<!-- _class: lead -->

<div class="label">PART 1</div>

# 서론

<p style="font-size:22px">문제 제기 및 시장 상황</p>

---

## 빠른 배송은 기준이 됐지만, 모두에게는 아닙니다

<div class="sub">물류센터 분포에 따라 갈리는 배송 경험</div>

<div class="cards">
<div class="card">
<div class="t">수도권 · 대도시</div>
<div class="d">· 대형 물류센터가 밀집<br>· 당일 · 익일 배송이 일상<br>· 선택지가 많고 경쟁도 치열</div>
</div>
<div class="card warm">
<div class="t">도서 · 산간 · 지방 중소도시</div>
<div class="d">· 인근에 대형 물류센터가 부족<br>· 배송에 며칠이 걸리는 경우가 많음<br>· 같은 서비스, 다른 경험</div>
</div>
</div>

<div class="note warm">지역 간 배송 격차</div>

---

## 실제 대화에서 출발했습니다

![bg right:42% w:430](images/fig01_chat.png)

<div class="sub">문제는 통계가 아니라 대화에서 먼저 보였습니다</div>

<div class="rows">
<div class="row"><div class="num">1</div><div class="body">
<div class="t">로켓배송이 뜨지 않는 지역</div></div></div>
<div class="row"><div class="num">2</div><div class="body">
<div class="t">배송에 이틀 이상 걸리는 경우</div></div></div>
<div class="row"><div class="num">3</div><div class="body">
<div class="t">본가에서는 다음날 도착</div>
<div class="d">이유를 물었더니 "물류센터가 가까워서"</div></div></div>
</div>

---

<!-- _class: lead -->

<div class="label">관점을 바꾸면</div>

## 배송이 늦는 지역은<br>아직 아무도 잡지 못한 수요입니다

<div class="cards" style="margin-top:40px">
<div class="card">
<div class="t" style="color:#FFFFFF">물류 인프라 부족</div>
<div class="d" style="color:#FFFFFF">센터도, 차량도 적습니다</div>
</div>
<div class="card">
<div class="t" style="color:#FFFFFF">경쟁이 덜한 시장</div>
<div class="d" style="color:#FFFFFF">선점한 기업이 없습니다</div>
</div>
<div class="card">
<div class="t" style="color:#FFFFFF">먼저 들어갈 기회</div>
<div class="d" style="color:#FFFFFF">거점 하나가 크게 작용합니다</div>
</div>
</div>

<p style="margin-top:32px;font-size:20px;color:#FFFFFF">사회적 과제이자, 동시에 사업 기회입니다</p>

---

## 같은 사실을 기업 관점으로 다시 읽으면

<div class="sub">현상에서 기회까지, 네 단계로 이어집니다</div>

![w:1150](images/fig08_reframe.png)

---

## 물류센터는 수도권에 집중되어 있습니다

<div class="sub">문제 인식이 데이터로도 확인됩니다</div>

![w:1150](images/fig07_warehouse.png)

<!-- footer: 출처 · 행정안전부 지방행정 인허가데이터 (2021.08.31 기준) -->

---

## 시장조사

<div class="sub">데이터는 있지만, 의사결정에 바로 쓰이지 못하고 있습니다</div>

<div class="cards">
<div class="card stat" style="flex:0 0 320px">
<div class="cap">전국 화물차 등록</div>
<div class="big">369만 대</div>
<div class="memo">물류시설 · 산업 · 기업 데이터까지<br>확장할 수 있는 기반</div>
</div>
<div class="rows" style="flex:1">
<div class="row"><div class="body">
<div class="n" style="color:#4A87AE">문제</div>
<div class="d">데이터는 존재하지만 입지 의사결정에 바로 활용하기 어렵습니다</div></div></div>
<div class="row"><div class="body">
<div class="n" style="color:#4A87AE">기존 해결 방식</div>
<div class="d">공공 통계와 물류정보 사이트에서 각각 조회하고 직접 비교합니다</div></div></div>
<div class="row"><div class="body">
<div class="n" style="color:#4A87AE">해결되지 않은 문제</div>
<div class="d">정보 분산 · 지역 비교의 번거로움 · 기업 관점 분석 부족</div></div></div>
</div>
</div>

<div class="banner">조회 → 지역 비교 · 분석 → 사용자 중요도 반영 → 입지 후보 · 근거를 하나의 시스템에서</div>

<!-- footer: '' -->

---

## 경쟁사 분석

<div class="sub">기존 솔루션과 우리 서비스를 같은 표에서 비교했습니다</div>

| 구분 | SK AX | NICE 지니데이타 | WAYLOGI |
|:--|:--|:--|:--|
| 주요 목적 | 물류센터 입지·구축 | 상권·출점 분석 | **물류 유망지역 추천** |
| 주요 대상 | 물류·유통 기업 | 프랜차이즈 기업 | **화물차·운송 기업** |
| 핵심 데이터 | 물동량·물류망 | 매출·유동인구 | **자동차·화물차·인구** |
| 화물차 특화 | 보통 | 없음 | **특화** |
| 기업 FAQ | 별도 영역 | 별도 영역 | **서비스 내 통합** |

<div class="note">WAYLOGI는 경쟁사가 아니라, 비교를 위해 함께 넣은 우리 서비스입니다</div>

---

## Pain Point

<div class="sub">시장조사와 경쟁사 분석에서 도출한 세 가지 불편함</div>

<div class="rows">
<div class="row warm"><div class="num">1</div><div class="body">
<div class="t">정보 탐색의 번거로움</div>
<div class="d">데이터가 여러 공공 통계 · 사이트에 분산되어, 필요한 자료를 직접 검색하고 모아야 합니다</div></div></div>
<div class="row warm"><div class="num">2</div><div class="body">
<div class="t">지역 비교 · 분석의 어려움</div>
<div class="d">기존 통계는 단순 제공 중심이라, 등록대수 · 증가율 · 비중을 직접 계산해 비교해야 합니다</div></div></div>
<div class="row warm"><div class="num">3</div><div class="body">
<div class="t">화물차 특화 · 맞춤 분석 부족</div>
<div class="d">기존 서비스는 물류센터 구축 · 상권 분석 중심이라, 화물차 기준과 기업별 중요도를 반영하기 어렵습니다</div></div></div>
</div>

<div class="note">이 불편함을 어떻게 풀지가 저희 분석 설계의 출발점입니다</div>

---

<!-- _class: lead -->

<div class="label">PART 2</div>

# 본론

<p style="font-size:22px">기획 · 타겟 정의 · 해결 방안 · 화면 시연</p>

---

## 이 격차를 줄일 수 있는 사람들

<div class="sub">화물차 데이터를 활용해 사업 지역을 검토하는 물류 · 운송 기업</div>

<div class="rows">
<div class="row"><div class="num">1</div><div class="body">
<div class="t">운송망 · 영업지역을 확장하려는 물류 · 운송 기업</div>
<div class="d">지역별 화물차 · 자동차 · 인구 현황을 바탕으로 신규 진출 지역을 검토합니다</div></div></div>
<div class="row"><div class="num">2</div><div class="body">
<div class="t">신규 사업 지역을 찾는 중견 · 중소 물류 · 운송 기업</div>
<div class="d">확장 의지는 있지만 자체 데이터 분석 인력이 없어, 판단 근거를 마련하기 어렵습니다</div></div></div>
<div class="row"><div class="num">3</div><div class="body">
<div class="t">화물차 운영이 사업의 핵심인 운송 사업자</div>
<div class="d">지역별 화물차 규모와 변화 추이를 통해 사업성이 높은 지역을 검토합니다</div></div></div>
</div>

---

## 타겟 규모

<div class="sub">대부분이 소규모 사업자입니다</div>

<div class="cards">
<div class="card stat" style="flex:0 0 340px">
<div class="cap">전체 화물자동차 운송업체</div>
<div class="big">184,559개</div>
<div class="memo">통계청 운수업조사 · 2017년 기준</div>
</div>
<div class="rows" style="flex:1">
<div class="row"><div class="body">
<div class="t">용달화물자동차운송업체가 가장 많습니다</div>
<div class="d">시장 진입 비용이 상대적으로 낮기 때문입니다</div></div></div>
<div class="row"><div class="body">
<div class="t">택배업체가 가장 적습니다</div>
<div class="d">전국 집 · 배송 시스템을 갖춰야 하기 때문입니다</div></div></div>
<div class="row"><div class="body">
<div class="t">자체 분석 인력을 두기 어려운 기업이 다수</div>
<div class="d">개별화물자동차운송업은 허가 기준이 1대입니다</div></div></div>
</div>
</div>

<!-- footer: 출처 · 통계청 운수업조사 (2017년 기준) -->

---

## 프로젝트 정의

<div class="sub">사용자가 직접 해야 했던 과정을 하나의 서비스로 연결합니다</div>

<div class="cards">
<div class="card"><div class="n">01</div>
<div class="t">데이터 통합</div>
<div class="d">자동차 · 화물차 · 인구 데이터를<br>지역 기준으로 결합</div></div>
<div class="card"><div class="n">02</div>
<div class="t">지표 산출</div>
<div class="d">산업성 · 성장성 · 수요성으로<br>물류 거점 점수 계산</div></div>
<div class="card warm"><div class="n">03</div>
<div class="t">후보 · 근거 제시</div>
<div class="d">유망 입지 후보 순위와<br>추천 근거를 함께 제공</div></div>
</div>

<div class="banner">데이터 조회 → 지역 비교 · 분석 → 중요도 설정 → 점수 계산 → 순위 → 근거 확인</div>

<!-- footer: '' -->

---

## 핵심 콘셉트

<div class="sub">네 가지 원칙으로 설계했습니다</div>

<div class="cards" style="margin-bottom:20px">
<div class="card"><div class="n">01</div>
<div class="t">단순 조회가 아닌 비교 · 분석</div>
<div class="d">자동차 · 화물차 · 인구 데이터를<br>지역 단위로 통합해 나란히 비교합니다</div></div>
<div class="card"><div class="n">02</div>
<div class="t">사용자가 직접 정하는 중요도</div>
<div class="d">산업성 · 성장성 · 수요성 응답을<br>그대로 가중치로 반영합니다</div></div>
</div>

<div class="cards">
<div class="card"><div class="n">03</div>
<div class="t">점수와 함께 근거 제공</div>
<div class="d">항목별 점수 · 시계열 지표 · 데이터 기준을<br>함께 보여줍니다</div></div>
<div class="card warm"><div class="n">04</div>
<div class="t">'최적 입지'가 아닌 '유망 입지 후보'</div>
<div class="d">단정하지 않고<br>의사결정을 돕는 참고 자료로 제공합니다</div></div>
</div>

<div class="note">순위만 보여주지 않고 "왜 이 지역이 추천되었는지"를 함께 확인할 수 있도록 합니다</div>

---

## 사용 데이터

<div class="sub">두 가지 공공데이터를 지역 · 연월 기준으로 결합합니다</div>

<div class="cards">
<div class="card">
<div class="n">국토교통부 · Excel + Python ETL</div>
<div class="t">자동차등록현황보고</div>
<div class="d">시군구별 · 월별 제공<br><br>차종을 승용 · 승합 · 화물 · 특수로,<br>용도를 관용 · 자가용 · 영업용으로 구분해<br>제공하므로 <b>사업 목적인 영업용까지 구분</b>할 수 있습니다</div>
</div>
<div class="card">
<div class="n">행정안전부 · 공공데이터포털 API</div>
<div class="t">주민등록 인구통계</div>
<div class="d">시군구별 · 월별 제공<br><br>API로 시군구 단위 37개월을 자동 수집했습니다.<br>물류는 받는 사람이 있어야 발생하므로<br><b>배후 수요의 기준</b>이 됩니다</div>
</div>
</div>

<div class="note">두 자료 모두 시군구별 · 월별이라 지역 코드와 시점으로 바로 결합할 수 있었습니다</div>

<!-- footer: 분석 기간 · 2023.07 ~ 2026.07 (37개월)  ·  분석 단위 · 전국 시군구 -->

---

## 데이터를 이렇게 수집했습니다

<div class="sub">두 데이터의 제공 형태가 달라 수집 방식도 다르게 했습니다</div>

<div class="cards">
<div class="card">
<div class="n">인구 데이터</div>
<div class="t">공공데이터포털 API 자동 수집</div>
<div class="d">
<b>requests</b> 로 API 호출 · <b>xml</b> 로 응답 파싱<br>
<b>pandas</b> 로 지역별 데이터 통합<br><br>
시군구 단위로 37개월을 반복 호출해<br>하나의 데이터셋으로 만들었습니다
</div></div>

<div class="card">
<div class="n">자동차 등록 데이터</div>
<div class="t">공식 Excel 원본 + Python ETL</div>
<div class="d">
국토교통부 제공 Excel 확보<br>
<b>etl/load_data.py</b> 로 검증 · 변환 · 적재<br><br>
지역 · 연월 · 차종 · 등록대수 구조로<br>정제해 MySQL에 넣었습니다
</div></div>
</div>

<div class="note">수집일자 2026.08.22 · 수집 기간 2023.07 ~ 2026.07 (37개월)</div>

<!-- footer: 인구 데이터 출처 · 행정안전부 행정동별 주민등록 인구 및 세대현황 (공공데이터포털 API) -->

---

<!-- _class: tight -->

## 전처리에서 가장 신경 쓴 것

<div class="sub">수집으로 끝내지 않고 두 데이터의 기준을 맞췄습니다</div>

<div class="rows">
<div class="row"><div class="num">1</div><div class="body">
<div class="t">행정구역 변경 대응</div>
<div class="d">최신 지역코드로 조회되지 않는 지역은 <b>이전 코드로 다시 수집</b>했습니다. 조회 안 되는 데이터를 지우지 않고 편입 여부를 확인해 보완했습니다</div></div></div>

<div class="row"><div class="num">2</div><div class="body">
<div class="t">지역 기준 통일</div>
<div class="d">인구 데이터의 시군구명, 자동차 데이터의 시군구명, <b>지도에서 쓰는 지역코드</b> 세 가지를 대조해 같은 지역을 같은 이름으로 맞췄습니다</div></div></div>

<div class="row"><div class="num">3</div><div class="body">
<div class="t">날짜 형식 통일</div>
<div class="d">두 데이터 모두 202307 형식으로 맞춰 같은 연월끼리 결합할 수 있게 했습니다</div></div></div>

<div class="row warm"><div class="num">4</div><div class="body">
<div class="t">중복 적재 방지</div>
<div class="d">지역 · 연월 · 차종 복합키로 <b>같은 지역 · 같은 월 · 같은 차종의 중복을 구조적으로 차단</b>했습니다</div></div></div>
</div>

<!-- footer: '' -->

---

## 최종 데이터 규모

<div class="sub">정제를 마친 뒤 이런 규모의 데이터를 구축했습니다</div>

<div class="cards">
<div class="card stat" style="flex:0 0 380px">
<div class="cap">지역 × 기간 × 차종</div>
<div class="big">110,556건</div>
<div class="memo">249개 시군구 × 37개월 × 12개 차량 분류</div>
</div>
<div class="rows" style="flex:1">
<div class="row"><div class="body">
<div class="t">249개 시군구</div>
<div class="d">시도 합계 행을 제외한 전국 시군구</div></div></div>
<div class="row"><div class="body">
<div class="t">37개월</div>
<div class="d">2023년 7월 ~ 2026년 7월 · 월 단위</div></div></div>
<div class="row"><div class="body">
<div class="t">12개 차량 분류</div>
<div class="d">승용 · 승합 · 화물 · 특수 × 관용 · 자가용 · 영업용</div></div></div>
</div>
</div>

---

## 분석은 6단계로 진행됩니다

<div class="sub">사용자의 관심에서 출발해 유망 입지 후보로 이어집니다</div>

<div class="cards" style="margin-bottom:20px">
<div class="card"><div class="n">01</div><div class="t">사용자 중요도 조사</div>
<div class="d">무엇을 중요하게 보는지<br>먼저 묻습니다</div></div>
<div class="card"><div class="n">02</div><div class="t">데이터 통합</div>
<div class="d">두 데이터를 지역 기준으로<br>하나로 합칩니다</div></div>
<div class="card"><div class="n">03</div><div class="t">시계열 분석</div>
<div class="d">37개월을 비교해<br>증가율과 지속성을 봅니다</div></div>
</div>

<div class="cards">
<div class="card"><div class="n">04</div><div class="t">물류 거점 점수</div>
<div class="d">산업성 · 성장성 · 수요성을<br>종합해 점수를 냅니다</div></div>
<div class="card"><div class="n">05</div><div class="t">추천 근거 제공</div>
<div class="d">점수와 주요 지표를<br>함께 보여줍니다</div></div>
<div class="card warm"><div class="n">06</div><div class="t">유망 입지 후보 추천</div>
<div class="d">점수와 근거를 함께<br>의사결정에 활용합니다</div></div>
</div>

<div class="note">사용자의 관심을 먼저 묻는다는 점이 기존 분석 서비스와 가장 다른 부분입니다</div>

<!-- footer: '' -->

---

## 물류 거점 평가 3가지 핵심 지표

<div class="cards">
<div class="card">
<div class="t">산업성</div>
<div class="d"><b>물류 산업 기반 강도</b><br><br>
✓ 영업용 화물 비중<br>✓ 입지계수 (LQ)<br>✓ 인구 1천 명당 화물차<br><br>
점수가 높을수록<br>이미 물류가 활발한 지역</div>
</div>
<div class="card">
<div class="t">성장성</div>
<div class="d"><b>물류 산업 성장 속도</b><br><br>
✓ 화물차 전년동월비<br>✓ 12개월 가속도<br>✓ 추세 지속성<br>✓ 영업용 전환율<br>✓ 인구-화물 디커플링<br>✓ 안정성</div>
</div>
<div class="card">
<div class="t">수요성</div>
<div class="d"><b>물류 수요 규모</b><br><br>
✓ 자체 인구<br>✓ 인구 밀도 (면적 기준)<br>✓ 인구 증가율<br><br>
점수가 높을수록<br>물류 수요가 큰 지역</div>
</div>
</div>

---

## 점수 산출 과정

<div class="sub">지표를 전국 기준으로 환산한 뒤 사용자 가중치를 반영합니다</div>

![w:1150](images/fig09_scoring.png)

<div class="note" style="font-size:18px;font-weight:400;color:#33454F">
<b>w1 · w2 · w3</b> 은 사용자가 정한 <b>비중</b>입니다.
산업성을 중요하게 답하면 w1이 커지고, 세 값을 더하면 항상 1이 됩니다.
</div>

---

## 데이터베이스 설계

<div class="sub">기준 정보와 수치 데이터를 분리하고, 복합키로 중복을 막았습니다</div>

![w:1150](images/fig11_erd.png)

<div class="note" style="font-size:18px;font-weight:400;color:#33454F">
설계 초기에는 <b>연·반기·분기를 관리하는 날짜 테이블</b>도 두었지만,
연월 단위 조회만 쓰이는 것을 확인해 <b>이번 프로젝트에서 제거</b>했습니다.
</div>

---

## 시스템 아키텍처

<div class="sub">공공데이터를 정제해 적재하고, 서비스 계층에서 지표를 계산합니다</div>

![w:1150](images/fig10_architecture.png)

---

## 경쟁사 한계를 이렇게 넘었습니다

<div class="sub">기존 서비스에서 불편했던 지점을 하나씩 대응했습니다</div>

| Pain Point | 해결 방안 |
|---|---|
| 데이터가 분산 | 두 공공데이터를 **한 화면에서 조회** |
| 직접 계산해야 함 | 증가율 · 비중 · 밀도를 **자동 산출** |
| 화물차 특화 부족 | **화물차 중심**, 영업용 비중까지 구분 |
| 기업별 기준 반영 안 됨 | **사용자가 가중치를 직접 설정** |
| 순위만 제공 | **계산 과정을 그대로 공개** |

<div class="note">다섯 가지 불편함을 하나의 서비스 안에서 해결했습니다</div>

---

<!-- _class: lead -->

<div class="label">LIVE DEMO</div>

# 실제 화면으로 보여드리겠습니다

<div class="cards" style="margin-top:40px">
<div class="card">
<div class="t" style="color:#FFFFFF">01 데이터 조회</div>
<div class="d" style="color:#FFFFFF">지도 · 검색 · 지역 비교</div></div>
<div class="card">
<div class="t" style="color:#FFFFFF">02 중요도 진단</div>
<div class="d" style="color:#FFFFFF">문항 응답 · 가중치 실시간 반영</div></div>
<div class="card">
<div class="t" style="color:#FFFFFF">03 유망지역 순위</div>
<div class="d" style="color:#FFFFFF">순위 · 근거 보기</div></div>
</div>

---

## 같은 데이터, 다른 결과

<div class="sub">사용자가 무엇을 중요하게 보느냐에 따라 순위가 달라집니다</div>

<div class="cards">
<div class="card">
<div class="t">산업성 우선</div>
<div class="d">이미 화물 이동이 활발하고<br>영업용 비중이 높은 지역</div></div>
<div class="card">
<div class="t">성장성 우선</div>
<div class="d">규모는 작아도<br>최근 증가 흐름이 뚜렷한 지역</div></div>
<div class="card">
<div class="t">수요성 우선</div>
<div class="d">배후 인구가 많고<br>인구가 늘고 있는 지역</div></div>
</div>

<div class="note">기업마다 다른 기준을 그대로 반영하는 것이 기존 서비스와의 가장 큰 차이입니다</div>

---

## 결과를 어떻게 신뢰할 수 있나

<div class="sub">추천이 맞다는 근거를 세 가지 방법으로 확인합니다</div>

<div class="cards">
<div class="card"><div class="n">1</div>
<div class="t">실제 물류 거점과 대조</div>
<div class="d">이미 대형 물류센터가 있는 지역이 상위권에 나오는지 확인합니다. 나온다면 모델이 현실과 맞다는 근거가 됩니다.</div></div>
<div class="card"><div class="n">2</div>
<div class="t">가중치를 바꿔도 확인</div>
<div class="d">가중치 조합을 여러 개 적용해도 상위권에 남는 지역을 확인합니다. 결과가 가중치에 크게 흔들리지 않음을 봅니다.</div></div>
<div class="card"><div class="n">3</div>
<div class="t">지표 중복 확인</div>
<div class="d">산업성과 수요성이 서로 겹치지 않는지 확인합니다. 같은 것을 두 번 세지 않도록 조정합니다.</div></div>
</div>

<div class="banner">점수의 절대값이 아닌 순위와 근거로 해석하며, 결과는 '유망 입지 후보'로 제시합니다</div>


---

<!-- _class: lead -->

<div class="label">PART 3</div>

# 결론

<p style="font-size:22px">향후 개선 방향 및 마무리</p>

<!-- footer: '' -->

---

## 향후 개선 방향

<div class="sub">설계와 기능 양쪽에서 다듬을 부분을 확인했습니다</div>

<div class="cards">
<div class="card"><div class="n">01</div>
<div class="t">관리자 페이지 구현</div>
<div class="d">문의 테이블에 답변 상태 컬럼은 있지만<br>답변을 등록할 화면이 없습니다.<br><b>관리자 계정과 답변 화면</b>을 만들어 FAQ 흐름을 완성하겠습니다.</div></div>

<div class="card"><div class="n">02</div>
<div class="t">점수 결과 저장</div>
<div class="d">현재는 조회할 때마다 지표를 계산합니다.<br>산출된 점수를 <b>별도 테이블에 저장</b>해<br>조회 속도와 재현성을 높이겠습니다.</div></div>

<div class="card warm"><div class="n">03</div>
<div class="t">데이터 범위 확장</div>
<div class="d">물류시설과 물동량 데이터를 더해<br><b>미반영 요인을 줄여</b> 나가겠습니다.</div></div>
</div>

<div class="note">직접 만들어 보고 나서야 무엇이 필요하고 무엇이 불필요한지 알 수 있었습니다</div>

---

## 참고자료

<div class="sub">사용 데이터</div>

| 자료 | 기관 |
|---|---|
| 자동차등록현황보고 | 국토교통부 · 국토교통 통계누리 |
| 주민등록 인구통계 | 행정안전부 |

<div class="sub" style="margin-top:24px">시장 근거 자료</div>

| 자료 | 출처 | 시점 |
|---|---|---|
| 물류창고 지역별 분포 | 행정안전부 지방행정 인허가데이터 | 2021.08 |
| 화물자동차 운송업체 수 | 통계청 운수업조사 | 2017 |
| 물류시설 입지 결정 요인 | 대한국토·도시계획학회지 | — |


---

<!-- _class: lead -->
<!-- _paginate: false -->

<div class="label">THANK YOU</div>

# 감사합니다

<div class="rule"></div>

<div class="team">
<b style="color:#FFFFFF">SKN 36기 2TEAM</b><br>
<span style="color:#FFFFFF;font-size:18px">나지인 · 문희영 · 임성경 · 차용우</span>
</div>
