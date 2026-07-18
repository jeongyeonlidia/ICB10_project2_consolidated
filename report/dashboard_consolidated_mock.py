"""
취업 시장 다차원 EDA 및 직무 적합도 진단 솔루션 (SaaS) — 마스터 통합 대시보드

주요 기능:
- 6대 직무(기획/전략, 인사/노무, 회계/재무, 감사/컴플라이언스, 마케팅, 데이터분석가/AI엔지니어) 지원
- 사이드바 마스터 컨트롤러(직무 스위처)를 통한 실시간 동적 데이터 연동(Reactive)
- 4대 마스터 탭 구조 구현:
  - 🏠 탭 0. 홈: 취업 마켓 다차원 EDA 센터 (전 직무 미스매치 현황, 주요 수집 데이터 규모 요약, 수요-공급 4분면 맵, Co-occurrence 네트워크, 시계열 관심도 트렌드, 네이버 카페 TF-IDF 여론 분석)
  - 💡 탭 1. 구직자: 스펙 자가진단 및 스코어링 엔진 (경력/학력/자격증/툴/경험 5대 다차원 가중치 산출 및 보완 추천)
  - 🏢 탭 2. 인사팀: 수급 Gap 분석 및 JD 최적화 도구 (Gap 차트, 미스매치 카드, JD 리모델링 시뮬레이터, 전략 제언)
  - ⚠️ 탭 3. 기업 이직위험 & 채용건전성 분석 (업종별 평균 이직위험도, 사원수별 이직위험 상관관계, 악성 구인 순환 분석)
- 실제 데이터(automated_total_mismatch_mart.csv, saramin_search_jobs.db, naver_dataanalysis.csv, saramin_turnover_datamart.csv,
  keyword_extraction_result_v2.json, data/naver_api/it_data/processed/*.csv)만 사용. 해당 파일이 없으면 차트 대신 "데이터 연동 필요" 메시지 표시.
- 탭2(인사팀 Gap 분석), 탭3(이직위험 분석)은 뒷받침할 실데이터 파일이 아직 없어 현재 비활성화(주석 처리)되어 있습니다.
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import re
import json
import itertools
from collections import Counter

# =====================================================================
# 페이지 기본 설정
# =====================================================================
st.set_page_config(
    page_title="마스터 통합 채용 미스매치 & 자가진단 대시보드",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================================================
# 1. 직무별 마스터 데이터 및 자가진단 풀 정의
# =====================================================================
JOB_LIST = [
    "기획/전략", "인사/노무", "회계/재무",
    "감사/컴플라이언스", "마케팅", "데이터분석가/AI엔지니어"
]

JOB_SPECS_POOL = {
    "기획/전략": {
        "licenses": ["SQLD", "ADsP", "정보처리기사", "CFA", "CPA", "컴퓨터활용능력"],
        "tools": ["Figma", "GA4", "Slack", "Jira", "Git", "ERP (더존/SAP)", "Tableau"],
        "experiences": ["역기획", "프로토타이핑", "서비스로그 분석", "M&A 검토", "시장조사 및 리서치", "사업타당성 분석", "예산 및 결산 관리"],
        "synonyms": {
            "SQLD": ["sqld", "sql개발자"], "ADsP": ["adsp", "데이터분석준전문가"],
            "정보처리기사": ["정보처리기사", "정처기"], "CFA": ["cfa", "재무분석사"],
            "CPA": ["cpa", "공인회계사"], "컴퓨터활용능력": ["컴퓨터활용능력", "컴활", "오피스"],
            "Figma": ["figma", "피그마"], "GA4": ["ga4", "구글애널리틱스"],
            "Slack": ["slack", "슬랙"], "Jira": ["jira", "지라"],
            "Git": ["git", "깃", "github"], "ERP (더존/SAP)": ["erp", "sap", "더존"],
            "Tableau": ["tableau", "태블로"],
            "역기획": ["역기획"], "프로토타이핑": ["프로토타이핑", "화면설계", "와이어프레임"],
            "서비스로그 분석": ["서비스로그", "로그분석", "ga4", "amplitude"],
            "M&A 검토": ["m&a", "인수합병", "투자심사"],
            "시장조사 및 리서치": ["시장조사", "리서치", "research"],
            "사업타당성 분석": ["타당성분석", "타당성 분석", "feasibility"],
            "예산 및 결산 관리": ["예산", "결산", "세무", "회계"]
        }
    },
    "인사/노무": {
        "licenses": ["공인노무사", "PHR/SPHR", "직업상담사", "ERP(인사)"],
        "tools": ["Slack", "Workday", "엑셀", "Google Workspace"],
        "experiences": ["노동법 대응", "조직문화 설계", "성과관리 시스템 구축", "채용면접기법"],
        "synonyms": {
            "공인노무사": ["노무사", "cpla"], "PHR/SPHR": ["phr", "sphr", "hr자격증"],
            "직업상담사": ["직업상담", "직상"], "ERP(인사)": ["erp", "더존", "sap"],
            "Slack": ["slack", "슬랙"], "Workday": ["workday", "워크데이"],
            "엑셀": ["엑셀", "excel"], "Google Workspace": ["gsuite", "구글웍스", "docs"],
            "노동법 대응": ["노동법", "근로기준법", "노무"], "조직문화 설계": ["조직문화", "컬처", "culture"],
            "성과관리 시스템 구축": ["성과관리", "kpi", "okr", "평가"], "채용면접기법": ["채용", "면접", "recruiting"]
        }
    },
    "회계/재무": {
        "licenses": ["CPA", "세무사", "재경관리사", "AICPA"],
        "tools": ["ERP(회계)", "SAP", "더존 i-U", "엑셀(VBA)"],
        "experiences": ["IFRS 적용", "세무 조정", "예산 편성 및 통제", "자금 운용 및 조달"],
        "synonyms": {
            "CPA": ["cpa", "회계사"], "세무사": ["세무사", "cta"],
            "재경관리사": ["재경관리사", "재경"], "AICPA": ["aicpa", "미국회계사"],
            "ERP(회계)": ["erp", "더존"], "SAP": ["sap", "에스에이피"],
            "더존 i-U": ["더존"], "엑셀(VBA)": ["vba", "excel", "엑셀"],
            "IFRS 적용": ["ifrs", "국제회계기준"], "세무 조정": ["세무조정", "법인세", "소득세"],
            "예산 편성 및 통제": ["예산", "통제", "budget"], "자금 운용 및 조달": ["자금", "조달", "운용", "treasury"]
        }
    },
    "감사/컴플라이언스": {
        "licenses": ["CIA", "CISA", "CFE"],
        "tools": ["ACL", "IDEA", "데이터분석(감사)", "Excel"],
        "experiences": ["내부감사 수행", "SOX 대응", "리스크 평가", "준법 감시"],
        "synonyms": {
            "CIA": ["cia", "국제내부감사사"], "CISA": ["cisa", "정보시스템감사사"],
            "CFE": ["cfe", "공인부정검사사"], "ACL": ["acl"], "IDEA": ["idea"],
            "데이터분석(감사)": ["데이터분석", "감사분석", "쿼리"], "Excel": ["excel", "엑셀"],
            "내부감사 수행": ["내부감사", "감사", "audit"], "SOX 대응": ["sox", "내부회계관리제도", "내부회계"],
            "리스크 평가": ["리스크", "risk", "위험"], "준법 감시": ["준법", "컴플라이언스", "compliance"]
        }
    },
    "마케팅": {
        "licenses": ["구글 애널리틱스 IQ", "SQLD", "검색광고마케터"],
        "tools": ["GA4", "Google Ads", "Meta Ads", "HubSpot", "Braze"],
        "experiences": ["SEO/SEM 최적화", "콘텐츠 기획 및 제작", "CRM 마케팅", "브랜드 전략 수립"],
        "synonyms": {
            "구글 애널리틱스 IQ": ["gaiq", "ga인증"], "SQLD": ["sqld", "sql"],
            "검색광고마케터": ["검색광고", "검광마"], "GA4": ["ga4", "구글애널리틱스"],
            "Google Ads": ["구글애즈", "google ads"], "Meta Ads": ["페이스북광고", "meta ads", "인스타광고"],
            "HubSpot": ["hubspot", "허브스팟"], "Braze": ["braze", "브레이즈"],
            "SEO/SEM 최적화": ["seo", "sem", "검색엔진"], "콘텐츠 기획 및 제작": ["콘텐츠", "카드뉴스", "제작"],
            "CRM 마케팅": ["crm", "리텐션", "푸시"], "브랜드 전략 수립": ["브랜드", "브랜딩", "전략"]
        }
    },
    "데이터분석가/AI엔지니어": {
        "licenses": ["빅데이터분석기사", "ADsP", "AWS Certified Data Analytics"],
        "tools": ["Python", "SQL", "Tableau/PowerBI", "Spark", "TensorFlow/PyTorch"],
        "experiences": ["지표 정의 및 대시보드 구축", "데이터 파이프라인(ETL) 구축", "ML/DL 모델링", "A/B 테스트 설계 및 분석"],
        "synonyms": {
            "빅데이터분석기사": ["빅분기"], "ADsP": ["adsp"],
            "AWS Certified Data Analytics": ["aws"], "Python": ["python", "파이썬"],
            "SQL": ["sql", "mysql", "oracle", "postgresql"], "Tableau/PowerBI": ["tableau", "태블로", "powerbi", "파워비아이"],
            "Spark": ["spark", "스파크", "hadoop", "하둡"], "TensorFlow/PyTorch": ["tensorflow", "pytorch", "keras", "딥러닝"],
            "지표 정의 및 대시보드 구축": ["지표", "대시보드", "dashboard", "시각화"],
            "데이터 파이프라인(ETL) 구축": ["파이프라인", "etl", "airflow"],
            "ML/DL 모델링": ["ml", "dl", "모델링", "예측"], "A/B 테스트 설계 및 분석": ["ab테스트", "a/b", "실험"]
        }
    }
}

# (MOCK_SKILLS_BY_JOB, MOCK_COOCCURRENCE, build_mock_mart 제거됨 - 실데이터 없는 가짜 통계였음. git 이력에서 복원 가능)

# =====================================================================
# 2. 실제 데이터 로더 (기존 파이프라인 결과물 우선 로드)
# =====================================================================
@st.cache_data
def load_real_mismatch_mart():
    paths = [
        "automated_total_mismatch_mart.csv",
        "../automated_total_mismatch_mart.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p, encoding="utf-8-sig"), p
            except Exception:
                pass
    return None, None

@st.cache_data
def load_naver_cafe_data():
    paths = [
        "naver-api-app/data/naver_dataanalysis.csv",
        "../naver-api-app/data/naver_dataanalysis.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p, encoding="utf-8-sig"), p
            except Exception:
                pass
    return None, None

@st.cache_data
def load_it_dev_company_demand():
    """IT개발·데이터 직무 기업 요구 스펙 (keyword_extraction_result_v2.json, dev 카테고리)."""
    paths = [
        "data/keyword_extraction_result_v2.json",
        "../data/keyword_extraction_result_v2.json",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    raw = json.load(f)
                dev_groups = raw["results"]["dev"]["keyword_groups"]
                rows = [{
                    "representative_keyword": g["representative_keyword"],
                    "type": g["type"],
                    "company_demand_raw": g["frequency_score"],
                } for g in dev_groups]
                return pd.DataFrame(rows), p
            except Exception:
                pass
    return None, None


@st.cache_data
def load_it_dev_jobseeker_content():
    """IT개발·데이터 직무 네이버 취업 준비 콘텐츠 키워드 집계 (keyword_content_summary.csv)."""
    paths = [
        "data/naver_api/it_data/processed/keyword_content_summary.csv",
        "../data/naver_api/it_data/processed/keyword_content_summary.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p, encoding="utf-8-sig"), p
            except Exception:
                pass
    return None, None


@st.cache_data
def load_it_dev_content_sample():
    """IT개발·데이터 직무 네이버 취업 관련 콘텐츠 원문 (it_job_related_content.csv)."""
    paths = [
        "data/naver_api/it_data/processed/it_job_related_content.csv",
        "../data/naver_api/it_data/processed/it_job_related_content.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p, encoding="utf-8-sig"), p
            except Exception:
                pass
    return None, None


def build_it_dev_gap_table(df_company, df_jobseeker):
    """기업 요구(TF-IDF) vs 구직자 관심(문서수)을 skills/certifications 그룹별 0~100 min-max 정규화 후 병합."""
    merged = pd.merge(
        df_company,
        df_jobseeker[["representative_keyword", "unique_document_count",
                      "blog_document_count", "cafe_document_count", "kin_document_count"]],
        on="representative_keyword", how="inner"
    ).rename(columns={"unique_document_count": "jobseeker_content_raw"})

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


@st.cache_data
def load_saramin_db():
    """기획/전략 직무로 스크랩된 실제 사람인 채용공고 DB (1,000건, company/title/career/education/sectors/detail_content)."""
    paths = [
        "data/saramin_search_jobs.db",
        "../data/saramin_search_jobs.db",
        "saramin/data/saramin_search_jobs.db",
        "../saramin/data/saramin_search_jobs.db",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                conn = sqlite3.connect(p)
                df = pd.read_sql("SELECT * FROM saramin_jobs", conn)
                conn.close()
                return df, p
            except Exception:
                pass
    return None, None


@st.cache_data
def load_it_dev_recruit_data():
    """IT개발·데이터(dev) 직무 실제 채용공고 (recruit_processed.db, 1,000건).
    load_saramin_db()와 동일한 컬럼(company/title/link/career/education/sectors/detail_content)으로 매핑해 반환."""
    paths = [
        "data/recruit_processed.db",
        "../data/recruit_processed.db",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                conn = sqlite3.connect(p)
                df = pd.read_sql("SELECT * FROM recruit_cleaned WHERE job_category='dev'", conn)
                conn.close()
                df = df.rename(columns={
                    "company_name": "company",
                    "education_level": "education",
                    "experience_level": "career",
                    "job_sector": "sectors",
                })
                df["detail_content"] = (
                    df["cleaned_requirement"].fillna("") + " " + df["cleaned_preferential"].fillna("")
                )
                return df, p
            except Exception:
                pass
    return None, None


def get_saramin_mart(job_name):
    """선택된 직무에 실제로 존재하는 채용공고 실데이터를 반환. 없으면 (None, None)."""
    if job_name == "기획/전략" and df_saramin is not None:
        return df_saramin, saramin_path
    if job_name == "데이터분석가/AI엔지니어" and df_it_recruit is not None:
        return df_it_recruit, it_recruit_path
    return None, None


@st.cache_data
def load_turnover_datamart():
    paths = [
        "saramin/data/saramin_turnover_datamart.csv",
        "../saramin/data/saramin_turnover_datamart.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p, encoding="utf-8-sig"), p
            except Exception:
                pass
    return None, None

# 데이터 로드
df_real_mart, real_mart_path = load_real_mismatch_mart()
df_naver, naver_path = load_naver_cafe_data()
df_saramin, saramin_path = load_saramin_db()
df_it_recruit, it_recruit_path = load_it_dev_recruit_data()
df_turnover, turnover_path = load_turnover_datamart()

# IT개발·데이터 직무 네이버 실데이터 (1차 연동)
df_it_company, it_company_path = load_it_dev_company_demand()
df_it_jobseeker, it_jobseeker_path = load_it_dev_jobseeker_content()
df_it_content, it_content_path = load_it_dev_content_sample()
df_it_gap = build_it_dev_gap_table(df_it_company, df_it_jobseeker) if (df_it_company is not None and df_it_jobseeker is not None) else None


# =====================================================================
# 3. 사이드바 컨트롤러 (Control Tower)
# =====================================================================
st.sidebar.title("🎛️ 마스터 컨트롤러")
st.sidebar.markdown("대시보드 전체 데이터를 제어하는 직무 스위처입니다.")

selected_job = st.sidebar.selectbox(
    "📋 분석할 직무를 선택하세요",
    JOB_LIST,
    index=0,
    help="선택한 직무에 맞춰 대시보드 메인 화면의 탭별 데이터셋이 실시간으로 새로고침됩니다."
)

selected_sub_job = "전체"
if selected_job == "기획/전략":
    selected_sub_job = st.sidebar.radio(
        "🔍 세부 기획 직무 필터",
        ["전체", "IT/서비스 기획", "경영/사업 전략"],
        help="기획/전략 직무 내 세부 직무에 따라 요구되는 역량 스펙을 미세 조율합니다."
    )

st.sidebar.write("---")

# 현재 직무에 실제로 연동 가능한 채용공고 실데이터 결정
df_saramin_job, saramin_job_path = get_saramin_mart(selected_job)

# 데이터 소스 상태 표시
st.sidebar.subheader("📡 데이터 소스 현황")
if real_mart_path:
    st.sidebar.success(f"✅ 수급마트 (실제): {real_mart_path}")
else:
    st.sidebar.warning("⚠️ 실제 수급마트 미발견 → 데이터 연동 필요 (자동 생성된 automated_total_mismatch_mart.csv는 이전 mock 값과 동일해 사용하지 않음)")

if naver_path:
    st.sidebar.success(f"✅ 네이버카페 (실제): {naver_path}")
else:
    st.sidebar.warning("⚠️ 네이버 카페 데이터 미발견 → 데이터 연동 필요")

if saramin_job_path:
    st.sidebar.success(f"✅ 채용공고 실데이터 [{selected_job}]: {saramin_job_path}")
else:
    st.sidebar.warning(f"⚠️ [{selected_job}] 채용공고 실데이터 미발견 → 데이터 연동 필요 (현재는 기획/전략, 데이터분석가/AI엔지니어만 연동)")

if turnover_path:
    st.sidebar.success(f"✅ 이직위험마트 (실제): {turnover_path}")
else:
    st.sidebar.warning("⚠️ 이직위험마트 미발견 → 데이터 연동 필요 (탭 비활성화)")

if it_jobseeker_path and it_company_path:
    st.sidebar.success(f"✅ IT개발·데이터 네이버 실데이터: {it_jobseeker_path}")
else:
    st.sidebar.warning("⚠️ IT개발·데이터 네이버 실데이터 미발견 → 해당 섹션 비활성화")


# 현재 직무의 데이터프레임 결정 (실데이터만 사용, 없으면 None)
def get_job_mart(job_name):
    if job_name == "기획/전략" and df_real_mart is not None:
        return df_real_mart
    return None

df_mart = get_job_mart(selected_job)

# 세부 직무 선택에 따른 데이터 마트 필터링 처리
if df_mart is not None and selected_job == "기획/전략" and selected_sub_job in ["IT/서비스 기획", "경영/사업 전략"]:
    if selected_sub_job == "IT/서비스 기획":
        target_skills_sub = ["SQLD", "ADsP", "Figma", "GA4", "컴퓨터활용능력", "정보처리기사", "데이터분석", "시장조사", "PPT작성법"]
    else: # 경영/사업 전략
        target_skills_sub = ["CPA", "CFA", "M&A", "컴퓨터활용능력", "정보처리기사", "데이터분석", "시장조사", "PPT작성법"]
    df_mart = df_mart[df_mart["자격증명"].isin(target_skills_sub)]

months_cols = [c for c in df_mart.columns if "_검색비율" in c] if df_mart is not None else []
months_labels = [c.replace("_검색비율", "") for c in months_cols]


# =====================================================================
# 4. 메인 타이틀 및 4 탭 구성
# =====================================================================
st.title("🤖 취업 시장 다차원 EDA 및 직무 적합도 진단 솔루션 (SaaS)")
st.markdown(
    f"**현재 관제 직무**: `{selected_job}` | "
    "실제 수집·연동된 데이터 파일만 사용하는 1차 실데이터 버전입니다."
)
st.write("---")

# 탭2(인사팀 Gap 분석), 탭3(이직위험 분석)은 뒷받침할 실데이터 파일이 없어 비활성화했습니다.
# 관련 코드는 이 파일 하단에 주석(문자열 리터럴)으로 보존되어 있어, 실데이터 연동 시 복원할 수 있습니다.
tab0, tab1 = st.tabs([
    "🏠 홈: 취업 마켓 다차원 EDA",
    "💡 구직자: 스펙 자가진단 및 스코어링",
])


# =====================================================================
# 탭 0. 홈 (Intro): 전 직무 미스매치 종합 현황
# =====================================================================
with tab0:
    st.header("🏠 홈: 취업 마켓 다차원 EDA 센터")
    st.markdown(
        "실제로 수집·연동된 데이터 파일이 있는 항목만 표시됩니다. "
        "현재는 **기획/전략**(자동화 미스매치 마트) 및 **데이터분석가/AI엔지니어**(네이버 API 실데이터) 직무에 한해 "
        "실데이터 연동 코드가 준비되어 있으며, 그 외 직무는 파일이 연동되기 전까지 \'데이터 연동 필요\'로 표시됩니다."
    )

    # 데이터 규모 메트릭 카드
    st.write("### 📊 실시간 분석 데이터셋 규모")
    col_m1, col_m3 = st.columns(2)
    with col_m1:
        if df_saramin_job is not None:
            st.metric(label=f"📄 [{selected_job}] 채용공고 수", value=f"{len(df_saramin_job):,} 건", delta="실제 데이터 연동")
        else:
            st.metric(label=f"📄 [{selected_job}] 채용공고 수", value="데이터 없음", delta="연동 필요", delta_color="off")
    with col_m3:
        if selected_job == "데이터분석가/AI엔지니어" and df_it_content is not None:
            st.metric(label="💬 네이버 취업 준비 콘텐츠 (IT개발·데이터)", value=f"{len(df_it_content):,} 건", delta="실제 데이터 연동")
        elif df_naver is not None:
            st.metric(label="💬 네이버 카페 여론 글", value=f"{len(df_naver):,} 건", delta="실제 데이터 연동")
        else:
            st.metric(label="💬 네이버 취업 준비 콘텐츠", value="데이터 없음", delta="연동 필요", delta_color="off")

    st.write("---")

    # 직무별 평균 미스매치 지수(Gap Index) - 실데이터가 있는 직무만 집계
    gap_indices = {}
    for job in JOB_LIST:
        if job == "기획/전략" and df_real_mart is not None:
            gap_indices[job] = float(np.mean(np.abs(df_real_mart["수급Gap(건)"])))

    if gap_indices:
        df_gap_index = pd.DataFrame({
            "직무군": list(gap_indices.keys()),
            "평균 미스매치 지수(Gap Index)": list(gap_indices.values())
        }).sort_values("평균 미스매치 지수(Gap Index)", ascending=False)

        fig_home = go.Figure()
        fig_home.add_trace(go.Bar(
            x=df_gap_index["직무군"],
            y=df_gap_index["평균 미스매치 지수(Gap Index)"],
            marker_color=["#ef4444" if idx == 0 else "#818cf8" for idx in range(len(df_gap_index))],
            text=[f"{val:,.0f}" for val in df_gap_index["평균 미스매치 지수(Gap Index)"]],
            textposition="auto",
            hovertemplate="직무군: %{x}<br>미스매치 지수: %{y:,.1f}<extra></extra>"
        ))
        fig_home.update_layout(
            title=dict(text="<b>직무군 평균 채용 미스매치 지수(Gap Index) - 실데이터 연동 직무만</b>", font=dict(size=13)),
            xaxis_title="직무군 분류",
            yaxis_title="평균 미스매치 크기 (절대치 평균)",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=380
        )
        st.plotly_chart(fig_home, use_container_width=True)
        st.caption(f"✅ 실데이터 연동: {real_mart_path}")
    else:
        st.info("📭 **데이터 연동 필요** — 직무별 수급 마트 실데이터 파일(예: automated_total_mismatch_mart.csv)이 아직 연동되지 않았습니다.")

    # 거시적 채용 트렌드 및 노동 시장 핵심 인사이트
    st.write("---")
    st.write("### 📈 거시적 고용 시장 트렌드 & 노동시장 인사이트")

    if df_saramin_job is not None:
        st.markdown(
            f"**[{selected_job}]** 실제 채용공고 데이터를 분석하여, 학력 요구와 경력 선호 현황을 시각화합니다."
        )
        col_tr1, col_tr2 = st.columns(2)

        with col_tr1:
            edu_dist = df_saramin_job['education'].value_counts()
            fig_edu_pie = go.Figure()
            fig_edu_pie.add_trace(go.Pie(
                labels=edu_dist.index,
                values=edu_dist.values,
                hole=0.4,
                marker=dict(colors=['#1abc9c', '#3498db', '#9b59b6', '#f1c40f']),
                hovertemplate="학력 요건: %{label}<br>비율: %{percent}<br>공고 수: %{value}건<extra></extra>"
            ))
            fig_edu_pie.update_layout(
                title=f"<b>[{selected_job}] 학력 요구사항 분포</b>",
                height=380,
                margin=dict(t=50, b=20, l=20, r=20),
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_edu_pie, use_container_width=True)
            st.caption(f"✅ 실데이터 연동: {saramin_job_path}")

        with col_tr2:
            career_dist = df_saramin_job['career'].value_counts().head(7)
            fig_career_bar = go.Figure()
            fig_career_bar.add_trace(go.Bar(
                x=career_dist.index,
                y=career_dist.values,
                marker_color='#34495e',
                hovertemplate="경력 요건: %{x}<br>공고 수: %{y}건<extra></extra>"
            ))
            fig_career_bar.update_layout(
                title=f"<b>[{selected_job}] 채용 경력 요구 요건 분포</b>",
                xaxis_title="경력 구분",
                yaxis_title="공고 수 (건)",
                height=380,
                margin=dict(t=50, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_career_bar, use_container_width=True)
            st.caption(f"✅ 실데이터 연동: {saramin_job_path}")
    else:
        st.info(f"📭 **데이터 연동 필요** — [{selected_job}] 직무의 실제 채용공고 데이터가 아직 연동되지 않았습니다. (현재는 기획/전략, 데이터분석가/AI엔지니어만 연동)")


# =====================================================================
# 취업 마켓 다차원 EDA 센터 섹션
# =====================================================================
    st.write("---")
    st.subheader("📊 취업 마켓 다차원 EDA 센터")
    st.markdown(
        "기업 공고 수요와 구직자 관심 데이터의 다차원 EDA입니다. 실데이터가 없는 직무/구간은 표시되지 않습니다."
    )

    # ① 수요-공급 4분면 포지셔닝 맵 (실데이터가 있는 직무만 플롯)
    st.subheader("① 수요-공급 4분면 포지셔닝 맵")
    scatter_data = []
    for job in JOB_LIST:
        if job == "기획/전략" and df_real_mart is not None:
            for _, r in df_real_mart.iterrows():
                scatter_data.append({
                    "직무": job, "스킬": r["자격증명"],
                    "기업수요": r["기업_수요_건수"], "구직자공급": r["구직자_공급_건수"]
                })

    color_map = {
        "기획/전략": "#818cf8", "인사/노무": "#34d399",
        "회계/재무": "#fb7185", "감사/컴플라이언스": "#fbbf24",
        "마케팅": "#60a5fa", "데이터분석가/AI엔지니어": "#a78bfa",
    }

    if scatter_data:
        df_scatter = pd.DataFrame(scatter_data)
        median_demand = df_scatter["기업수요"].median()
        median_supply = df_scatter["구직자공급"].median()

        fig_scatter = go.Figure()
        for job in df_scatter["직무"].unique():
            df_j = df_scatter[df_scatter["직무"] == job]
            fig_scatter.add_trace(go.Scatter(
                x=df_j["기업수요"], y=df_j["구직자공급"],
                mode="markers+text",
                name=job,
                text=df_j["스킬"],
                textposition="top center",
                textfont=dict(size=9),
                marker=dict(size=11, color=color_map.get(job, "#999"), opacity=0.85,
                            line=dict(width=1, color="white")),
                hovertemplate="직무: %{fullData.name}<br>스킬: %{text}<br>수요: %{x}건<br>공급: %{y:,}건<extra></extra>"
            ))

        fig_scatter.add_hline(y=median_supply, line_dash="dash", line_color="#94a3b8", line_width=1)
        fig_scatter.add_vline(x=median_demand, line_dash="dash", line_color="#94a3b8", line_width=1)

        fig_scatter.update_layout(
            xaxis_title="기업 공고 수요 (건)",
            yaxis_title="구직자 공급량 (건)",
            plot_bgcolor="rgba(255,255,255,0.95)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_scatter, use_container_width=True)
        st.caption(f"✅ 실데이터 연동: {real_mart_path}")
    else:
        st.info("📭 **데이터 연동 필요** — 직무별 수요-공급 마트 실데이터가 아직 연동되지 않았습니다. (현재는 기획/전략 직무만 이 차트에 연동 가능한 구조입니다)")

    st.write("---")

    # ② 시계열 검색량 변동성(Volatility) 분석
    st.subheader("② 시계열 검색량 변동성(Volatility) 분석")
    if df_mart is not None:
        vol_skills = st.multiselect("트렌드 시계열 분석 대상 스킬 (최대 4개)", df_mart["자격증명"].tolist(), default=df_mart["자격증명"].tolist()[:3])
        if vol_skills and months_cols:
            fig_vol = go.Figure()
            all_avg = df_mart[months_cols].mean()
            fig_vol.add_trace(go.Scatter(x=months_labels, y=all_avg.values, mode="lines", name="전체 평균", line=dict(color="#94a3b8", width=1.5, dash="dot")))

            for sk in vol_skills:
                row = df_mart[df_mart["자격증명"] == sk]
                if not row.empty:
                    vals = [float(row[c].values[0]) for c in months_cols]
                    fig_vol.add_trace(go.Scatter(x=months_labels, y=vals, mode="lines+markers", name=sk, line=dict(width=2.5)))

            peak_idx = int(all_avg.values.argmax())
            peak_label = months_labels[peak_idx]
            fig_vol.add_trace(go.Scatter(
                x=[peak_label, peak_label], y=[0, 100], mode="lines",
                name=f"🔥 피크 ({peak_label})",
                line=dict(color="#f97316", width=1.5, dash="dash"), showlegend=True
            ))
            fig_vol.update_layout(
                title=dict(text=f"[{selected_job}] 검색 관심도 트렌드", font=dict(size=13)),
                xaxis_title="연월",
                yaxis_title="상대적 검색비율 (%)",
                plot_bgcolor="rgba(255,255,255,0.95)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=400,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_vol, use_container_width=True)
            st.caption(f"✅ 실데이터 연동: {real_mart_path}")
        else:
            st.info("스킬을 선택하십시오.")
    else:
        st.info("📭 **데이터 연동 필요** — 현재 선택된 직무의 시계열 검색비율 실데이터가 연동되지 않았습니다.")

    st.write("---")

    # ③ 네이버 취업 준비 콘텐츠 분석 (TF-IDF)
    st.subheader("③ 네이버 취업 준비 콘텐츠 분석 (TF-IDF)")
    st.markdown("구직자들이 취업 준비 과정에서 네이버 블로그·카페·지식iN에 남긴 글의 핵심 키워드 중요도 분석 결과입니다.")

    naver_text_df, naver_text_col, naver_text_source_label = None, "제목", None
    if selected_job == "데이터분석가/AI엔지니어" and df_it_content is not None:
        naver_text_df, naver_text_col, naver_text_source_label = df_it_content, "title", it_content_path
    elif df_naver is not None:
        naver_text_df, naver_text_col, naver_text_source_label = df_naver, "제목", naver_path

    if naver_text_df is not None:
        from sklearn.feature_extraction.text import TfidfVectorizer
        korean_stopwords = {
            '하는', '있다', '합니다', '대한', '있는', '준비', '시험', '데이터', '분석', '분석가',
            '어떻게', '바로', '공부', '준비하는', '자격증', '방법', '시험이', '대해서', '관련',
            '데이터분석', '취업', '독취사', '네이버', '카페', '글링크', '요약', '제목', '경우',
            '통해', '가지', '때문에', '그리고', '해서', '생각', '진행', '이후', '현재', '일부'
        }
        try:
            vectorizer_title = TfidfVectorizer(
                token_pattern=r'(?u)\b[a-zA-Z가-힣]{2,}\b',
                stop_words=list(korean_stopwords),
                max_features=100
            )
            tfidf_matrix = vectorizer_title.fit_transform(naver_text_df[naver_text_col].fillna(''))
            feature_names = vectorizer_title.get_feature_names_out()
            mean_tfidf = np.asarray(tfidf_matrix.mean(axis=0)).ravel()
            df_tfidf = pd.DataFrame({'word': feature_names, 'tfidf': mean_tfidf}).sort_values(by='tfidf', ascending=False).head(15)

            fig_text = go.Figure()
            fig_text.add_trace(go.Bar(
                x=df_tfidf['tfidf'][::-1],
                y=df_tfidf['word'][::-1],
                orientation='h',
                marker_color='#16a085',
                hovertemplate="키워드: %{y}<br>TF-IDF 중요도: %{x:.4f}<extra></extra>"
            ))
            fig_text.update_layout(
                title="<b>네이버 취업 준비 콘텐츠 핵심 키워드 TOP 15</b>",
                xaxis_title="평균 TF-IDF 중요도",
                yaxis_title="키워드",
                plot_bgcolor="rgba(255,255,255,0.9)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=450
            )
            st.plotly_chart(fig_text, use_container_width=True)
            st.caption(f"✅ 실데이터 연동: {naver_text_source_label} ({len(naver_text_df):,}건)")
        except Exception as e:
            st.error(f"텍스트 TF-IDF 분석 중 오류 발생: {e}")
    else:
        st.info("📭 **데이터 연동 필요** — 현재 선택된 직무의 네이버 취업 준비 콘텐츠 실데이터가 아직 연동되지 않았습니다. (현재는 데이터분석가/AI엔지니어 직무만 연동됨)")

    # =====================================================================
    # IT개발·데이터 직무: 기업 요구 vs 네이버 취업 준비 관심도 비교 (1차 실데이터 연동)
    # UI/정보구조: 요약 카드 -> TOP10(관심/요구) -> GAP TOP5x2(인사이트 포함) -> 비교표
    # =====================================================================
    if selected_job == "데이터분석가/AI엔지니어":
        st.write("---")
        st.write("### 🔍 IT개발·데이터 — 기업 요구 vs 네이버 취업 준비 관심도 비교 (1차 실데이터 버전)")
        st.caption(
            "ℹ️ 구직자 관심도는 실제 구직자 수가 아니라 네이버 취업 관련 콘텐츠에서 "
            "해당 키워드가 등장한 상대적 수준입니다."
        )

        if df_it_gap is not None:
            # --- 0. 요약 카드 (10초 요약) ---
            source_counts = df_it_content["source"].value_counts() if df_it_content is not None else pd.Series(dtype=int)
            biggest_gap_row = df_it_gap.loc[df_it_gap["gap_score"].abs().idxmax()]
            biggest_gap_dir = "기업 요구 > 구직자 관심" if biggest_gap_row["gap_score"] > 0 else "구직자 관심 > 기업 요구"

            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.metric("🏢 기업 분석 키워드 수", f"{len(df_it_company):,} 개")
            with sc2:
                st.metric("💬 네이버 취업 콘텐츠 총 건수", f"{len(df_it_content):,} 건" if df_it_content is not None else "데이터 없음")
            with sc3:
                st.metric(
                    "📊 blog / cafe / kin",
                    f"{source_counts.get('blog', 0):,} / {source_counts.get('cafe', 0):,} / {source_counts.get('kin', 0):,}"
                )
            with sc4:
                st.metric(
                    "⚠️ 최대 미스매치 키워드",
                    biggest_gap_row["representative_keyword"],
                    delta=biggest_gap_dir,
                    delta_color="off"
                )
            st.caption(f"✅ 실데이터 연동: {it_company_path} · {it_jobseeker_path}" + (f" · {it_content_path}" if it_content_path else ""))

            st.write("---")

            # --- 1. TOP10 차트 2개 (관심 / 요구) ---
            col_it1, col_it2 = st.columns(2)

            with col_it1:
                st.subheader("① 네이버 취업 준비 관심 TOP10")
                st.caption("※ '검색량'이 아니라 **네이버 취업 관련 콘텐츠 문서 수**(블로그+카페+지식iN, 중복 제거) 기준입니다.")
                top_jobseeker = df_it_jobseeker.sort_values("unique_document_count", ascending=False).head(10)
                fig_top_jobseeker = go.Figure()
                fig_top_jobseeker.add_trace(go.Bar(
                    x=top_jobseeker["representative_keyword"],
                    y=top_jobseeker["unique_document_count"],
                    text=top_jobseeker["unique_document_count"],
                    textposition="outside",
                    marker_color="#818cf8",
                    customdata=top_jobseeker[["blog_document_count", "cafe_document_count", "kin_document_count"]].values,
                    hovertemplate=(
                        "키워드: %{x}<br>"
                        "취업 관련 콘텐츠 문서 수: %{y}건<br>"
                        "블로그: %{customdata[0]}건 · 카페: %{customdata[1]}건 · 지식iN: %{customdata[2]}건"
                        "<extra></extra>"
                    )
                ))
                fig_top_jobseeker.update_layout(
                    title="<b>취업 관련 콘텐츠 문서 수 TOP10</b>",
                    xaxis_title="스펙/키워드",
                    yaxis_title="취업 관련 콘텐츠 문서 수 (건)",
                    plot_bgcolor="rgba(255,255,255,0.9)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=420
                )
                st.plotly_chart(fig_top_jobseeker, use_container_width=True)
                st.caption(f"✅ 실데이터 연동: {it_jobseeker_path}")

            with col_it2:
                st.subheader("② 기업 요구 스펙 TOP10")
                st.caption("※ 채용 공고 자격요건·우대사항 텍스트의 가중 TF-IDF 스코어(frequency_score) 기준입니다.")
                top_company = df_it_company.sort_values("company_demand_raw", ascending=False).head(10)
                fig_top_company = go.Figure()
                fig_top_company.add_trace(go.Bar(
                    x=top_company["representative_keyword"],
                    y=top_company["company_demand_raw"],
                    text=[f"{v:,.0f}" for v in top_company["company_demand_raw"]],
                    textposition="outside",
                    marker_color="#fb7185",
                    hovertemplate="스펙: %{x}<br>가중 TF-IDF 스코어: %{y:,.1f}<extra></extra>"
                ))
                fig_top_company.update_layout(
                    title="<b>기업 공고 가중 TF-IDF 스코어 TOP10</b>",
                    xaxis_title="스펙/키워드",
                    yaxis_title="가중 TF-IDF 스코어",
                    plot_bgcolor="rgba(255,255,255,0.9)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=420
                )
                st.plotly_chart(fig_top_company, use_container_width=True)
                st.caption(f"✅ 실데이터 연동: {it_company_path}")

            st.write("---")

            # --- 2. GAP TOP5 x 2 (기업>구직자 / 구직자>기업), 각각 페어 바 차트 + 자동 인사이트 ---
            st.subheader("③ 기업 요구 vs 구직자 관심 GAP TOP5")

            def render_gap_chart(df_top, chart_title, bar_color_company, bar_color_jobseeker, insight_fn):
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df_top["representative_keyword"], y=df_top["company_demand_score"],
                    name="기업 요구도 (0~100)", marker_color=bar_color_company,
                    text=[f"{v:.0f}" for v in df_top["company_demand_score"]], textposition="outside"
                ))
                fig.add_trace(go.Bar(
                    x=df_top["representative_keyword"], y=df_top["jobseeker_content_score"],
                    name="구직자 관심도 (0~100)", marker_color=bar_color_jobseeker,
                    text=[f"{v:.0f}" for v in df_top["jobseeker_content_score"]], textposition="outside"
                ))
                fig.update_layout(
                    title=f"<b>{chart_title}</b>",
                    barmode="group",
                    xaxis_title="스펙/키워드",
                    yaxis_title="정규화 스코어 (0~100)",
                    yaxis_range=[0, 115],
                    plot_bgcolor="rgba(255,255,255,0.9)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=380,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig, use_container_width=True)
                for line in insight_fn(df_top):
                    st.markdown(f"💡 {line}")

            col_gap1, col_gap2 = st.columns(2)

            with col_gap1:
                st.markdown("**A. 기업 요구 대비 구직자 관심이 낮은 TOP5**")
                top_company_gap = df_it_gap.sort_values("gap_score", ascending=False).head(5)

                def insight_company_gap(df_top):
                    lines = []
                    for _, r in df_top.head(2).iterrows():
                        lines.append(
                            f"**{r['representative_keyword']}**는 기업 요구도({r['company_demand_score']:.0f}점)가 높지만 "
                            f"취업 준비 콘텐츠 언급({r['jobseeker_content_score']:.0f}점)은 상대적으로 낮습니다."
                        )
                    return lines

                render_gap_chart(top_company_gap, "기업 요구 대비 구직자 관심 낮음 TOP5", "#fb7185", "#c7d2fe", insight_company_gap)

            with col_gap2:
                st.markdown("**B. 구직자 관심 대비 기업 요구가 낮은 TOP5**")
                top_jobseeker_gap = df_it_gap.sort_values("gap_score", ascending=True).head(5)

                def insight_jobseeker_gap(df_top):
                    lines = []
                    for _, r in df_top.head(2).iterrows():
                        lines.append(
                            f"**{r['representative_keyword']}**는 취업 준비 콘텐츠에서는 관심({r['jobseeker_content_score']:.0f}점)이 높지만 "
                            f"기업 공고 요구도({r['company_demand_score']:.0f}점)는 상대적으로 낮습니다."
                        )
                    return lines

                render_gap_chart(top_jobseeker_gap, "구직자 관심 대비 기업 요구 낮음 TOP5", "#fca5a5", "#818cf8", insight_jobseeker_gap)

            st.write("---")

            # --- 3. 비교 표 ---
            st.subheader("④ 기업 요구 vs 구직자 관심 비교표")
            df_table = df_it_gap[["representative_keyword", "company_demand_score", "jobseeker_content_score",
                                   "gap_score", "jobseeker_content_raw"]].rename(columns={
                "representative_keyword": "keyword",
                "jobseeker_content_raw": "jobseeker_document_count"
            }).sort_values("gap_score", ascending=False).round(1)
            st.dataframe(df_table, use_container_width=True, hide_index=True)

            st.caption(
                "⚠️ 1차 실데이터 연동 버전(시각화 확인용)입니다. LLM/'지원' 등 일부 키워드의 중의성 보정을 포함한 추가 데이터 정제는 후속 작업에서 진행할 예정입니다."
            )
        else:
            st.info("📭 **데이터 연동 필요** — IT개발·데이터 네이버 실데이터 파일을 찾을 수 없습니다.")

# =====================================================================
# 탭 1. 구직자: 스펙 자가진단 및 스코어링 엔진
# =====================================================================
with tab1:
    st.header(f"💡 [{selected_job}] 구직자 스펙 자가진단 및 적합도 스코어링")
    st.markdown(
        "보유하신 경력/학력/자격증/툴/실무 경험을 토대로 "
        "**실제 기업 공고 조건과 다차원적으로 비교**하여 점수를 진단합니다."
    )
    if df_saramin_job is None:
        st.caption(f"ℹ️ 현재 [{selected_job}] 직무는 실제 채용공고 실데이터가 연동되지 않아, 아래 진단은 보유 스펙 비율 기반 자체 채점 로직으로 계산됩니다 (실공고 매칭은 기획/전략, 데이터분석가/AI엔지니어 직무에서만 가능).")

    # 스킬풀 가져오기
    specs = JOB_SPECS_POOL.get(selected_job, {"licenses": [], "tools": [], "experiences": [], "synonyms": {}})
    
    # 기획/전략 세부 직무 필터링에 따른 진단 스펙 풀 동적 조정
    if selected_job == "기획/전략" and selected_sub_job in ["IT/서비스 기획", "경영/사업 전략"]:
        if selected_sub_job == "IT/서비스 기획":
            specs = {
                "licenses": ["SQLD", "ADsP", "컴퓨터활용능력"],
                "tools": ["Figma", "GA4", "Slack", "Jira", "Tableau"],
                "experiences": ["역기획", "프로토타이핑", "서비스로그 분석", "시장조사 및 리서치"],
                "synonyms": specs["synonyms"]
            }
        else: # 경영/사업 전략
            specs = {
                "licenses": ["CPA", "CFA", "컴퓨터활용능력"],
                "tools": ["Slack", "ERP (더존/SAP)", "Tableau"],
                "experiences": ["M&A 검토", "시장조사 및 리서치", "사업타당성 분석", "예산 및 결산 관리"],
                "synonyms": specs["synonyms"]
            }
            
    licenses_pool = specs["licenses"]
    tools_pool = specs["tools"]
    experiences_pool = specs["experiences"]
    synonyms = specs["synonyms"]

    # 입력 폼
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        user_career = st.selectbox(
            "📅 나의 경력 수준",
            ["신입", "주니어 (1~3년)", "미들 (4~7년)", "시니어 (8년 이상)"],
            key="user_career_py"
        )
    with col_input2:
        user_edu = st.selectbox(
            "🎓 최종 학력",
            ["고졸 이하", "초대졸 (2/3년제)", "대졸 (4년제 학사)", "대학원 (석사/박사)"],
            key="user_edu_py"
        )

    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        user_licenses = st.multiselect("보유 자격증", options=licenses_pool, default=[])
    with col_sel2:
        user_tools = st.multiselect("사용 가능한 실무 툴", options=tools_pool, default=[])
    with col_sel3:
        user_experiences = st.multiselect("보유 실무/직무 경험", options=experiences_pool, default=[])

    diagnose_clicked = st.button("📊 나의 다차원 직무 적합도 진단 실행")

    # 경력/학력 변환 함수
    def parse_career_years(s):
        if not isinstance(s, str): return 0
        nums = re.findall(r'\d+', s.lower())
        return int(nums[0]) if nums else 0

    def parse_edu_level(s):
        if not isinstance(s, str): return 0
        s = s.lower()
        if "대학원" in s or "석사" in s or "박사" in s: return 3
        elif "대졸" in s or "학사" in s or "대학교" in s: return 2
        elif "전문대" in s or "초대졸" in s: return 1
        return 0

    user_career_val = {"신입": 0, "주니어 (1~3년)": 2, "미들 (4~7년)": 5, "시니어 (8년 이상)": 10}[user_career]
    user_edu_val = {"고졸 이하": 0, "초대졸 (2/3년제)": 1, "대졸 (4년제 학사)": 2, "대학원 (석사/박사)": 3}[user_edu]
    user_skills = user_licenses + user_tools + user_experiences

    if diagnose_clicked or user_skills:
        # 스코어링 알고리즘 작동 (선택 직무의 실제 채용공고 실데이터가 있으면 매칭, 없으면 보유 스펙 비율 기반 산출)
        if df_saramin_job is not None:
            total_scores = []
            for _, row in df_saramin_job.iterrows():
                # 경력/학력 스코어
                req_career = parse_career_years(row.get("career", ""))
                career_score = 100 if user_career_val >= req_career else 0
                req_edu = parse_edu_level(row.get("education", ""))
                edu_score = 100 if user_edu_val >= req_edu else 0
                
                text = (str(row.get("sectors", "")) + " " +
                        str(row.get("title", "")) + " " +
                        str(row.get("detail_content", ""))).lower()
                
                # 자격증 매칭
                needed_lic = [l for l in licenses_pool if any(k in text for k in synonyms.get(l, [l.lower()]))]
                lic_score = 100 if not needed_lic else (sum(1 for l in needed_lic if l in user_licenses) / len(needed_lic)) * 100
                
                # 실무 툴 매칭
                needed_tools = [t for t in tools_pool if any(k in text for k in synonyms.get(t, [t.lower()]))]
                tool_score = 100 if not needed_tools else (sum(1 for t in needed_tools if t in user_tools) / len(needed_tools)) * 100
                
                # 직무 경험 매칭
                needed_exps = [e for e in experiences_pool if any(k in text for k in synonyms.get(e, [e.lower()]))]
                exp_score = 100 if not needed_exps else (sum(1 for e in needed_exps if e in user_experiences) / len(needed_exps)) * 100
                
                total_scores.append(
                    career_score * 0.2 + edu_score * 0.2 + lic_score * 0.2 +
                    tool_score * 0.2 + exp_score * 0.2
                )
            suitability_score = float(np.clip(np.mean(total_scores), 0, 100)) if total_scores else 0.0
        else:
            # 타 직무 가상 매칭 (선택된 스펙 개수 / 전체 스펙 개수 기반 보정)
            total_pool = len(licenses_pool) + len(tools_pool) + len(experiences_pool)
            ratio = (len(user_skills) / total_pool) if total_pool > 0 else 0.0
            suitability_score = float(np.clip(ratio * 70 + (user_career_val * 2) + (user_edu_val * 4), 0, 100))

        # 미보유 추천 스펙 TOP 3 도출
        unselected = (
            [(l, "자격증") for l in licenses_pool if l not in user_licenses] +
            [(t, "실무 툴") for t in tools_pool if t not in user_tools] +
            [(e, "직무 경험") for e in experiences_pool if e not in user_experiences]
        )
        missing_specs = unselected[:3]

        st.subheader("📋 다차원 직무 적합도 진단 결과")
        c_res1, c_res2 = st.columns([1, 2])
        with c_res1:
            st.metric(
                "종합 직무 적합도 점수",
                f"{suitability_score:.1f}점",
                help="경력 20% + 학력 20% + 자격증 20% + 실무툴 20% + 직무경험 20%"
            )
        with c_res2:
            st.markdown(f"##### ⚠️ 탑티어 {selected_job} 전문가 도약을 위해 우선순위로 채워야 할 스펙 TOP 3")
            if missing_specs:
                for idx, (item, cat) in enumerate(missing_specs):
                    st.warning(f"**{idx+1}순위: {item}** ({cat})")
            else:
                st.success("🎉 축하합니다! 해당 직무군 핵심 요구 스펙을 모두 체크하셨습니다.")
                
        # 추가 요구사항: 점수 산정 기준 및 점수 향상 전략
        st.write("---")
        col_std1, col_std2 = st.columns(2)
        
        with col_std1:
            st.markdown("#### 📊 직무 적합도 점수 산정 기준")
            st.markdown(
                (f"본 자가진단의 종합 스코어는 [{selected_job}] 실제 채용 공고 텍스트 매칭율을 토대로 "
                 if df_saramin_job is not None else
                 "본 자가진단의 종합 스코어는 (실데이터 매칭 전까지) 보유 스펙 비율 기반 자체 채점 로직으로 ") +
                "**5개 차원의 가중치 합산(각 20% 씩)**으로 계산됩니다."
            )
            
            # 산정 기준 표 구성
            std_data = {
                "평가 항목": ["📅 경력 수준", "🎓 최종 학력", "📜 우대 자격증", "🛠️ 필수 실무 툴", "🔥 실무 직무 경험"],
                "반영 비중": ["20%", "20%", "20%", "20%", "20%"],
                "상세 평가 기준": [
                    "공고 요구 최소 경력(연차) 충족 여부",
                    "지원 직군 요구 최소 학력 조건 충족율",
                    "우대사항 텍스트 내 자격증 매칭 비율",
                    "요구 필수 사용 툴(Figma 등)의 일치율",
                    "직무 프로젝트 수행 경험(로그 분석 등) 매칭율"
                ]
            }
            st.table(pd.DataFrame(std_data))
            
        with col_std2:
            st.markdown("#### 🚀 직무 적합도 점수 향상 및 합격 전략")
            st.markdown(
                f"**선택하신 `{selected_job}` 직무군에서 단기간에 점수를 보완하고 "
                "서류 통과율을 극대화할 수 있는 수석 실무진의 합격 로드맵입니다.**"
            )
            
            st.info(
                "1️⃣ **포트폴리오 중심 실무 툴 & 경험(40% 비중) 우선 확보**\n\n"
                "경력과 학력은 단기 보완이 어렵지만, **실무 툴(Figma/GA4 등)**과 **직무 경험(역기획/A-B테스트 등)**은 "
                "개인 포트폴리오 기획 및 미니 프로젝트를 통해 단기간에 채울 수 있어 점수를 빠르게 올릴 수 있는 치트키 영역입니다."
            )
            st.warning(
                "2️⃣ **과공급 스펙 지양 & 채용난 블루오션 역량 적극 어필**\n\n"
                "컴퓨터활용능력이나 일반 PPT 작성 등의 흔한 자격증보다, 위 EDA 섹션에서 확인한 "
                "수요 대비 공급이 낮은 희소 역량을 보유 역량에 기재하여 희소성을 선점하십시오."
            )
            st.success(
                "3️⃣ **정량 자격증은 직무 지향형으로 조율**\n\n"
                "공급 밀도가 너무 높은 공통 자격증 취득보다는 실제 SQL 작성 및 데이터 조작을 입증하여 실무 연계성이 높은 "
                "**SQLD, ADsP, 빅데이터분석기사** 등을 보조적으로 빠르게 보완하는 것이 유리합니다."
            )
    else:
        st.info("💡 경력/학력/보유 역량을 선택한 뒤 **'나의 다차원 직무 적합도 진단 실행'** 버튼을 누르세요.")


# =====================================================================
# [비활성화] 탭 2(인사팀 Gap 분석) & 탭 3(이직위험 분석)
# 뒷받침할 실데이터 파일(수급 마트, 이직위험 마트)이 아직 연동되지 않아 화면에서 숨겼습니다.
# 아래는 보존용 코드이며 문자열 리터럴이라 실행되지 않습니다.
# 실데이터 연동 시: 이 주석과 여는/닫는 following 잉크 '''를 제거하고,
# st.tabs([...]) unpacking을 tab0, tab1, tab2, tab3 = st.tabs([...4개 라벨...]) 로 되돌리면 복원됩니다.
# =====================================================================
_DISABLED_TAB2_TAB3_SOURCE = '''
# =====================================================================
# 탭 2. 인사팀: 수급 Gap 분석 및 JD 최적화 도구
# =====================================================================
with tab2:
    st.header(f"🏢 [{selected_job}] 인사팀 수급 Gap 분석 및 JD 최적화")
    st.markdown(
        "시장 트렌드를 바탕으로 허수 지원자를 방지하고 채용 성사율을 극대화하는 인사담당자 분석 룸입니다."
    )
    if is_mock:
        mock_badge()

    # --- ① 이중 축 수급 Gap 차트 ---
    st.subheader("📊 스킬별 수급 Gap 비교 분석 차트")
    fig_gap = make_subplots(specs=[[{"secondary_y": True}]])
    fig_gap.add_trace(
        go.Bar(
            x=df_mart["자격증명"], y=df_mart["구직자_공급_건수"],
            name="구직자 관심도 (공급)", marker_color="#818cf8", opacity=0.85,
            hovertemplate="스킬: %{x}<br>구직자 공급: %{y:,.0f}건<extra></extra>"
        ), secondary_y=False
    )
    fig_gap.add_trace(
        go.Bar(
            x=df_mart["자격증명"], y=df_mart["기업_수요_건수"],
            name="실제 기업 우대 빈도 (수요)", marker_color="#fb7185", opacity=0.85,
            hovertemplate="스킬: %{x}<br>기업 수요: %{y}건<extra></extra>"
        ), secondary_y=True
    )
    fig_gap.update_layout(
        barmode="group",
        plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_gap.update_xaxes(title_text="<b>요구 자격증 및 실무 스킬셋</b>")
    fig_gap.update_yaxes(title_text="<b>구직자 공급량 (건)</b>", secondary_y=False)
    fig_gap.update_yaxes(title_text="<b>실제 기업 우대 건수 (건)</b>", secondary_y=True)
    st.plotly_chart(fig_gap, use_container_width=True)

    # --- ② 미스매치 유형별 키워드 자동 분류 카드 ---
    st.subheader("🔍 미스매치 유형별 키워드 자동 분류 인사이트")
    
    # 임계 기준 설정
    oversupply_threshold = -8000
    oversupply_kws = []
    shortage_kws = []

    for _, row in df_mart.iterrows():
        skill = row["자격증명"]
        gap = row["수급Gap(건)"]
        supply = row["구직자_공급_건수"]
        demand = row["기업_수요_건수"]
        avg_ratio = row[months_cols].mean() if months_cols else 0.0

        if gap < oversupply_threshold:
            oversupply_kws.append({
                "키워드": skill, "구직자 공급(건)": supply, "기업 수요(건)": demand, "평균 검색비율(%)": round(avg_ratio, 1)
            })
        elif demand >= 20 and avg_ratio < 50:
            shortage_kws.append({
                "키워드": skill, "구직자 공급(건)": supply, "기업 수요(건)": demand, "평균 검색비율(%)": round(avg_ratio, 1)
            })

    card_col1, card_col2 = st.columns(2)
    with card_col1:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#fef3c7,#fde68a);border-radius:14px;
        padding:20px;border:2px solid #f59e0b;margin-bottom:8px;">
        <h4 style="color:#92400e;margin:0 0 6px 0;font-size:16px;">⚠️ 과공급 위험 키워드 (스펙 낭비 군집)</h4>
        <p style="color:#92400e;font-size:12px;margin:0;">
        구직자의 관심이나 준비량(공급)은 비정상적으로 높으나, 실제 채용 우대사항에선 반영률이 낮은 과밀 스펙입니다.
        </p>
        </div>
        """, unsafe_allow_html=True)
        if oversupply_kws:
            st.dataframe(pd.DataFrame(oversupply_kws), use_container_width=True, hide_index=True)
        else:
            st.caption("해당 분류 키워드가 발견되지 않았습니다.")

    with card_col2:
        st.markdown("""
        <div style="background:linear-gradient(135deg,#fee2e2,#fca5a5);border-radius:14px;
        padding:20px;border:2px solid #ef4444;margin-bottom:8px;">
        <h4 style="color:#7f1d1d;margin:0 0 6px 0;font-size:16px;">🔥 채용난 위험 키워드 (인재 부족 군집)</h4>
        <p style="color:#7f1d1d;font-size:12px;margin:0;">
        기업 우대 요구 빈도는 매우 높으나, 정작 구직자의 트렌드 인지도 및 준비율이 턱없이 모자란 핵심 전문 스펙군입니다.
        </p>
        </div>
        """, unsafe_allow_html=True)
        if shortage_kws:
            st.dataframe(pd.DataFrame(shortage_kws), use_container_width=True, hide_index=True)
        else:
            st.caption("해당 분류 키워드가 발견되지 않았습니다.")

    st.write("---")

    # --- ③ JD(채용공고) 리모델링 시뮬레이터 ---
    st.subheader("🛠️ 채용공고(JD) 리모델링 시뮬레이터")
    
    with st.expander("⚡ JD 리모델링 시뮬레이터 구동", expanded=True):
        sim_col1, sim_col2 = st.columns(2)
        with sim_col1:
            jd_target = st.selectbox(
                "📌 채용 직무 포지션",
                [f"{selected_job} 담당 실무자", f"{selected_job} 시니어 파트장", f"데이터 기반 {selected_job} 전문가"],
                key="jd_target_py"
            )
            jd_skills = st.multiselect(
                "🔑 JD 강조 우대 역량 설정 (수급난 키워드 적극 추천)",
                options=df_mart["자격증명"].tolist(),
                default=df_mart["자격증명"].tolist()[:3] if len(df_mart) >= 3 else df_mart["자격증명"].tolist(),
                key="jd_skills_py"
            )
        with sim_col2:
            jd_tone = st.radio(
                "📣 공고 커뮤니케이션 톤",
                ["친근하고 자유로운 스타트업 톤", "격식 있고 전문적인 대기업 톤", "데이터 중심 테크 톤"],
                key="jd_tone_py"
            )
            jd_experience = st.selectbox(
                "📅 경력 요건 범위",
                ["신입 (0년)", "1~3년 차 주니어", "3~5년 차 미들", "5년 이상 시니어"],
                key="jd_experience_py"
            )

        if st.button("⚡ 미스매치 분석 기반 JD 초안 자동 생성", key="jd_gen_py", type="primary"):
            skills_str = ", ".join(jd_skills) if jd_skills else "직무 핵심 실무 역량"
            tone_map = {
                "친근하고 자유로운 스타트업 톤": "저희와 함께 로켓 성장을 이뤄낼 든든한 동료를 찾습니다! 🚀",
                "격식 있고 전문적인 대기업 톤": "당사 사업 경쟁력 강화를 위한 우수 전문 인재를 아래와 같이 영입하고자 합니다.",
                "데이터 중심 테크 톤": "데이터 지표 설계 및 의사결정을 리드해 주실 데이터 중심 인재를 모십니다. 📊"
            }
            opening = tone_map.get(jd_tone, "")

            # 시장 현황 피드백 계산
            feedback_messages = []
            for sk in jd_skills:
                row = df_mart[df_mart["자격증명"] == sk]
                if not row.empty:
                    gap = int(row["수급Gap(건)"].values[0])
                    if gap < -10000:
                        feedback_messages.append(f"⚠️ **{sk}**: 현재 구직자 공급 과밀 영역입니다. 우대 사항의 장벽으로 작용할 수 있으니 우대 가치를 낮추는 것을 추천합니다.")
                    elif gap > -5000:
                        feedback_messages.append(f"🟢 **{sk}**: 블루오션(채용난) 역량입니다! 우대 조건으로 최상단에 배치하면 인재 유치 경쟁력을 대폭 향상시킬 수 있습니다.")

            st.success("📝 **미스매치 최적화 JD 자동 생성 초안**")
            jd_draft = f"""
            ### [{jd_target}] 채용 공고
            
            **[환영 메시지]**
            {opening}
            
            **[주요 업무]**
            - {selected_job} 관련 비즈니스 전략 수립 및 핵심 KPI 관리
            - 유관 부서와의 긴밀한 커뮤니케이션 및 협업 리드
            
            **[지원 요건]**
            - 경력 수준: {jd_experience}
            - 학력 수준: 학사 학위 이상 보유자
            
            **[우대 사항]**
            - **{skills_str}** 역량 보유자 또는 관련 실무 경험자 극진 우대
            - 시장의 흐름을 읽고 스스로 문제를 해결해 나갈 수 있는 인재
            """
            st.markdown(jd_draft)
            
            if feedback_messages:
                st.info("💡 **시뮬레이터 채용 분석 피드백:**\n\n" + "\n\n".join(feedback_messages))

    st.write("---")

    # --- ④ 채용 전략 제언 ---
    st.subheader("③ 채용 전략 제언")
    strategy_texts = {
        "기획/전략": (
            "인재 부족 영역인 'Figma/M&A' 인재를 유인하기 위해, "
            "구직자 검색 빈도가 높은 키워드를 공고 상단에 의도적으로 배치(JD Optimization)하고 "
            "사내 기획자 양성 로드맵을 선제 공개하십시오. "
            "컴퓨터활용능력·PPT작성법 등 과공급 키워드는 과감히 축소 배치하세요."
        ),
        "인사/노무": (
            "노동법·컴플라이언스 전문 인재의 공급이 크게 부족합니다. "
            "공인노무사 자격 보유자뿐 아니라 노동법 실무 경험자도 우대 범위에 포함시키고, "
            "인사 ERP 활용 역량을 JD에 명시하여 디지털 HR 인재를 확보하세요."
        ),
        "회계/재무": (
            "CPA·세무사 자격의 공급 과잉에 비해 IFRS·SAP·AICPA 등 글로벌 재무 역량은 "
            "심각한 공급 부족 상태입니다. 국제 회계 기준 경험자를 우대하고, "
            "엑셀(VBA) 고급 활용 역량을 별도 기술 요건으로 분리 기술하세요."
        ),
        "감사/컴플라이언스": (
            "내부감사·리스크관리 수요가 급증하지만 CISA·CIA 보유 인재는 극소수입니다. "
            "감사 직무 경력 3년 이상이면 자격증 대신 실무 역량을 우대하는 JD 리모델링이 필요합니다. "
            "데이터 기반 감사(Data Analytics Audit) 역량을 전면 배치하세요."
        ),
        "마케팅": (
            "GA4·Google Ads 등 퍼포먼스 마케팅 역량의 수요가 급증하나, "
            "구직자들은 여전히 브랜드전략·콘텐츠마케팅 등 전통적 역량에 집중하고 있습니다. "
            "마케팅자동화(HubSpot/Braze 등) 실무 경험을 JD 최우선 요건으로 격상하세요."
        ),
        "데이터분석가/AI엔지니어": (
            "Python·SQL 역량은 공급이 과잉이나, TensorFlow/PyTorch 딥러닝 실전 경험과 "
            "AWS/GCP 클라우드 ML 파이프라인 역량은 극심한 채용난 상태입니다. "
            "Spark 대규모 처리 경험자를 우대하고, 빅데이터분석기사 자격을 보조 우대로 배치하세요."
        ),
    }

    advice = strategy_texts.get(selected_job, "해당 직무의 전략 제언이 준비 중입니다.")
    st.info(f"💡 **[{selected_job}] 채용 전략 제언**\n\n{advice}")


# =====================================================================
# 탭 3. 기업 이직위험 & 채용건전성 분석
# =====================================================================
with tab3:
    st.header("⚠️ 기업 이직위험 및 채용 건전성 분석")
    st.markdown(
        "사람인 공고 분석 기반 기업 건전성 마트 데이터를 토대로, "
        "기업들의 구인 빈도 패턴과 악성 순환(Toxic Rotation) 채용 구조를 추적하여 고용의 건전성을 탐색합니다."
    )
    
    # 데이터 유무에 따른 로드 및 Fallback 분기
    if df_turnover is not None:
        df_t = df_turnover
        st.success(f"📊 실제 이직위험 데이터마트 분석 엔진이 활성화되었습니다. (총 {len(df_t)}개사 분석 진행 중)")
    else:
        # Fallback Mock Data 생성
        import random
        sectors_mock = ["IT/웹에이전시", "제조/화학", "유통/무역", "서비스업", "물류/배송", "금융/은행", "의료/제약", "교육업", "건설업", "미디어/디자인"]
        mock_list = []
        for _ in range(300):
            emp = random.randint(5, 5000)
            sec = random.choice(sectors_mock)
            score = max(0, min(100, 80 - 10 * np.log10(emp) + random.normalvariate(0, 15)))
            level = "High" if score > 60 else ("Medium" if score > 35 else "Low")
            toxic = 1 if (sec in ["물류/배송", "서비스업"] and random.random() > 0.4) else (1 if random.random() > 0.8 else 0)
            interval = random.uniform(2, 14) if toxic == 1 else random.uniform(15, 60)
            mock_list.append({
                "company": f"가상기업_{random.randint(100, 999)}",
                "employee_count": emp,
                "primary_sector": sec,
                "turnover_risk_score": score,
                "turnover_risk_level": level,
                "is_toxic_rotation": toxic,
                "reposting_interval_days": interval
            })
        df_t = pd.DataFrame(mock_list)
        mock_badge()
        
    # 요약 통계 카드
    st.write("### 🔑 채용 건전성 주요 요약 지표")
    t_col1, t_col2, t_col3, t_col4 = st.columns(4)
    with t_col1:
        avg_risk = df_t['turnover_risk_score'].mean()
        st.metric(label="📉 평균 이직 위험 점수", value=f"{avg_risk:.1f} 점")
    with t_col2:
        high_risk_ratio = (df_t['turnover_risk_level'] == 'High').mean() * 100
        st.metric(label="🚨 고위험(High Risk) 기업 비율", value=f"{high_risk_ratio:.1f} %")
    with t_col3:
        avg_interval = df_t['reposting_interval_days'].dropna().mean()
        st.metric(label="📅 평균 공고 재등록 주기", value=f"{avg_interval:.1f} 일")
    with t_col4:
        toxic_ratio = df_t['is_toxic_rotation'].mean() * 100
        st.metric(label="⚠️ 악성 구인 순환 기업 비율", value=f"{toxic_ratio:.1f} %")
        
    st.write("---")
    
    # 1. 업종별 평균 이직 위험도 & 2. 사원수와 이직 위험도 관계
    col_t_g1, col_t_g2 = st.columns(2)
    
    with col_t_g1:
        st.subheader("① 업종별 평균 이직 위험 점수 비교")
        df_t_sector = df_t.groupby('primary_sector')['turnover_risk_score'].mean().sort_values(ascending=False).reset_index().head(15)
        
        fig_t1 = go.Figure()
        fig_t1.add_trace(go.Bar(
            x=df_t_sector['primary_sector'],
            y=df_t_sector['turnover_risk_score'],
            marker_color='#e74c3c',
            hovertemplate="업종: %{x}<br>평균 이직위험 점수: %{y:.1f}점<extra></extra>"
        ))
        fig_t1.update_layout(
            xaxis_title="업종 분류",
            yaxis_title="평균 이직위험 점수 (점)",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=400,
            xaxis=dict(tickangle=45)
        )
        st.plotly_chart(fig_t1, use_container_width=True)
        st.caption("💡 **분석 결과:** 물류, 고객 서비스 및 단순 유통 성격의 업종이 높은 평균 이직 위험 수치를 보이며, 고용 안정도가 취약한 양상을 띠고 있습니다.")
        
    with col_t_g2:
        st.subheader("② 기업 사원 수와 이직 위험 점수 상관관계")
        fig_t2 = go.Figure()
        fig_t2.add_trace(go.Scatter(
            x=df_t['employee_count'],
            y=df_t['turnover_risk_score'],
            mode='markers',
            marker=dict(
                size=8,
                color=df_t['turnover_risk_score'],
                colorscale='Reds',
                showscale=True,
                colorbar=dict(title="이직 위험도")
            ),
            text=df_t['company'] if 'company' in df_t.columns else None,
            hovertemplate="회사: %{text}<br>사원수: %{x}명<br>이직위험점수: %{y:.1f}점<extra></extra>"
        ))
        fig_t2.update_layout(
            xaxis_title="사원 수 (명, 로그 스케일)",
            yaxis_title="이직 위험 점수 (점)",
            xaxis=dict(type="log"),
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=400
        )
        st.plotly_chart(fig_t2, use_container_width=True)
        st.caption("💡 **분석 결과:** 기업의 사원 규모(사원 수)가 작아질수록 평균적인 이직위험도가 확연히 높게 군집되어 있으며, 소기업 중심의 고용 유지가 만성적인 과제로 파악됩니다.")

    st.write("---")
    
    # 3. 악성 순환별 재등록 주기 & 4. 주요 업종별 악성 순환 비율
    col_t_g3, col_t_g4 = st.columns(2)
    
    with col_t_g3:
        st.subheader("③ 악성 구인 순환 여부별 공고 재등록 주기 비교")
        df_clean_interval = df_t[df_t['reposting_interval_days'].notnull()]
        
        fig_t3 = go.Figure()
        fig_t3.add_trace(go.Box(
            y=df_clean_interval[df_clean_interval['is_toxic_rotation'] == 0]['reposting_interval_days'],
            name="정상 고용 기업",
            marker_color='#3498db',
            boxpoints='outliers'
        ))
        fig_t3.add_trace(go.Box(
            y=df_clean_interval[df_clean_interval['is_toxic_rotation'] == 1]['reposting_interval_days'],
            name="악성 순환 기업",
            marker_color='#e74c3c',
            boxpoints='outliers'
        ))
        fig_t3.update_layout(
            yaxis_title="공고 재등록 주기 (일)",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=400
        )
        st.plotly_chart(fig_t3, use_container_width=True)
        st.caption("💡 **분석 결과:** 악성 채용 순환(Toxic Rotation) 징후가 감지된 기업들은 공고 재등록 주기가 평균 10일 이내로 밀접하게 집중되어 상시적 채용 소모전이 이어지고 있습니다.")
        
    with col_t_g4:
        st.subheader("④ 주요 업종별 악성 채용 순환 비율 (%)")
        top_sectors = df_t['primary_sector'].value_counts().head(10).index
        df_top_sectors = df_t[df_t['primary_sector'].isin(top_sectors)]
        
        crosstab_t = pd.crosstab(df_top_sectors['primary_sector'], df_top_sectors['is_toxic_rotation'], normalize='index') * 100
        crosstab_t = crosstab_t.reset_index()
        
        # 0과 1 컬럼 보장
        if 0 not in crosstab_t.columns:
            crosstab_t[0] = 0.0
        if 1 not in crosstab_t.columns:
            crosstab_t[1] = 0.0
            
        fig_t4 = go.Figure()
        fig_t4.add_trace(go.Bar(
            x=crosstab_t['primary_sector'],
            y=crosstab_t[0],
            name="정상 채용",
            marker_color='#3498db',
            hovertemplate="업종: %{x}<br>정상 채용: %{y:.1f}%<extra></extra>"
        ))
        fig_t4.add_trace(go.Bar(
            x=crosstab_t['primary_sector'],
            y=crosstab_t[1],
            name="악성 순환 (Toxic)",
            marker_color='#e74c3c',
            hovertemplate="업종: %{x}<br>악성 순환: %{y:.1f}%<extra></extra>"
        ))
        fig_t4.update_layout(
            barmode='stack',
            xaxis_title="업종 분류",
            yaxis_title="비율 (%)",
            plot_bgcolor="rgba(255,255,255,0.9)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=400,
            xaxis=dict(tickangle=45),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_t4, use_container_width=True)
        st.caption("💡 **분석 결과:** 서비스 및 운수물류 등 특정 대면 직무/업종에서 정상 채용 대비 악성 순환 징후의 상대적 비율이 높게 누적되어 있음이 통계적으로 감지되었습니다.")

'''
# =====================================================================
# 푸터
# =====================================================================
st.write("---")
st.caption(
    "📊 취업 시장 다차원 EDA & 직무 적합도 진단 솔루션 (SaaS) — 1차 실데이터 연동 버전 | "
    "실제로 연동된 데이터 파일이 없는 직무·구간은 '데이터 연동 필요'로 표시됩니다. "
    "탭2(인사팀 Gap 분석)·탭3(이직위험 분석)은 뒷받침할 실데이터가 아직 없어 현재 비활성화되어 있습니다."
)
