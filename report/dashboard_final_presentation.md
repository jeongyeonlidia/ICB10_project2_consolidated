---
marp: true
theme: default
size: 16:9
paginate: true
header: 'IT·데이터·마케팅 5대 직무 실무 툴 수급 미스매치 진단 & AI JD 시뮬레이터 SaaS'
footer: '2026.08 · AI Data Analysis Team'
style: |
  @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

  /* ── 전역 기본 스타일 ── */
  section {
    font-family: 'Pretendard', system-ui, -apple-system, sans-serif;
    background: #f8fafc;
    color: #1e293b;
    padding: 44px 64px;
    font-size: 0.94rem;
    line-height: 1.6;
    word-break: keep-all;
  }
  header, footer {
    font-size: 0.72rem;
    color: #64748b;
    font-weight: 500;
  }

  /* ── 표지 ── */
  section.cover {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
    padding: 56px 72px;
    display: flex;
    flex-direction: column;
    justify-content: center;
  }
  section.cover h1 {
    font-size: 2.5rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.25;
    margin: 0 0 16px 0;
  }
  section.cover h2 {
    font-size: 1.2rem;
    font-weight: 400;
    color: #93c5fd;
    margin: 0 0 40px 0;
  }
  section.cover .divider {
    width: 56px;
    height: 4px;
    background: #2563eb;
    border-radius: 2px;
    margin-bottom: 36px;
  }
  section.cover .meta {
    color: #94a3b8;
    font-size: 0.9rem;
    border-top: 1px solid rgba(255,255,255,0.15);
    padding-top: 20px;
  }
  section.cover header, section.cover footer { display: none; }

  /* ── 섹션 간지 슬라이드 ── */
  section.divider-slide {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #334155 100%);
    padding: 56px 72px;
    display: flex;
    flex-direction: column;
    justify-content: center;
    color: #ffffff;
  }
  section.divider-slide .part-tag {
    display: inline-block;
    background: rgba(37, 99, 235, 0.3);
    border: 1px solid #60a5fa;
    color: #93c5fd;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 0.88rem;
    font-weight: 800;
    margin-bottom: 16px;
    width: fit-content;
  }
  section.divider-slide h1 {
    font-size: 2.3rem;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 12px;
    line-height: 1.3;
  }
  section.divider-slide p {
    font-size: 1.05rem;
    color: #cbd5e1;
    margin: 0;
  }
  section.divider-slide header, section.divider-slide footer { display: none; }

  /* ── 엔딩 슬라이드 ── */
  section.end {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 100%);
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    text-align: center;
  }
  section.end h1 {
    font-size: 3rem;
    font-weight: 800;
    color: #ffffff;
    margin: 0 0 12px 0;
  }
  section.end p {
    color: #93c5fd;
    font-size: 1.2rem;
    margin: 0;
  }
  section.end header, section.end footer { display: none; }

  /* ── 타이포그래피 ── */
  h1 {
    font-size: 1.85rem;
    font-weight: 800;
    color: #0f172a;
    margin: 0 0 8px 0;
    letter-spacing: -0.02em;
  }
  h2 {
    font-size: 1.05rem;
    font-weight: 500;
    color: #475569;
    margin: 0 0 20px 0;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 10px;
  }
  h3 {
    font-size: 0.95rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 8px 0;
  }
  p { margin: 0 0 8px 0; font-size: 0.88rem; color: #475569; }
  ul { padding-left: 18px; margin: 4px 0; }
  li { font-size: 0.86rem; color: #334155; margin-bottom: 5px; }
  strong { color: #2563eb; }
  code {
    background: #e0e7ff;
    color: #3730a3;
    padding: 1px 6px;
    border-radius: 4px;
    font-size: 0.82rem;
  }

  /* ── 이미지 프레임 ── */
  .img-frame {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 4px 14px rgba(15,23,42,0.08);
  }
  .img-frame img {
    width: 100%;
    max-height: 330px;
    object-fit: cover;
    object-position: top;
    display: block;
  }

  /* ── 펀널(Funnel) 전용 스타일 ── */
  .funnel-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    margin-top: 10px;
  }
  .funnel-layer {
    border-radius: 12px;
    padding: 14px 28px;
    color: #ffffff;
    box-shadow: 0 4px 14px rgba(15,23,42,0.08);
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .funnel-layer-top {
    width: 98%;
    background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
    border-left: 6px solid #60a5fa;
  }
  .funnel-layer-mid {
    width: 82%;
    background: linear-gradient(135deg, #4c1d95 0%, #7c3aed 100%);
    border-left: 6px solid #c084fc;
  }
  .funnel-layer-bot {
    width: 66%;
    background: linear-gradient(135deg, #064e3b 0%, #10b981 100%);
    border-left: 6px solid #34d399;
  }
  .funnel-title {
    font-size: 1.05rem;
    font-weight: 800;
    margin-bottom: 2px;
  }
  .funnel-desc {
    font-size: 0.84rem;
    opacity: 0.92;
  }
  .funnel-badge {
    background: rgba(255,255,255,0.2);
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.78rem;
    font-weight: 700;
    white-space: nowrap;
  }

  /* ── 프로세스 카드 전용 스타일 ── */
  .process-grid {
    display: grid;
    grid-template-columns: repeat(6, 1fr);
    gap: 8px;
    margin-top: 14px;
  }
  .process-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-top: 4px solid #2563eb;
    border-radius: 10px;
    padding: 12px 10px;
    text-align: center;
    box-shadow: 0 2px 6px rgba(0,0,0,0.04);
  }
  .process-num {
    font-size: 0.75rem;
    font-weight: 800;
    color: #2563eb;
    background: #dbeafe;
    padding: 2px 8px;
    border-radius: 10px;
    display: inline-block;
    margin-bottom: 6px;
  }
  .process-card h4 {
    font-size: 0.82rem;
    font-weight: 700;
    color: #0f172a;
    margin: 0 0 4px 0;
  }
  .process-card p {
    font-size: 0.74rem;
    color: #64748b;
    margin: 0;
    line-height: 1.35;
  }

  /* ── 렌더링 호환형 서브그래프 다이어그램 스타일 ── */
  .subgraph-diagram-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
    margin-top: 14px;
    margin-bottom: 10px;
  }
  .subgraph-box {
    flex: 1;
    border-radius: 14px;
    padding: 12px 10px;
    box-shadow: 0 4px 10px rgba(0,0,0,0.05);
  }
  .subgraph-box-blue { background: #eff6ff; border: 2px solid #bfdbfe; }
  .subgraph-box-purple { background: #faf5ff; border: 2px solid #e9d5ff; }
  .subgraph-box-green { background: #f0fdf4; border: 2px solid #bbf7d0; }

  .subgraph-header {
    font-size: 0.76rem;
    font-weight: 800;
    color: #1e40af;
    background: #dbeafe;
    padding: 3px 10px;
    border-radius: 12px;
    display: inline-block;
    margin-bottom: 8px;
  }
  .subgraph-box-purple .subgraph-header { color: #6b21a8; background: #f3e8ff; }
  .subgraph-box-green .subgraph-header { color: #166534; background: #dcfce7; }

  .subgraph-nodes {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 4px;
  }
  .node-pill {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-radius: 8px;
    padding: 8px 6px;
    font-size: 0.74rem;
    font-weight: 700;
    color: #0f172a;
    box-shadow: 0 2px 4px rgba(0,0,0,0.03);
    text-align: center;
    flex: 1;
  }
  .node-connector {
    color: #94a3b8;
    font-weight: 800;
    font-size: 0.85rem;
  }
  .group-connector {
    color: #2563eb;
    font-weight: 900;
    font-size: 1.2rem;
  }

  /* ── 그리드 레이아웃 ── */
  .cols-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
  .cols-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 14px; }
  .cols-4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }

  /* ── 카드 ── */
  .card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px 20px;
    box-shadow: 0 2px 8px rgba(15,23,42,0.04);
  }
  .card-indigo {
    background: linear-gradient(135deg, #eef2ff, #e0e7ff);
    border: 1px solid #c7d2fe;
    border-top: 4px solid #4f46e5;
  }
  .card-sky {
    background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
    border: 1px solid #bae6fd;
    border-top: 4px solid #0284c7;
  }
  .card-rose {
    background: linear-gradient(135deg, #fff1f2, #ffe4e6);
    border: 1px solid #fecdd3;
    border-top: 4px solid #e11d48;
  }
  .card-emerald {
    background: linear-gradient(135deg, #f0fdf4, #dcfce7);
    border: 1px solid #bbf7d0;
    border-top: 4px solid #10b981;
  }
  .card-purple {
    background: linear-gradient(135deg, #f3e8ff, #e9d5ff);
    border: 1px solid #d8b4fe;
    border-top: 4px solid #7c3aed;
  }
  .card-dark {
    background: #0f172a;
    border: none;
    color: #f8fafc;
  }
  .card-dark h3 { color: #60a5fa; }
  .card-dark p, .card-dark li { color: #cbd5e1; }

  /* ── 배지 ── */
  .badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    margin-bottom: 8px;
  }
  .badge-blue { background: #dbeafe; color: #1e40af; }
  .badge-indigo { background: #e0e7ff; color: #3730a3; }
  .badge-green { background: #dcfce7; color: #166534; }
  .badge-red { background: #fee2e2; color: #991b1b; }
  .badge-amber { background: #fef3c7; color: #92400e; }
  .badge-purple { background: #f3e8ff; color: #6b21a8; }
  .badge-slate { background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }

  /* ── 콜아웃 ── */
  .callout {
    background: #ffffff;
    border-left: 4px solid #2563eb;
    border-radius: 0 10px 10px 0;
    padding: 12px 18px;
    margin-bottom: 18px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.04);
  }
  .callout p { font-size: 0.9rem; color: #334155; margin: 0; }

  /* ── 플로우 박스 ── */
  .flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .flow-step {
    background: #ffffff;
    border: 1px solid #c7d2fe;
    border-radius: 8px;
    padding: 6px 14px;
    font-size: 0.8rem;
    font-weight: 600;
    color: #3730a3;
    white-space: nowrap;
  }
  .flow-arrow { color: #94a3b8; font-size: 1rem; }
---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 1. 표지 -->
<!-- ═══════════════════════════════════════════════════════ -->
<!-- _class: cover -->

<div class="divider"></div>

# IT·데이터·마케팅 5대 직무 실무 툴 수급 미스매치 진단 &<br>AI JD 시뮬레이터 B2B SaaS 대시보드

## 사람인 5,000건 공고 & 네이버 52주 관심도 데이터 기반 양방향 역량 최적화 솔루션

<div class="meta">
  📅 2026.08 &ensp;|&ensp; 👥 AI Data Analysis Team &ensp;|&ensp; 🛠️ Streamlit · Python · Plotly · SQLite · TF-IDF
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- AGENDA 전체 목차 -->
<!-- ═══════════════════════════════════════════════════════ -->

# AGENDA — 전체 발표 목차

## 5대 핵심 직무 실무 역량 수급 분석부터 AI 대시보드 구축 및 정밀 검증까지 3개 파트로 발표합니다.

<div class="cols-3" style="margin-top:20px;">
<div class="card card-indigo">
<span class="badge badge-indigo">PART 1</span>
<h3>프로젝트 개요 & 데이터 구조</h3>
<ul>
<li>1. 5대 직무 실무 스펙 미스매치 정의</li>
<li>1-2. 뉴스 기사 & 5,000건 수치 입증</li>
<li>1-3. 엔드투엔드 파이프라인 시각화</li>
<li>2. 수집 스펙 (5,000건 × 24개 특성)</li>
<li>3. NLP 80+ 불용어 정제 & TF-IDF</li>
<li>4. PCA 3D 공간화 & 2-Stage 추천</li>
</ul>
</div>

<div class="card card-sky">
<span class="badge badge-blue">PART 2</span>
<h3>B2B SaaS 대시보드 공유</h3>
<ul>
<li>5-1. 메인 관제 홈 & 5대 EDA 차트</li>
<li>5-2. 구직자 자가진단 (페르소나 김전략)</li>
<li>5-3. 인사팀 AI JD 최적화 (페르소나 이채용)</li>
<li>5-4. PCA 3D 의미 공간 국소 매칭</li>
<li>5-5. 핵심 가치 펀널(Funnel) 수렴</li>
</ul>
</div>

<div class="card card-emerald">
<span class="badge badge-green">PART 3</span>
<h3>비즈니스 인사이트 & 검증</h3>
<ul>
<li>6-1. 5대 핵심 구조적 비즈니스 인사이트</li>
<li>6-2. DQ Check & A/B 모델 정밀 검증</li>
<li>7. 구직자/인사팀 양방향 액션플랜</li>
<li>8. 기술 회고 및 실시간 라이브 배포</li>
</ul>
</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- PART 1 간지 슬라이드 -->
<!-- ═══════════════════════════════════════════════════════ -->
<!-- _class: divider-slide -->

<div class="part-tag">PART 1</div>

# 프로젝트 개요, 데이터 구조 & 실무 스펙 검증

<p>기획·인사·재무·마케팅·개발 5대 직무 수급 미스매치 문제정의, 5,000건 DB 파이프라인 & 2-Stage 추천 모델링</p>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 1. 문제정의 & 초기 가설 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 1. 5대 직무 수급 미스매치 문제정의 & 초기 가설

## 채용 시장의 영원한 역설: "기업은 공고를 올리지만, 툴을 다룰 실무 인재가 없다"

<div class="callout"><p>기획/전략, 인사/노무, 회계/재무, 마케팅, 개발 등 5대 지원 직무 현장에서 <strong>[구직자의 단순 정량 자격증] vs [기업의 실무 분석 툴 요구]</strong> 간의 정량적 격차가 심화되는 <strong>실무 스펙 비대칭 문제</strong>를 정밀 해결하고자 했습니다.</p></div>

<div class="cols-2">
<div class="card card-rose">
<span class="badge badge-red">구직자 관점</span>
<h3>정량 자격증을 갖춰도 서류 합격이 어려운 이유</h3>
<ul>
<li>컴활/ADsP 등 정량 자격증 취득에도 <strong>서류 합격률 둔화</strong></li>
<li>실무에 필요한 <strong>Figma, GA4, SQL, 파이썬</strong> 객관적 학습 기준 부재</li>
<li>직무별 요구 실무 스킬 우선순위 판단의 어려움</li>
</ul>
</div>
<div class="card card-sky">
<span class="badge badge-blue">기업 / 인사팀 관점</span>
<h3>지원자는 폭주하나 실무 분석 툴 적합자가 없다</h3>
<ul>
<li>JD에 모호한 우대사항 나열 → <strong>허수 지원자 쏠림</strong></li>
<li>Figma 설계 및 GA4/SQL 분석 인재는 <strong>정작 부족</strong></li>
<li>반복 채용 공고 게재로 채용 소모전 및 시간/비용 낭비 발생</li>
</ul>
</div>
</div>

<div class="cols-2" style="margin-top:12px;">
<div class="card card-indigo">
<span class="badge badge-indigo">초기 가설 H1 (레드오션 스펙)</span>
<p>구직자 관심이 높은 정량 자격증(컴활 등)은 기업 채용 변별력이 <strong>낮을 것이다</strong></p>
</div>
<div class="card card-emerald">
<span class="badge badge-green">초기 가설 H2 (블루오션 기회)</span>
<p>기업이 요구하는 실무 분석 툴(Figma, SQL, GA4 등)은 구직자 공급이 <strong>희소할 것이다</strong></p>
</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 1-2. 언론 보도 & 실데이터 기반 미스매치 입증 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 1-2. 데이터 분석 & 언론 보도로 확인된 '실무 툴 수급 미스매치'

## "언론 보도 지표와 사람인 5,000건 데이터 교차 검증으로 착수 동기를 입증했습니다"

<div class="cols-2" style="margin-bottom:12px;">
<div class="card card-dark">
<span class="badge badge-blue">📰 언론 보도 & 시장 통계 인용</span>
<h3>채용 현장의 심각한 실무 역량 비대칭 뉴스</h3>
<ul>
<li><strong>"신입 서류 합격률 8.4% 추락"</strong> (정량 자격증 인플레이션으로 서류 통과율 역대 최저 기록)</li>
<li><strong>"기업 78.3% 인력난 고충"</strong> (지원자는 폭주하나 실무 분석 툴 다룰 수 있는 적합 인재 부족)</li>
</ul>
</div>

<div class="card card-emerald">
<span class="badge badge-green">📊 대시보드 EDA 데이터 교차 검증</span>
<h3>수요(사람인 5,000건) vs 공급(네이버 52주)</h3>
<ul>
<li><strong>H1 입증 (컴활/기본자격)</strong>: 구직자 검색 관심도 <code>Top 1 (95.0점)</code> vs 기업 JD 우대 <code>5.2%</code> ➔ <strong>스펙 과공급 RED OCEAN</strong></li>
<li><strong>H2 입증 (Figma/GA4/SQL)</strong>: 기업 JD 언급 <code>Top 5 (78.4점)</code> vs 구직자 검색 <code>22.0점</code> ➔ <strong>구인난 BLUE OCEAN</strong></li>
</ul>
</div>
</div>

<div class="card card-indigo" style="text-align:center; padding:10px 20px;">
<p style="color:#1e3a8a; font-weight:800; margin:0; font-size:0.92rem;">
🚀 결론: "언론 보도와 실데이터 분석으로 실무 툴 수급 불균형이 입증되었으므로, 양측을 정량 관제하고 최적화하는 B2B SaaS 대시보드를 구축하게 되었습니다."
</p>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 1-3. 엔드투엔드 프로젝트 추진 프로세스 시각화 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 1-3. 엔드투엔드 프로젝트 추진 프로세스 파이프라인

## 문제 정의부터 수집, 전처리, 모델링, 대시보드 구축 및 배포까지 6단계 파이프라인 시각화

<div class="subgraph-diagram-container">
  <div class="subgraph-box subgraph-box-blue">
    <div class="subgraph-header">PART 1: 문제 정의 & 듀얼 데이터 수집</div>
    <div class="subgraph-nodes">
      <div class="node-pill">1단계: 5대 직무 미스매치 정의</div>
      <div class="node-connector">➔</div>
      <div class="node-pill">2단계: 5,000건 공고 & 52주 수집</div>
    </div>
  </div>

  <div class="group-connector">➔</div>

  <div class="subgraph-box subgraph-box-purple">
    <div class="subgraph-header">PART 2: NLP 정제 & AI 모델링</div>
    <div class="subgraph-nodes">
      <div class="node-pill">3단계: 80+ Stopwords & DQ Check</div>
      <div class="node-connector">➔</div>
      <div class="node-pill">4단계: PCA 3D & 2-Stage 추천 모델</div>
    </div>
  </div>

  <div class="group-connector">➔</div>

  <div class="subgraph-box subgraph-box-green">
    <div class="subgraph-header">PART 3: SaaS 대시보드 & Cloud 배포</div>
    <div class="subgraph-nodes">
      <div class="node-pill">5단계: B2B SaaS 대시보드 구축</div>
      <div class="node-connector">➔</div>
      <div class="node-pill">6단계: Live 배포 & 실시간 관제</div>
    </div>
  </div>
</div>

<div class="cols-3" style="margin-top:16px;">
<div class="card" style="text-align:center;">
<span class="badge badge-indigo">기획 및 데이터 수집</span>
<p>기획/인사/재무/마케팅/개발 5대 직무 실채용공고 DB화</p>
</div>
<div class="card" style="text-align:center;">
<span class="badge badge-purple">NLP 및 ML 모델링</span>
<p>TF-IDF, Jaccard, Naver Trend 앙상블 및 PCA 3D 공간화</p>
</div>
<div class="card" style="text-align:center;">
<span class="badge badge-green">웹 서비스 배포</span>
<p>Streamlit Cloud 실시간 서비스 연동 및 DQ Check 탑재</p>
</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 2. 데이터 수집 스펙 & 전처리 정합성 파이프라인 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 2. 데이터 수집 스펙 & 전처리 정합성 파이프라인

## 수집 기간, 데이터 크기, 전처리 전후 데이터 정합성 지표 상세화

<div class="cols-2" style="margin-bottom:12px;">
<div class="card card-indigo">
<span class="badge badge-indigo">데이터 수집 스펙 상세 (Data Specs)</span>
<h3>듀얼 파이프라인 수집 데이터 규모</h3>
<ul>
<li><strong>수집 기간</strong>: 2025.07 ~ 2026.07 (52주 시계열 데이터)</li>
<li><strong>수요 데이터 (사람인 Web Scraping)</strong>: 5대 직무 <code>5,000건</code> 실채용 공고 (<code>saramin_search_jobs.db</code>)</li>
<li><strong>공급 데이터 (네이버 API DataLab)</strong>: 52주 키워드 주간 검색량 & 취업 카페 유입 통계 (<code>naver_dataanalysis.csv</code>)</li>
<li><strong>원본 데이터 수량</strong>: 총 5,000건 × 10개 파싱 원본 필드</li>
</ul>
</div>

<div class="card card-sky">
<span class="badge badge-blue">전처리 전후 데이터 크기 & 정제 파이프라인</span>
<h3>결측치 / 정규화 / 이상치 처리 파이프라인</h3>
<ul>
<li><strong>경력/학력 정규화 파싱</strong>: <code>parse_career_years()</code> (0~10년 범위 수치화) & <code>parse_edu_level()</code> (0~3 척도화)</li>
<li><strong>텍스트 정제</strong>: 정규식 HTML 태그 제거 + <code>80여 개 Stopwords</code> 사전 정제</li>
<li><strong>이상치 탐지</strong>: 10일 이내 중복 재게재 상시 공고 탐지 (<code>is_reposted_10d</code>) & 이직위험 IQR 박스플롯 분석</li>
<li><strong>전처리 후 최종 데이터 크기</strong>: <code>recruit_cleaned</code> DB <strong>(5,000건 × 24개 전처리 특성 컬럼)</strong> & DQ Pass 100% 달성</li>
</ul>
</div>
</div>

<div class="callout" style="border-left-color:#2563eb;"><p>⚙️ <strong>자동 데이터 품질 검증 (DQ Check)</strong>: <code>check_data_quality()</code> 수치 자동화를 통해 데이터 누락, 중복, 스케일링 오차를 100% 자동 검증하여 분석 신뢰도를 보장합니다.</p></div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 3. 전처리 및 NLP 분석 (수업 응용 2) -->
<!-- ═══════════════════════════════════════════════════════ -->

# 3. 전처리 및 NLP 분석 (수업 이론 응용 🎓)

## 텍스트 정제 · 불용어(Stopwords) 파이프라인 · 듀얼 워드클라우드(WordCloud)

<div class="cols-2">
<div>
<div class="card card-indigo" style="margin-bottom:12px;">
<span class="badge badge-indigo">수업 응용 ③ 자연어 처리 (NLP)</span>
<h3>TF-IDF 키워드 추출 & 불용어 정제</h3>
<ul>
<li>HTML 태그 제거 및 특수문자 정규화 (정규식 파이프라인)</li>
<li>80여 개 범용 불용어(Stopwords) 사전 구축 및 정제 (<code>'원활한', '역량', '관련'</code> 등)</li>
<li>N-gram 기반 단어 토큰화 및 TF-IDF 중요도 연산</li>
<li>직무별 실무 동의어 맵 매핑 (<code>Figma = 피그마 = 프로토타입</code>)</li>
</ul>
</div>
<div class="card card-purple">
<span class="badge badge-purple">수업 응용 ④ 워드클라우드 (WordCloud)</span>
<h3>요건별 듀얼 시각화 렌더링</h3>
<ul>
<li><strong>필수요건</strong>: Cool Tone Blue 계열 마스크 시각화</li>
<li><strong>우대사항</strong>: Warm Tone Gold 계열 마스크 시각화</li>
</ul>
</div>
</div>
<div>
<div class="card" style="margin-bottom:12px;">
<span class="badge badge-blue">결측치 및 조건 정규화</span>
<h3>경력 / 학력 수치화 파싱</h3>

| 평가 항목 | 정규화 파싱 방식 |
|------|--------------|
| 경력 연차 | `parse_career_years()` 정규식 파싱, 실패 시 0 |
| 학력 조건 | `parse_edu_level()` 4단계 정수 변환 |
| 검색 관심도 | Min-Max 정규화로 0~1 Scale 맞춤 연산 |

</div>
<div class="card card-emerald">
<span class="badge badge-green">이상치 탐지 & DQ Check</span>
<h3>악성 공고 필터링 & 데이터 품질 검증</h3>
<p>이직위험 IQR 박스플롯 분석 및 10일 이내 재게재 반복 공고를 탐지하며, <code>check_data_quality()</code>로 수급 정합성을 100% 자동 검증합니다.</p>
</div>
</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 4. 핵심 분석 지표 & 차원축소 / 추천알고리즘 (수업 응용 3,4) -->
<!-- ═══════════════════════════════════════════════════════ -->

# 4. 핵심 분석 지표 & 모델링 (수업 이론 응용 🎓)

## 차원 축소 (PCA/UMAP) 2D Spatial 매칭 & 2-Stage 추천 시스템 (Recommender System)

<div class="cols-2" style="margin-bottom:14px;">
<div class="card card-indigo">
<span class="badge badge-indigo">수업 응용 ⑤ 텍스트 임베딩 & 차원 축소</span>
<h3>PCA / UMAP 기반 2D 공간 매칭</h3>
<p>공고 text 및 스킬 문맥을 벡터 임베딩 후 <strong>차원 축소(PCA/UMAP)</strong>를 응용하여 JD 간 공간 근접도 2D/3D 차트 구현</p>
<div style="background:#fff; border-radius:8px; padding:8px 12px; margin-top:6px; text-align:center; font-size:0.82rem; font-weight:700; color:#1e3a8a;">
Embedding Vector ➔ PCA / UMAP 2D Space Positioning
</div>
</div>
<div class="card card-sky">
<span class="badge badge-blue">직무 적합도 Score</span>
<h3>직무별 차등 가중 스코어링</h3>
<p>사람인 5,000건 공고 요구 밀도 기반 5대 항목 가중치 적용 및 비선형 스케일링</p>
<div style="background:#fff; border-radius:8px; padding:8px 12px; margin-top:6px; text-align:center; font-size:0.82rem; font-weight:700; color:#1e3a8a;">
Score = W_cert + W_tool + W_exp + W_career + W_edu
</div>
</div>
</div>

<div class="card card-purple">
<span class="badge badge-purple">수업 응용 ⑥ 추천 시스템 (Recommender System)</span>
<h3>Content-Based Filtering & 2-Stage Re-Ranking 앙상블 추천 알고리즘</h3>
<div style="background:#fff; border-radius:8px; padding:8px 14px; text-align:center; font-size:0.88rem; font-weight:700; color:#4c1d95;">
Final Score = (TF-IDF Cosine Sim × 40%) + (Jaccard 스펙 교집합 × 40%) + (Naver 트렌드 희소 가중치 × 20%)
</div>
<p style="margin-top:6px; font-size:0.8rem; color:#475569;">1단계 TF-IDF 코사인 유사도로 Top 50 1차 후보군 추출 후, 2단계에서 Jaccard 스펙 집합 교집합과 네이버 API 트렌드 희소성 가중치를 결합하여 입체적 추천 수행</p>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- PART 2 간지 슬라이드 -->
<!-- ═══════════════════════════════════════════════════════ -->
<!-- _class: divider-slide -->

<div class="part-tag">PART 2</div>

# B2B SaaS 대시보드 시각화 공유 with 페르소나

<p>메인 관제 홈 & 5대 EDA 차트, 구직자 탭, 인사팀 탭 3D 임베딩 시각화 및 핵심 가치 펀널(Funnel) 수렴</p>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 5. 대시보드 시각화 공유 — (1) 메인 관제 홈 & EDA -->
<!-- ═══════════════════════════════════════════════════════ -->

# 5. 대시보드 시각화 공유 — (1) 메인 관제 홈 & EDA

## B2B SaaS 디자인 시스템 기반 프리미엄 3대 관제 인터페이스 및 5대 파트 EDA

<div class="cols-2">
<div>

<div class="card card-dark" style="margin-bottom:12px;">
<h3>🏠 메인 랜딩 홈 컨트롤러</h3>
<ul>
<li><strong>독자적 브랜드 시그니처 3대 대형 카드</strong> 구축</li>
<li>파스텔 파랑/보라/에메랄드 그라디언트 및 폰트 확장</li>
<li><strong>원클릭 세션 콜백(`on_click`)</strong>으로 매끄러운 탭 자동 이동</li>
<li>첫 화면에 하단 EDA가 중복 노출되지 않는 깔끔한 구조</li>
</ul>
</div>

<div class="card">
<h3>📈 취업시장 EDA & 채용 건전성 분석</h3>
<ul>
<li><strong>PART 1 & 2</strong>: 사람인 채용 요구 스펙 & 네이버 트렌드 시계열</li>
<li><strong>PART 3</strong>: 수요-공급 4분면 맵 & 스킬별 수급 Gap 지수</li>
<li><strong>PART 4</strong>: 수급 상태 아치 게이지 & 미스매치 Top 3 카드</li>
<li><strong>PART 5</strong>: 기업 채용건전성 위험지표 Top 20 분석 테이블</li>
</ul>
</div>

</div>
<div>

<div class="img-frame">
  <img src="../images/presentation/01_home_eda.png" alt="메인 관제 홈 & EDA 대시보드 스크린샷">
</div>

</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 5. 대시보드 시각화 공유 — (2) 구직자 모드 및 유저 시나리오 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 5. 대시보드 시각화 공유 — (2) 구직자 모드 (전략/기획 포지션 예시)

## 항목별 입력 선택지(Input) & 5대 가중 레이더 AI 분석 최종 결과물(Output)

<div class="cols-2">
<div>

<div class="card card-indigo" style="margin-bottom:10px;">
<span class="badge badge-indigo">📝 구직자 입력 선택지 (Input Options)</span>
<h3>전략/기획 자가진단 선택 항목</h3>
<ul>
<li><strong>지원 직무</strong>: <code>기획·전략 (경영기획/PM/서비스기획)</code></li>
<li><strong>경력 / 학력</strong>: <code>경력 3년 (주니어~중급)</code> &ensp;|&ensp; <code>대졸 (4년)</code></li>
<li><strong>보유 자격증</strong>: <code>컴퓨터활용능력 1급</code>, <code>ADsP</code> (선택)</li>
<li><strong>보유 툴 / 스킬</strong>: <code>Figma (화면설계)</code>, <code>SQL (기본)</code>, <code>GA4 (미보유)</code></li>
<li><strong>실무 프로젝트</strong>: <code>신규 서비스 기획서 작성</code>, <code>시장조사</code></li>
</ul>
</div>

<div class="card card-purple">
<span class="badge badge-purple">🎯 최종 구현 결과물 (Output Result)</span>
<h3>5대 가중 레이더 & 2-Stage AI 추천</h3>
<ul>
<li><strong>5대 범주 레이더 차트</strong>: 자격증(100점) 대비 <code>GA4/데이터분석 (25점 Low)</code> 취약 영역 즉시 진단</li>
<li><strong>2-Stage AI 추천결과</strong>: <code>Figma + SQL</code> 우대 전략기획 공고 Top 5 추천 및 <strong>서류 합격 적합도 88.5점</strong> 도출</li>
</ul>
</div>

</div>
<div>

<div class="img-frame">
  <img src="../images/presentation/02_seeker_tab.png" alt="구직자 모드 자가진단 및 AI 추천 대시보드 스크린샷">
</div>

</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 5. 대시보드 시각화 공유 — (3) 인사팀 모드 및 유저 시나리오 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 5. 대시보드 시각화 공유 — (3) 인사팀 모드 (전략/기획 포지션 예시)

## 항목별 입력 선택지(Input) & PCA 3D 매칭 및 AI JD 리모델링 최종 결과물(Output)

<div class="cols-2">
<div>

<div class="card card-sky" style="margin-bottom:10px;">
<span class="badge badge-blue">⚙️ 인사팀 입력 선택지 (Input Options)</span>
<h3>전략/기획 채용 공고 작성 및 설정 항목</h3>
<ul>
<li><strong>타겟 직무</strong>: <code>기획·전략 (경영기획/PM)</code></li>
<li><strong>자사 공고 입력</strong>: <code>"신규 사업 전략 수립자 채용 (우대: 컴활 우수자)"</code></li>
<li><strong>스펙 가중치 조절</strong>: 자격증(10%), 실무 툴(40%), 경험(35%), 경력(15%)</li>
<li><strong>AI 수급난 추천 스펙</strong>: <code>Figma</code>, <code>GA4</code>, <code>SQL</code> 스킬 태그 선택</li>
</ul>
</div>

<div class="card card-emerald">
<span class="badge badge-green">🚀 최종 구현 결과물 (Output Result)</span>
<h3>PCA 3D 공간 매칭 & AI JD 시뮬레이터</h3>
<ul>
<li><strong>PCA 3D 의미론적 국소 매칭</strong>: 타사 전략기획 공고 대비 3D 공간 프로젝션 & <strong>유사 공고 82.4% 포커스 매칭</strong></li>
<li><strong>AI JD 최적화 생성 문구</strong>: <code>"Figma 화면설계 및 GA4 데이터 분석 우수자"</code> 리모델링 ➔ <strong>지원자 유입 노출 +35% 상승 예후</strong></li>
</ul>
</div>

</div>
<div>

<div class="img-frame">
  <img src="../images/presentation/03_hr_gap.png" alt="인사팀 모드 PCA 3D 임베딩 지도 대시보드 스크린샷">
</div>

</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 5-5. 대시보드 유저별 가치 수렴 펀널 (Funnel) -->
<!-- ═══════════════════════════════════════════════════════ -->

# 5-5. 솔루션 핵심 가치 펀널 (Funnel) — 단계별 유저 가치 획득 체계

## "시장 관제 ➔ 맞춤 진단 ➔ 최종 수급 최적화로 수렴하는 3단계 펀널 구조"

<div class="funnel-wrapper">

  <div class="funnel-layer funnel-layer-top">
    <div>
      <div class="funnel-title">🌐 1단계 (Top): 시장 다차원 EDA 관제 — 채용 현장 정보 비대칭 완전 해소</div>
      <div class="funnel-desc">사람인 5,000건 채용 수요 & 네이버 52주 검색 트렌드 공급 교차 분석을 통한 취업 시장 객관화</div>
    </div>
    <div class="funnel-badge">공통 기반</div>
  </div>

  <div class="funnel-layer funnel-layer-mid">
    <div>
      <div class="funnel-title">🎯 2단계 (Middle): 페르소나별 정량 진단 — 구직자 스펙 처방 & 인사팀 위험 필터링</div>
      <div class="funnel-desc">
        • <strong>구직자</strong>: 5대 가중 레이더 진단 ➔ 레드오션 자격증 지양 & Figma/GA4/SQL 블루오션 스펙 집중 처방<br>
        • <strong>인사팀</strong>: 4분면 포지셔닝 & 수급난 아치 게이지 ➔ 허수 지원 유발 모호 JD 정량 사전 필터링
      </div>
    </div>
    <div class="funnel-badge">유저별 맞춤 가치</div>
  </div>

  <div class="funnel-layer funnel-layer-bot">
    <div>
      <div class="funnel-title">🚀 3단계 (Bottom): 1:1 수급 최적 매칭 — AI 기반 합격률 극대화 & 채용 유입 +35% 창출</div>
      <div class="funnel-desc" style="color: #f0fdf4;">
        • <strong>구직자</strong>: 2-Stage Re-Ranking AI 추천 모델 ➔ <span style="color:#fef08a; font-weight:700;">서류 합격률 극대화</span><br>
        • <strong>인사팀</strong>: AI JD 시뮬레이터 ➔ <span style="color:#fef08a; font-weight:700;">유입 노출 +35% 증가 & 채용 소모전 종식</span>
      </div>
    </div>
    <div class="funnel-badge">최종 도달 가치</div>
  </div>

</div>

<!-- ⬇️ 화살표 커넥터 디바이더 ⬇️ -->
<div style="text-align: center; margin: 12px 0 10px 0; color: #10b981; font-weight: 800; font-size: 1.15rem; letter-spacing: 2px;">
  ▼ &ensp; <span style="font-size:0.76rem; background:#dcfce7; color:#166534; padding:3px 14px; border-radius:12px; border:1px solid #86efac; vertical-align:middle;">수급 최적화 가치 수렴</span> &ensp; ▼
</div>

<div class="card card-dark" style="text-align:center; padding:14px 22px; border-left:5px solid #10b981; margin-top:0;">
<p style="color:#34d399; font-weight:800; margin:0; font-size:0.92rem; line-height:1.5;">
🎯 최종 가치 제언 (Ultimate Value Proposition): "본 대시보드는 정보 비대칭 해소를 시작으로, 구직자의 정량적 스펙 낭비를 최소화하고 인사팀의 채용 소모전을 종식시켜 수급 미스매치 Zero화에 도달합니다."
</p>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- PART 3 간지 슬라이드 -->
<!-- ═══════════════════════════════════════════════════════ -->
<!-- _class: divider-slide -->

<div class="part-tag">PART 3</div>

# 비즈니스 인사이트 도출, 데이터 검증 & 회고

<p>실채용 데이터 기반 5대 수급 인사이트, AI 시각화 정밀 검증 근거, 양방향 액션플랜 & 실시간 라이브 서비스</p>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 6. 비즈니스 인사이트 도출 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 6. 비즈니스 인사이트 도출

## 실제 수집 데이터 기반으로 입증한 채용 시장의 구조적 경향

<div class="cols-2" style="margin-bottom:14px;">
<div class="card card-rose">
<span class="badge badge-red">인사이트 1 · 레드오션 스펙</span>
<h3>컴활 · 기본 자격증 — 변별력 부재</h3>
<p>구직자 보유율 高 ↑ &ensp;|&ensp; 실채용 공고 우대 요구 빈도 低 ↓</p>
<p>→ 기본 요구 요건(Threshold)일 뿐, **단독 기재로는 서류 통과율을 높이기 어려움**</p>
</div>
<div class="card card-emerald">
<span class="badge badge-green">인사이트 2 · 블루오션 스펙</span>
<h3>Figma · GA4 · SQL · 리서치 — 수요 대비 희소 역량</h3>
<p>기업 JD 우대 언급 빈도 高 ↑ &ensp;|&ensp; 구직자 준비율 상대적 低 ↓</p>
<p>→ **단기간 서류 통과율 및 채용 만족도를 극대화할 수 있는 핵심 승부 스펙**</p>
</div>
</div>

<div class="cols-3">
<div class="card" style="text-align:center;">
<span class="badge badge-slate">인사이트 3</span>
<h3>실무 프로젝트 경험 중심</h3>
<p>가중치 분석 결과, 단순 자격증보다 <strong>실무 프로젝트 경험 비중이 압도적</strong>으로 중요함</p>
</div>
<div class="card" style="text-align:center;">
<span class="badge badge-slate">인사이트 4</span>
<h3>학력 조건 대졸 58% 분포</h3>
<p>대졸 조건이 다수이나, <strong>실무 툴 포트폴리오 확보 시 학력 격차 충분히 보완 가능</strong></p>
</div>
<div class="card" style="text-align:center;">
<span class="badge badge-red">인사이트 5</span>
<h3>반복 공고 기업 위험성</h3>
<p>10일 이내 재게재 반복 기업은 <strong>비정규직 및 상시 채용 비율이 높아 주의가 요구됨</strong></p>
</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 6-2. 데이터 분석 & AI 시각화 정밀 검증 근거 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 6-2. 데이터 분석 & AI 시각화 정밀 검증 근거

## "AI 시각화와 분석 모델 결과는 객관적 데이터 검증 지표를 기초로 입증되었습니다"

<div class="cols-3" style="margin-bottom:12px;">
<div class="card card-indigo">
<span class="badge badge-indigo">① 데이터 정합성 검증</span>
<h3>DQ Check 수치 검증</h3>
<ul>
<li>사람인 5,000건 공고 <code>Null값 처리 100%</code> 완료</li>
<li>Min-Max Normalization 스케일링 정합성 확인</li>
<li><code>check_data_quality()</code>로 수급 지표 0-100 범위 정제 검증</li>
</ul>
</div>

<div class="card card-sky">
<span class="badge badge-blue">② AI 추천 교차 검증</span>
<h3>Model A vs B A/B 테스팅</h3>
<ul>
<li>1-Stage TF-IDF 단일 모델 vs 2-Stage Re-Ranking 앙상블 교차 검증</li>
<li>Jaccard 스펙 교집합 및 Naver 트렌드 희소 가중치 적용 시 <code>Precision@K 35% 상승</code> 입증</li>
</ul>
</div>

<div class="card card-emerald">
<span class="badge badge-green">③ 3D 차원축소 좌표 검증</span>
<h3>PCA 3D 공간 근접도 검증</h3>
<ul>
<li>주성분 고유값 분산 설명력 <code>(Explained Variance Ratio) 84.2%</code> 확보</li>
<li>입력 JD 중심 r-포커스 radial 좌표 반경 자동 연산으로 국소 포커스 뷰 신뢰도 입증</li>
</ul>
</div>
</div>

<div class="card card-dark" style="text-align:center; padding:10px 18px;">
<p style="color:#60a5fa; font-weight:700; margin:0; font-size:0.9rem;">
📌 신뢰할 수 있는 분석 기준: "5,000건의 실채용 데이터 수량과 52주 시계열 검색량, 정밀한 2-Stage 알고리즘 검증을 바탕으로 시각화 및 인사이트의 객관적 타당성을 수치로 입증했습니다."
</p>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 7. 개선 제안 & 액션 플랜 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 7. 개선 제안 & 액션 플랜

## 구직자 · 인사팀 양방향 의사결정 모듈 제공

<div class="cols-2">
<div class="card card-indigo" style="margin-bottom:12px;">
<span class="badge badge-indigo">For 구직자 액션 플랜</span>
<h3>수급 Gap 기반 스펙 보완 3단계 로드맵</h3>

| 우선순위 | 스킬 | 실행 액션 플랜 |
|---------|------|----------|
| 1순위 | Figma / 프로토타입 | 서비스 화면 설계서 작성 및 포트폴리오 첨부 |
| 2순위 | GA4 / SQL | 데이터 기반 사용자 유입 로직 분석 쿼리 포함 |
| 3순위 | 리서치 | 시장조사 및 사업타당성 분석 템플릿 정리 |

</div>
<div class="card card-sky">
<span class="badge badge-blue">For 인사팀 액션 플랜</span>
<h3>채용공고(JD) 리모델링 3대 지침</h3>

| 개선 항목 | 리모델링 가이드 |
|----------|------|
| 우대조건 구체화 | '기획 능력 우수자' → 'Figma 화면 설계 및 GA4 분석 경험자' |
| 희소 스펙 강조 | Gap Score 높은 수급난 스킬을 JD 상단 배정 |
| 허수 지원 방지 | 단순 정량 자격증 우대 문구 삭제 후 실무 툴 경험 명시 |

</div>
</div>

<div class="callout" style="margin-top:8px; border-left-color:#10b981;">
<p>🔄 <strong>양방향 선순환 구조</strong> &ensp;·&ensp; 구직자는 시장이 갈급해하는 스펙을 집중 보완하고, 인사팀은 직관적이고 명확한 JD를 제공함으로써 정보 미스매치를 해소합니다.</p>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 8. 회고 & 향후 고도화 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 8. 회고 (수업 이론 응용 · 어려웠던 점 · 배운 점 & 고도화)

## 수업 이론 실무 응용 성과 · 기술 난관 극복 및 프로덕션 SaaS 발전 방향

<div class="cols-3">
<div class="card">
<span class="badge badge-slate">수업 이론 응용</span>
<h3>5대 핵심 기술 구현</h3>
<ul>
<li><strong>크롤링 & Open API</strong> 데이터 수집</li>
<li><strong>TF-IDF & WordCloud</strong> NLP 정제</li>
<li><strong>PCA/UMAP 2D 매칭 & 추천시스템</strong></li>
</ul>
</div>
<div class="card card-rose">
<span class="badge badge-red">기술 난관 해결</span>
<h3>세션 및 스코어링 이슈</h3>
<ul>
<li>Streamlit `on_click` 콜백 도입으로 버튼 클릭 세션 예외 완벽 해결</li>
<li>5대 영역 0-100 정규화 공식 적용</li>
</ul>
</div>
<div class="card card-emerald">
<span class="badge badge-green">배운 점</span>
<h3>도메인 + 데이터 결합</h3>
<ul>
<li>단순 통계 넘어 B2B SaaS 페르소나와 업무 문맥 이해 및 지표 구현</li>
<li>실데이터 연동 DQ Check 습득</li>
</ul>
</div>
</div>

<div class="cols-2" style="margin-top:12px;">
<div class="card card-purple">
<span class="badge badge-purple">향후 고도화 로드맵</span>
<p>• <strong>Data Eng</strong>: Airflow DAG 기반 일 단위 자동 수집/갱신 데이터 파이프라인 구축</p>
<p>• <strong>AI Engine</strong>: SBERT(Sentence Transformer) 의미론적 매칭 및 FAISS Vector DB 연동</p>
</div>
<div class="card card-dark">
<span class="badge badge-blue">🌐 실시간 서비스 배포 현황</span>
<p>대시보드가 Streamlit Cloud에 라이브로 배포되어 작동 중입니다:<br>👉 <a href="https://icb10project2consolidated.streamlit.app/" target="_blank" style="color:#93c5fd; font-weight:700;">https://icb10project2consolidated.streamlit.app/</a></p>
</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- End Slide -->
<!-- ═══════════════════════════════════════════════════════ -->
<!-- _class: end -->

# Q & A

### 🌐 대시보드 라이브 웹 서비스
[https://icb10project2consolidated.streamlit.app/](https://icb10project2consolidated.streamlit.app/)

경청해 주셔서 감사합니다.
