---
marp: true
theme: default
size: 16:9
paginate: true
header: '취업 시장 다차원 EDA & 직무 적합도 진단 솔루션'
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
    font-size: 2.8rem;
    font-weight: 800;
    color: #ffffff;
    line-height: 1.25;
    margin: 0 0 16px 0;
  }
  section.cover h2 {
    font-size: 1.25rem;
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

# 취업 시장 다차원 EDA &<br>직무 적합도 진단 솔루션

## B2B SaaS 대시보드 — 채용 수급 미스매치 해소 프로젝트

<div class="meta">
  📅 2026.08 &ensp;|&ensp; 👥 AI Data Analysis Team &ensp;|&ensp; 🛠️ Streamlit · Python · Plotly · SQLite
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 1. 문제정의 & 초기 가설 -->
<!-- ═══════════════════════════════════════════════════════ -->

# 1. 문제정의 & 초기 가설

## 채용 시장의 영원한 역설: "기업은 공고를 올리지만, 쓸 사람이 없다"

<div class="callout"><p>채용 시장 양측 모두 수많은 채용 정보와 이력서를 축적하고 있으나, <strong>[구직자 보유 스펙] vs [기업 요구 역량]</strong> 간의 정량적 격차가 심화되는 <strong>정보 비대칭 문제</strong>를 해결하고자 했습니다.</p></div>

<div class="cols-2">
<div class="card card-rose">
<span class="badge badge-red">구직자 관점</span>
<h3>스펙을 갖춰도 서류 합격이 어려운 이유</h3>
<ul>
<li>자격증 및 어학 성적을 올려도 <strong>서류 합격률 둔화</strong></li>
<li>정확히 어떤 실무 툴을 익혀야 하는지 <strong>객관적 기준 부재</strong></li>
<li>직무별 요구 스킬 우선순위 판단의 어려움</li>
</ul>
</div>
<div class="card card-sky">
<span class="badge badge-blue">기업 / 인사팀 관점</span>
<h3>지원자는 많은데 직무 적합자가 없다</h3>
<ul>
<li>JD에 모호한 우대사항 나열 → <strong>허수 지원자 쏠림</strong></li>
<li>실무에 필요한 핵심 분석 역량자는 <strong>정작 부족</strong></li>
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
<p>기업이 실제로 요구하는 툴/경험(Figma, SQL, GA4 등)은 구직자 공급이 <strong>희소할 것이다</strong></p>
</div>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 1-2. 미스매치 실제 입증 & 착수 동기 (핵심 보완 슬라이드!) -->
<!-- ═══════════════════════════════════════════════════════ -->

# 1-2. 실제 데이터 분석으로 확인된 '수급 미스매치' 현상 & 착수 동기

## "가설 검증 결과, 우리가 정의한 채용 수급 미스매치가 실제로 존재함을 데이터로 입증했습니다!"

<div class="callout" style="border-left-color:#10b981;"><p>🔍 사람인 채용공고 5,000건(수요)과 네이버 API 검색 트렌드(공급)를 교차 분석한 결과, <strong>H1과 H2 가설이 100% 데이터로 확인되어 솔루션 개발에 착수하게 되었습니다.</strong></p></div>

<div class="cols-2">
<div class="card card-rose">
<span class="badge badge-red">가설 H1 실제 검증 ➔ 스펙 과공급 (레드오션)</span>
<h3>구직자 관심도는 폭발적이나 기업 요구는 미미</h3>
<ul>
<li><strong>컴활 / 기본 자격증 / 파이썬 기초</strong>: 구직자 주간 검색 관심도 <code>Top 10 (85~95점)</code> 포함</li>
<li><strong>실제 기업 JD 우대 비율</strong>: 전체 공고의 <code>5% ~ 12% 미만</code>에 불과</li>
<li>💡 <strong>입증 결과</strong>: 단순 스펙 쌓기가 실제 채용 변별력으로 연결되지 않는 <strong>정량 스펙 낭비 현상 증명</strong></li>
</ul>
</div>

<div class="card card-emerald">
<span class="badge badge-green">가설 H2 실제 검증 ➔ 스펙 구인난 (블루오션)</span>
<h3>기업 채용 수요는 극대화되나 구직자 준비는 부족</h3>
<ul>
<li><strong>Figma / GA4 / SQL / 리서치 / A/B테스트</strong>: 기업 JD 실무 우대 언급 <code>Top 5 (65~88점)</code> 차지</li>
<li><strong>구직자 주간 검색 관심도</strong>: <code>15% ~ 30% 수준</code>으로 현저히 저조</li>
<li>💡 <strong>입증 결과</strong>: 기업이 갈급해하는 핵심 실무 역량의 <strong>심각한 수급 불균형(Mismatch) 증명</strong></li>
</ul>
</div>
</div>

<div class="card card-dark" style="margin-top:12px; text-align:center; padding:12px 20px;">
<p style="color:#60a5fa; font-weight:700; margin:0; font-size:0.92rem;">
🚀 프로젝트 추진 결론: "수급 미스매치 엄존이 정량 데이터로 입증되었으므로, 이를 실시간 관제하고 양측에 명확한 솔루션을 제공하는 B2B SaaS 대시보드를 구축하게 되었습니다."
</p>
</div>

---

<!-- ═══════════════════════════════════════════════════════ -->
<!-- 2. 데이터 구조 및 수집 기법 (수업 응용 1) -->
<!-- ═══════════════════════════════════════════════════════ -->

# 2. 데이터 구조 및 수집 기법 (수업 이론 응용 🎓)

## 크롤링(Crawling) & 오픈 API(Open API) 연동을 통한 채용 수요-공급 듀얼 파이프라인

<div class="cols-3" style="margin-bottom:14px;">
<div class="card card-indigo">
<span class="badge badge-indigo">수업 응용 ① 웹 크롤링</span>
<h3>사람인 실채용 공고 수집</h3>
<p><code>saramin_search_jobs.db</code></p>
<ul>
<li><strong>BeautifulSoup4 & Requests</strong> 응용</li>
<li>실채용공고 <strong>5,000건</strong> 웹 크롤링 파싱</li>
<li>필수·우대 스킬, 학력, 경력, 마감일 DB화</li>
</ul>
</div>
<div class="card card-sky">
<span class="badge badge-blue">수업 응용 ② 네이버 Open API</span>
<h3>네이버 DataLab & 카페 연동</h3>
<p><code>naver_weekly_insights.json</code></p>
<ul>
<li><strong>REST API HTTP 연동 & JSON 파싱</strong></li>
<li>DataLab 주간 스킬 검색 트렌드 시계열</li>
<li>취업 카페 게시글 유입량 키워드 수급 연산</li>
</ul>
</div>
<div class="card card-emerald">
<span class="badge badge-green">데이터 결합</span>
<h3>수급 Gap 데이터마트</h3>
<p><code>automated_total_mismatch_mart.csv</code></p>
<ul>
<li>Demand Score (기업 채용 수요)</li>
<li>Supply Score (구직자 주간 관심)</li>
<li><strong>Gap Score (수요-공급 차이)</strong> 산출</li>
</ul>
</div>
</div>

<div class="cols-2">
<div class="card">
<h3>5대 전체 지원 직무</h3>
<div class="flow" style="margin-top:8px;">
<span class="flow-step">기획/전략</span>
<span class="flow-arrow">·</span>
<span class="flow-step">인사/노무</span>
<span class="flow-arrow">·</span>
<span class="flow-step">회계/재무</span>
<span class="flow-arrow">·</span>
<span class="flow-step">마케팅</span>
<span class="flow-arrow">·</span>
<span class="flow-step">개발</span>
</div>
<p style="margin-top:10px; font-size:0.82rem; color:#64748b;">사이드바 마스터 컨트롤러를 통해 직무 전환 시 대시보드 전체 데이터 동적 연동</p>
</div>
<div class="card card-dark">
<h3>핵심 기술 스택</h3>
<ul>
<li><strong>Streamlit</strong>: B2B SaaS 멀티 탭/모드 반응형 웹 인터페이스</li>
<li><strong>Plotly</strong>: 수급 4분면 맵, 오각형 레이더 차트, 수급 아치 게이지</li>
<li><strong>TF-IDF & Jaccard</strong>: 2-Stage Re-Ranking 추천 모델</li>
<li><strong>SQLite</strong>: DB 정합성 100% 실시간 연동</li>
</ul>
</div>
</div>

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

# 5. 대시보드 시각화 공유 — (2) 구직자 모드 및 유저 예시

## 스펙 자가진단 & 2-Stage AI 추천 (유저 시나리오 예시: 취준생 '김전략' 님)

<div class="cols-2">
<div>

<div class="card card-purple" style="margin-bottom:10px;">
<span class="badge badge-purple">유저 시나리오 예시</span>
<h3>👤 취준생 '김전략' 님의 고민</h3>
<ul>
<li>"남들이 다 따는 컴활/ADsP 자격증을 얻었으나 <strong>서류 합격률이 10% 미만</strong>입니다."</li>
<li>"어떤 실무 툴을 준비해야 할지 <strong>우선순위를 정하지 못해 불안</strong>합니다."</li>
</ul>
</div>

<div class="card card-indigo">
<span class="badge badge-indigo">구직자 모드 탭 핵심</span>
<h3>📝 자가진단 & 2-Stage AI 추천</h3>
<ul>
<li>경력·학력·자격증·툴·경험 5대 영역 가중 스코어링</li>
<li><strong>5대 범주 오각형 레이더 차트 (`fig_radar`)</strong></li>
<li><strong>Model A vs B 추천 알고리즘 A/B 테스트</strong></li>
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

# 5. 대시보드 시각화 공유 — (3) 인사팀 모드 및 유저 예시

## 수급 Gap 분석 & AI JD 시뮬레이터 (유저 시나리오 예시: 인사팀장 '이채용' 님)

<div class="cols-2">
<div>

<div class="card card-rose" style="margin-bottom:10px;">
<span class="badge badge-red">유저 시나리오 예시</span>
<h3>👤 인사팀장 '이채용' 님의 고민</h3>
<ul>
<li>"공고를 올려도 모호한 우대조건으로 <strong>허수 지원자만 많고 실무형 인재가 안 옵니다.</strong>"</li>
<li>"어느 조건을 교체해야 유입이 늘어나는지 <strong>지표가 없습니다.</strong>"</li>
</ul>
</div>

<div class="card card-sky">
<span class="badge badge-blue">인사팀 모드 탭 핵심</span>
<h3>⚖️ 3D 임베딩 매칭 & AI JD 시뮬레이터</h3>
<ul>
<li><strong>PCA 3D 의미론적 국소 매칭</strong>: 유사 공고 3D 근접도 포커스 뷰</li>
<li><strong>수급난 추천 스펙 일괄 연동</strong>: 지원자 유입 노출 <strong>+35% 상승 예측 JD 문구 생성</strong></li>
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
