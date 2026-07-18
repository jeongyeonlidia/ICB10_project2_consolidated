"""
취업 시장 실데이터 분석 대시보드

2탭 구조:
- 탭 1. 시장 데이터 EDA: 사람인 실채용공고 EDA + 네이버 취업준비 콘텐츠 EDA
- 탭 2. 시장 비교 · 스펙 진단: 기업수요 vs 구직자관심 GAP 분석 + 실공고 기반 구직자 스펙 진단

원칙:
- mock/임시/랜덤 데이터를 사용하지 않습니다. 모든 수치는 아래 실제 파일에서 직접 계산됩니다.
    - data/keyword_extraction_result_v2.json   : 직무별(acc/dev/hr/mkt/plan) 기업 요구 스킬·자격증 + 가중TF-IDF 스코어
    - data/recruit_processed.db (recruit_cleaned) : acc/dev/hr/mkt 실채용공고 각 1,000건
    - data/saramin_search_jobs.db (saramin_jobs)  : plan(기획/전략) 실채용공고 1,000건
    - data/naver_api/it_data/processed/*.csv      : dev(IT개발·데이터) 네이버 취업준비 콘텐츠 실데이터
- 실데이터가 없는 직무(감사/컴플라이언스)·구간(월별 시계열)은 화면에서 제외하거나 "데이터 없음"으로 표시합니다.
- automated_total_mismatch_mart.csv는 과거 mock 딕셔너리를 그대로 CSV로 내보낸 파일로 확인되어 사용하지 않습니다.
  대신 build_gap_table()이 사람인+네이버 실데이터를 실행 시점에 병합해 GAP 테이블을 직접 생성합니다.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import json
import os
import plotly.graph_objects as go

# =====================================================================
# 페이지 기본 설정
# =====================================================================
st.set_page_config(
    page_title="취업 시장 실데이터 분석 대시보드",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# 1. 직무 <-> 데이터 코드 매핑
# =====================================================================
# keyword_extraction_result_v2.json / recruit_processed.db의 job_category 코드
JOB_CODE_MAP = {
    "기획/전략": "plan",
    "인사/노무": "hr",
    "회계/재무": "acc",
    "마케팅": "mkt",
    "데이터분석가/AI엔지니어": "dev",
}
# 감사/컴플라이언스는 어떤 실데이터에도 없어 목록에서 제외 (요청사항: 실데이터 있는 직무만 표시)
AVAILABLE_JOBS = list(JOB_CODE_MAP.keys())

# 네이버 취업 준비 콘텐츠 실데이터가 존재하는 직무 -> 데이터 폴더명
NAVER_JOB_DIR = {"dev": "it_data"}


# =====================================================================
# 2. 데이터 로더 (전부 실제 파일/DB만 읽음)
# =====================================================================
@st.cache_data
def load_company_keywords(job_code):
    """직무별 기업 요구 스킬/자격증 + 가중 TF-IDF 스코어 (keyword_extraction_result_v2.json)."""
    paths = ["data/keyword_extraction_result_v2.json", "../data/keyword_extraction_result_v2.json"]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    raw = json.load(f)
                groups = raw.get("results", {}).get(job_code, {}).get("keyword_groups", [])
                if not groups:
                    return None, None
                rows = [{
                    "representative_keyword": g["representative_keyword"],
                    "type": g["type"],
                    "frequency_score": g["frequency_score"],
                    "search_group": g.get("search_group", [g["representative_keyword"]]),
                } for g in groups]
                return pd.DataFrame(rows), p
            except Exception:
                pass
    return None, None


@st.cache_data
def load_recruit_postings(job_code):
    """직무별 실제 채용공고. plan은 saramin_search_jobs.db, 그 외는 recruit_processed.db.
    공통 컬럼(company/title/career/education/full_text)으로 매핑해 반환."""
    if job_code == "plan":
        paths = ["data/saramin_search_jobs.db", "../data/saramin_search_jobs.db"]
        for p in paths:
            if os.path.exists(p):
                try:
                    conn = sqlite3.connect(p)
                    df = pd.read_sql("SELECT * FROM saramin_jobs", conn)
                    conn.close()
                    df["full_text"] = (
                        df["title"].fillna("") + " " + df["sectors"].fillna("") + " " + df["detail_content"].fillna("")
                    ).str.lower()
                    return df[["company", "title", "career", "education", "full_text"]], p
                except Exception:
                    pass
        return None, None
    else:
        paths = ["data/recruit_processed.db", "../data/recruit_processed.db"]
        for p in paths:
            if os.path.exists(p):
                try:
                    conn = sqlite3.connect(p)
                    df = pd.read_sql(
                        "SELECT * FROM recruit_cleaned WHERE job_category = ?", conn, params=(job_code,)
                    )
                    conn.close()
                    if df.empty:
                        return None, None
                    df["full_text"] = (
                        df["title"].fillna("") + " " +
                        df["required_keywords"].fillna("") + " " +
                        df["preferred_keywords"].fillna("") + " " +
                        df["preferred_certificates"].fillna("") + " " +
                        df["cleaned_requirement"].fillna("") + " " +
                        df["cleaned_preferential"].fillna("")
                    ).str.lower()
                    df = df.rename(columns={
                        "company_name": "company",
                        "education_level": "education",
                        "experience_level": "career",
                    })
                    return df[["company", "title", "career", "education", "full_text"]], p
                except Exception:
                    pass
        return None, None


@st.cache_data
def load_naver_keyword_summary(job_code):
    """직무별 네이버 취업 준비 콘텐츠 키워드 집계 (keyword_content_summary.csv)."""
    subdir = NAVER_JOB_DIR.get(job_code)
    if not subdir:
        return None, None
    paths = [
        f"data/naver_api/{subdir}/processed/keyword_content_summary.csv",
        f"../data/naver_api/{subdir}/processed/keyword_content_summary.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p, encoding="utf-8-sig"), p
            except Exception:
                pass
    return None, None


@st.cache_data
def load_naver_content_sample(job_code):
    """직무별 네이버 취업 준비 콘텐츠 원문 (건수/소스 breakdown용)."""
    subdir = NAVER_JOB_DIR.get(job_code)
    if not subdir:
        return None, None
    paths = [
        f"data/naver_api/{subdir}/processed/it_job_related_content.csv",
        f"../data/naver_api/{subdir}/processed/it_job_related_content.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p, encoding="utf-8-sig"), p
            except Exception:
                pass
    return None, None


# =====================================================================
# 3. Build 함수 (실데이터를 실행 시점에 병합/계산 - mock CSV 대체)
# =====================================================================
def build_gap_table(df_company, df_jobseeker):
    """사람인(기업 요구) + 네이버(구직자 관심) 공통 키워드를 skills/certifications 그룹별
    0~100 min-max 정규화해 병합. automated_total_mismatch_mart.csv 없이 실행 시 직접 생성."""
    if df_company is None or df_jobseeker is None:
        return None

    merged = pd.merge(
        df_company[["representative_keyword", "type", "frequency_score"]],
        df_jobseeker[["representative_keyword", "unique_document_count",
                      "blog_document_count", "cafe_document_count", "kin_document_count"]],
        on="representative_keyword", how="inner"
    ).rename(columns={"frequency_score": "company_demand_raw", "unique_document_count": "jobseeker_content_raw"})

    if merged.empty:
        return None

    def minmax_by_type(df, col, out_col):
        result = df.copy()
        for t in result["type"].unique():
            mask = result["type"] == t
            vmin, vmax = result.loc[mask, col].min(), result.loc[mask, col].max()
            result.loc[mask, out_col] = 50.0 if vmax == vmin else (result.loc[mask, col] - vmin) / (vmax - vmin) * 100
        return result

    merged = minmax_by_type(merged, "company_demand_raw", "company_demand_score")
    merged = minmax_by_type(merged, "jobseeker_content_raw", "jobseeker_content_score")
    merged["gap_score"] = merged["company_demand_score"] - merged["jobseeker_content_score"]
    return merged


def compute_skill_appearance_rates(df_company, df_postings):
    """스킬/자격증별로 실제 채용공고 텍스트(search_group 동의어 매칭)에 등장하는 비율을 계산.
    LLM/임의 추천 없이 순수 텍스트 매칭 카운트만 사용."""
    if df_company is None or df_postings is None or df_postings.empty:
        return None
    total = len(df_postings)
    texts = df_postings["full_text"].tolist()
    rows = []
    for _, g in df_company.iterrows():
        sg = g["search_group"]
        synonyms = [str(s).lower() for s in sg] if isinstance(sg, list) else [str(sg).lower()]
        cnt = sum(1 for t in texts if any(s in t for s in synonyms))
        rows.append({
            "representative_keyword": g["representative_keyword"],
            "type": g["type"],
            "frequency_score": g["frequency_score"],
            "posting_count": cnt,
            "appearance_rate": round(cnt / total * 100, 1) if total else 0.0,
        })
    return pd.DataFrame(rows).sort_values("frequency_score", ascending=False).reset_index(drop=True)


# =====================================================================
# 4. 사이드바: 직무 선택 (실데이터가 있는 직무만 노출)
# =====================================================================
st.sidebar.title("🎛️ 컨트롤 패널")
selected_job = st.sidebar.selectbox(
    "📋 분석할 직무를 선택하세요",
    AVAILABLE_JOBS,
    index=AVAILABLE_JOBS.index("데이터분석가/AI엔지니어"),
    help="실제 채용공고/키워드 실데이터가 존재하는 직무만 표시됩니다 (감사/컴플라이언스는 실데이터 없어 제외)."
)
job_code = JOB_CODE_MAP[selected_job]

# 현재 선택된 직무의 실데이터 로드
df_company, company_path = load_company_keywords(job_code)
df_postings, postings_path = load_recruit_postings(job_code)
df_jobseeker, jobseeker_path = load_naver_keyword_summary(job_code)
df_content, content_path = load_naver_content_sample(job_code)
df_gap = build_gap_table(df_company, df_jobseeker)

st.sidebar.write("---")
st.sidebar.subheader("📡 데이터 소스 현황")
if company_path:
    st.sidebar.success(f"✅ 기업 요구 키워드: {company_path}")
else:
    st.sidebar.warning("⚠️ 기업 요구 키워드 데이터 없음")

if postings_path:
    st.sidebar.success(f"✅ 실채용공고: {postings_path} ({len(df_postings):,}건)")
else:
    st.sidebar.warning("⚠️ 실채용공고 데이터 없음")

if jobseeker_path:
    st.sidebar.success(f"✅ 네이버 취업준비 콘텐츠: {jobseeker_path}")
else:
    st.sidebar.warning("⚠️ 네이버 실데이터 없음 (현재 데이터분석가/AI엔지니어만 연동)")
st.sidebar.caption("⚠️ 월별 검색비율 시계열 실데이터는 프로젝트 내에 존재하지 않아 시계열 분석은 제공하지 않습니다.")


# =====================================================================
# 5. 메인 타이틀 및 탭
# =====================================================================
st.title("📊 취업 시장 실데이터 분석 대시보드")
st.markdown(f"**현재 분석 직무**: `{selected_job}` | 실제 파일/DB에서 계산된 값만 표시합니다.")
st.write("---")

tab1, tab2 = st.tabs(["📈 시장 데이터 EDA", "🔍 시장 비교 · 스펙 진단"])


# =====================================================================
# 탭 1. 시장 데이터 EDA
# =====================================================================
with tab1:
    # -----------------------------------------------------------------
    # 섹션 1) 사람인 채용 데이터 EDA
    # -----------------------------------------------------------------
    st.header("① 사람인 채용 데이터 EDA")

    if df_postings is not None and df_company is not None:
        skills_n = (df_company["type"] == "skills").sum()
        certs_n = (df_company["type"] == "certifications").sum()

        k1, k2, k3 = st.columns(3)
        k1.metric("📄 실채용공고 수", f"{len(df_postings):,} 건")
        k2.metric("🛠️ 분석된 스킬 키워드", f"{skills_n} 개")
        k3.metric("📜 분석된 자격증 키워드", f"{certs_n} 개")
        st.caption(f"✅ 실데이터 연동: {postings_path} · {company_path}")

        st.write("---")
        col_a, col_b = st.columns(2)

        with col_a:
            st.subheader("주요 요구 스킬 TOP 10")
            top_skills = df_company[df_company["type"] == "skills"].sort_values("frequency_score", ascending=False).head(10)
            fig1 = go.Figure(go.Bar(
                x=top_skills["frequency_score"][::-1], y=top_skills["representative_keyword"][::-1],
                orientation="h", marker_color="#fb7185",
                text=[f"{v:,.0f}" for v in top_skills["frequency_score"][::-1]], textposition="outside",
                hovertemplate="스킬: %{y}<br>가중 TF-IDF: %{x:,.1f}<extra></extra>"
            ))
            fig1.update_layout(xaxis_title="가중 TF-IDF 스코어", height=400,
                                plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig1, use_container_width=True)

        with col_b:
            st.subheader("주요 채용 키워드 (자격증/어학) TOP 10")
            top_certs = df_company[df_company["type"] == "certifications"].sort_values("frequency_score", ascending=False).head(10)
            if not top_certs.empty:
                fig2 = go.Figure(go.Bar(
                    x=top_certs["frequency_score"][::-1], y=top_certs["representative_keyword"][::-1],
                    orientation="h", marker_color="#818cf8",
                    text=[f"{v:,.0f}" for v in top_certs["frequency_score"][::-1]], textposition="outside",
                    hovertemplate="키워드: %{y}<br>가중 TF-IDF: %{x:,.1f}<extra></extra>"
                ))
                fig2.update_layout(xaxis_title="가중 TF-IDF 스코어", height=400,
                                    plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("📭 해당 직무의 자격증/어학 키워드 데이터가 없습니다.")

        st.write("---")
        col_c, col_d = st.columns(2)
        with col_c:
            st.subheader("학력 요구 분포")
            edu_dist = df_postings["education"].value_counts()
            fig3 = go.Figure(go.Pie(labels=edu_dist.index, values=edu_dist.values, hole=0.4,
                                     hovertemplate="%{label}: %{value}건 (%{percent})<extra></extra>"))
            fig3.update_layout(height=360, margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig3, use_container_width=True)
        with col_d:
            st.subheader("경력 요구 분포")
            career_dist = df_postings["career"].value_counts().head(8)
            fig4 = go.Figure(go.Bar(x=career_dist.index, y=career_dist.values, marker_color="#34495e",
                                     hovertemplate="%{x}: %{y}건<extra></extra>"))
            fig4.update_layout(xaxis_title="경력 구분", yaxis_title="공고 수", height=360,
                                margin=dict(t=30, b=10, l=10, r=10))
            st.plotly_chart(fig4, use_container_width=True)
        st.caption(f"✅ 실데이터 연동: {postings_path}")

        st.write("---")
        top1_skill = top_skills.iloc[0] if not top_skills.empty else None
        top_edu = edu_dist.index[0] if len(edu_dist) else "-"
        top_edu_pct = edu_dist.iloc[0] / len(df_postings) * 100 if len(edu_dist) else 0
        insight_msgs = []
        if top1_skill is not None:
            insight_msgs.append(f"가장 많이 요구되는 스킬은 **{top1_skill['representative_keyword']}**(가중 TF-IDF {top1_skill['frequency_score']:,.0f})입니다.")
        insight_msgs.append(f"학력 요건은 **{top_edu}**이(가) 전체의 {top_edu_pct:.0f}%로 가장 많습니다.")
        st.info("💡 " + " ".join(insight_msgs))
    else:
        st.info(f"📭 **데이터 없음** — [{selected_job}] 직무의 실채용공고/기업 요구 키워드 실데이터가 없습니다.")

    st.write("---")

    # -----------------------------------------------------------------
    # 섹션 2) 네이버 검색/콘텐츠 EDA
    # -----------------------------------------------------------------
    st.header("② 네이버 검색/콘텐츠 EDA")

    if df_jobseeker is not None:
        k1, k2, k3 = st.columns(3)
        k1.metric(f"💬 [{selected_job}] 관심도 (콘텐츠 총 건수)", f"{len(df_content):,} 건" if df_content is not None else f"{int(df_jobseeker['unique_document_count'].sum()):,} 건")
        if df_content is not None:
            sc = df_content["source"].value_counts()
            k2.metric("📊 blog / cafe / kin", f"{sc.get('blog',0):,} / {sc.get('cafe',0):,} / {sc.get('kin',0):,}")
        top_kw = df_jobseeker.sort_values("unique_document_count", ascending=False).iloc[0]
        k3.metric("🔝 최다 관심 키워드", top_kw["representative_keyword"], delta=f"{int(top_kw['unique_document_count']):,}건", delta_color="off")
        st.caption(f"✅ 실데이터 연동: {jobseeker_path}" + (f" · {content_path}" if content_path else ""))

        st.write("---")
        col_e, col_f = st.columns(2)
        with col_e:
            st.subheader("취업 준비 키워드 TOP 10")
            st.caption("※ '검색량'이 아닌 네이버 취업 관련 콘텐츠 문서 수(블로그+카페+지식iN, 중복 제거) 기준입니다.")
            top_jb = df_jobseeker.sort_values("unique_document_count", ascending=False).head(10)
            fig5 = go.Figure(go.Bar(
                x=top_jb["representative_keyword"], y=top_jb["unique_document_count"],
                text=top_jb["unique_document_count"], textposition="outside", marker_color="#60a5fa",
                customdata=top_jb[["blog_document_count", "cafe_document_count", "kin_document_count"]].values,
                hovertemplate="%{x}<br>문서 수: %{y}건<br>블로그 %{customdata[0]} · 카페 %{customdata[1]} · 지식iN %{customdata[2]}<extra></extra>"
            ))
            fig5.update_layout(yaxis_title="취업 관련 콘텐츠 문서 수 (건)", height=400,
                                plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig5, use_container_width=True)

        with col_f:
            st.subheader("키워드 카테고리 분석")
            if df_company is not None:
                type_map = df_company.set_index("representative_keyword")["type"].to_dict()
                cat_series = df_jobseeker.copy()
                cat_series["type"] = cat_series["representative_keyword"].map(type_map).fillna("기타")
                cat_sum = cat_series.groupby("type")["unique_document_count"].sum()
                fig6 = go.Figure(go.Pie(labels=cat_sum.index, values=cat_sum.values, hole=0.4,
                                         hovertemplate="%{label}: %{value}건 (%{percent})<extra></extra>"))
                fig6.update_layout(height=400, margin=dict(t=30, b=10, l=10, r=10))
                st.plotly_chart(fig6, use_container_width=True)
            else:
                st.info("📭 기업 요구 키워드 데이터가 없어 카테고리(skills/certifications) 분류를 매길 수 없습니다.")

        st.caption("⏱️ 시계열(월별) 검색비율 실데이터는 프로젝트 내에 존재하지 않아 관심도 추이 분석은 제외했습니다.")

        st.write("---")
        st.info(f"💡 [{selected_job}] 네이버 취업 준비 콘텐츠에서 가장 많이 언급된 키워드는 **{top_kw['representative_keyword']}**({int(top_kw['unique_document_count']):,}건)입니다.")
    else:
        st.info(f"📭 **데이터 없음** — [{selected_job}] 직무의 네이버 취업 준비 콘텐츠 실데이터가 없습니다. (현재는 데이터분석가/AI엔지니어만 연동)")


# =====================================================================
# 탭 2. 시장 비교 · 스펙 진단
# =====================================================================
with tab2:
    # -----------------------------------------------------------------
    # 섹션 1) 기업 수요 vs 구직자 관심 GAP
    # -----------------------------------------------------------------
    st.header("① 기업 수요 vs 구직자 관심 GAP")
    st.caption("사람인 실채용공고(기업 수요)와 네이버 취업 준비 콘텐츠(구직자 관심)의 공통 키워드를 0~100으로 각각 정규화해 비교합니다.")

    if df_gap is not None:
        k1, k2 = st.columns(2)
        k1.metric("🔗 공통 키워드 수", f"{len(df_gap)} 개")
        biggest = df_gap.loc[df_gap["gap_score"].abs().idxmax()]
        k2.metric("⚠️ 최대 GAP 키워드", biggest["representative_keyword"],
                   delta=("기업 수요 > 구직자 관심" if biggest["gap_score"] > 0 else "구직자 관심 > 기업 수요"), delta_color="off")
        st.caption(f"✅ build_gap_table() 실행 시 자동 생성 — 원천: {company_path} · {jobseeker_path}")

        st.write("---")
        st.subheader("4분면 분석 (Scatter)")
        fig_sc = go.Figure()
        for t, color in [("skills", "#fb7185"), ("certifications", "#818cf8")]:
            d = df_gap[df_gap["type"] == t]
            if d.empty:
                continue
            fig_sc.add_trace(go.Scatter(
                x=d["jobseeker_content_score"], y=d["company_demand_score"],
                mode="markers+text", text=d["representative_keyword"], textposition="top center",
                name=t, marker=dict(size=11, color=color, opacity=0.85, line=dict(width=1, color="white")),
                hovertemplate="%{text}<br>구직자 관심: %{x:.0f}<br>기업 수요: %{y:.0f}<extra></extra>"
            ))
        fig_sc.add_hline(y=50, line_dash="dash", line_color="#94a3b8", line_width=1)
        fig_sc.add_vline(x=50, line_dash="dash", line_color="#94a3b8", line_width=1)
        fig_sc.add_annotation(x=0.05, y=0.95, xref="paper", yref="paper", text="기업 수요 高 · 구직자 관심 低", showarrow=False, font=dict(size=10, color="#ef4444"))
        fig_sc.add_annotation(x=0.95, y=0.95, xref="paper", yref="paper", text="기업 수요 高 · 구직자 관심 高", showarrow=False, font=dict(size=10, color="#16a34a"))
        fig_sc.add_annotation(x=0.05, y=0.05, xref="paper", yref="paper", text="기업 수요 低 · 구직자 관심 低", showarrow=False, font=dict(size=10, color="#94a3b8"))
        fig_sc.add_annotation(x=0.95, y=0.05, xref="paper", yref="paper", text="기업 수요 低 · 구직자 관심 高", showarrow=False, font=dict(size=10, color="#f59e0b"))
        fig_sc.update_layout(xaxis_title="구직자 관심도 (0~100)", yaxis_title="기업 수요도 (0~100)",
                              height=500, plot_bgcolor="rgba(255,255,255,0.95)", paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_sc, use_container_width=True)

        st.write("---")
        col_g, col_h = st.columns(2)
        top_gap = df_gap.reindex(df_gap["gap_score"].abs().sort_values(ascending=False).index).head(10)
        with col_g:
            st.subheader("GAP 큰 키워드 TOP 10")
            st.dataframe(
                top_gap[["representative_keyword", "type", "company_demand_score", "jobseeker_content_score", "gap_score"]].round(1),
                use_container_width=True, hide_index=True
            )
        with col_h:
            st.subheader("수요 vs 관심 Bar Chart")
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(x=top_gap["representative_keyword"], y=top_gap["company_demand_score"], name="기업 수요", marker_color="#fb7185"))
            fig_bar.add_trace(go.Bar(x=top_gap["representative_keyword"], y=top_gap["jobseeker_content_score"], name="구직자 관심", marker_color="#818cf8"))
            fig_bar.update_layout(barmode="group", yaxis_title="정규화 스코어 (0~100)", height=400,
                                   plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)",
                                   legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig_bar, use_container_width=True)

        st.write("---")
        top_company_side = top_gap[top_gap["gap_score"] > 0].head(1)
        top_jobseeker_side = top_gap[top_gap["gap_score"] < 0].head(1)
        lines = []
        if not top_company_side.empty:
            r = top_company_side.iloc[0]
            lines.append(f"**{r['representative_keyword']}**는 기업 요구도({r['company_demand_score']:.0f}점)가 높지만 취업 준비 콘텐츠 언급({r['jobseeker_content_score']:.0f}점)은 상대적으로 낮습니다.")
        if not top_jobseeker_side.empty:
            r = top_jobseeker_side.iloc[0]
            lines.append(f"**{r['representative_keyword']}**는 취업 준비 콘텐츠에서는 관심({r['jobseeker_content_score']:.0f}점)이 높지만 기업 공고 요구도({r['company_demand_score']:.0f}점)는 상대적으로 낮습니다.")
        if lines:
            st.info("💡 " + " ".join(lines))
    else:
        st.info(f"📭 **데이터 없음** — [{selected_job}] 직무는 기업 요구 키워드와 네이버 관심 키워드가 동시에 존재해야 GAP 분석이 가능합니다. (현재는 데이터분석가/AI엔지니어만 두 데이터가 모두 있음)")

    st.write("---")

    # -----------------------------------------------------------------
    # 섹션 2) 구직자 스펙 진단
    # -----------------------------------------------------------------
    st.header("② 구직자 스펙 진단")
    st.caption(f"희망 직무는 사이드바에서 선택한 **[{selected_job}]**을 사용합니다. 실제 채용공고 텍스트 매칭만으로 계산하며, LLM 기반 임의 추천은 사용하지 않습니다.")

    if df_company is not None and df_postings is not None:
        col_i1, col_i2, col_i3 = st.columns(3)
        with col_i1:
            user_career = st.selectbox("📅 나의 경력", ["신입", "1~3년", "4~7년", "8년 이상"], key="diag_career")
        with col_i2:
            user_edu = st.selectbox("🎓 최종 학력", ["고졸", "초대졸", "대졸", "석사", "박사"], key="diag_edu")
        with col_i3:
            all_skills = df_company.sort_values("frequency_score", ascending=False)["representative_keyword"].tolist()
            user_skills = st.multiselect("🛠️ 보유 스킬/자격증", options=all_skills, default=[], key="diag_skills")

        run_diag = st.button("📊 스펙 진단 실행", key="diag_run")

        if run_diag or user_skills:
            df_rates = compute_skill_appearance_rates(df_company, df_postings)
            top10 = df_rates.head(10)
            lacking = top10[~top10["representative_keyword"].isin(user_skills)]
            priority3 = lacking.sort_values("appearance_rate", ascending=False).head(3)

            st.write("---")
            k1, k2, k3 = st.columns(3)
            k1.metric("🏢 기업 요구 TOP 스킬 수", f"{len(top10)} 개")
            k2.metric("✅ 내 보유 스킬 (TOP10 중)", f"{len(top10) - len(lacking)} / {len(top10)}")
            k3.metric("⚠️ 부족한 스킬", f"{len(lacking)} 개")

            col_j1, col_j2 = st.columns(2)
            with col_j1:
                st.subheader("기업 요구 TOP 스킬 & 내 보유 여부")
                display_df = top10[["representative_keyword", "type", "appearance_rate", "posting_count"]].copy()
                display_df["보유 여부"] = display_df["representative_keyword"].apply(lambda k: "✅ 보유" if k in user_skills else "❌ 미보유")
                display_df = display_df.rename(columns={
                    "representative_keyword": "스킬/자격증", "type": "구분",
                    "appearance_rate": "공고 등장 비율(%)", "posting_count": "등장 공고 수"
                })
                st.dataframe(display_df, use_container_width=True, hide_index=True)

            with col_j2:
                st.subheader("스킬별 공고 등장 비율")
                fig_rate = go.Figure(go.Bar(
                    x=top10["representative_keyword"], y=top10["appearance_rate"],
                    marker_color=["#16a34a" if k in user_skills else "#fb7185" for k in top10["representative_keyword"]],
                    text=[f"{v:.0f}%" for v in top10["appearance_rate"]], textposition="outside",
                    hovertemplate="%{x}<br>공고 등장 비율: %{y:.1f}%<extra></extra>"
                ))
                fig_rate.update_layout(yaxis_title="공고 등장 비율 (%)", height=400,
                                        plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_rate, use_container_width=True)
                st.caption("초록 = 보유, 빨강 = 미보유")

            st.write("---")
            st.subheader("준비 우선순위 TOP 3 (실제 채용공고 등장 빈도 기준)")
            if not priority3.empty:
                for i, (_, r) in enumerate(priority3.iterrows(), 1):
                    st.warning(f"**{i}순위: {r['representative_keyword']}** — 실채용공고의 {r['appearance_rate']:.1f}%({r['posting_count']}건)에서 요구되지만 아직 보유하지 않았습니다.")
            else:
                st.success("🎉 기업 요구 TOP10 스킬을 모두 보유하고 계십니다.")
            st.caption(f"✅ 실데이터 연동: {postings_path} · {company_path} — 텍스트 동의어 매칭 기반 결정론적 계산 (LLM 미사용)")
        else:
            st.info("💡 보유 스킬을 선택하거나 '스펙 진단 실행' 버튼을 누르면 실제 채용공고 기준 진단 결과가 표시됩니다.")
    else:
        st.info(f"📭 **데이터 없음** — [{selected_job}] 직무의 실채용공고/기업 요구 키워드 데이터가 없어 진단할 수 없습니다.")


st.write("---")
st.caption(
    "📊 취업 시장 실데이터 분석 대시보드 — mock/임시 데이터 미사용, 실제 파일/DB만 사용합니다. "
    "감사/컴플라이언스 직무 및 월별 검색 시계열은 실데이터가 없어 제외되어 있습니다."
)
