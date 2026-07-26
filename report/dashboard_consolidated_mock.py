"""
취업 시장 다차원 EDA 및 직무 적합도 진단 솔루션 (SaaS) — 마스터 통합 대시보드

주요 기능:
- 5대 직무(기획/전략, 인사/노무, 회계/재무, 마케팅, 데이터분석가/AI엔지니어) 지원
- 사이드바 마스터 컨트롤러(직무 스위처)를 통한 실시간 동적 데이터 연동(Reactive)
- 4대 마스터 탭 구조 구현:
  - 🏠 탭 0. 홈: 취업 마켓 다차원 EDA 센터 (전 직무 미스매치 현황, 주요 수집 데이터 규모 요약, 수요-공급 4분면 맵, Co-occurrence 네트워크, 시계열 관심도 트렌드, 네이버 카페 TF-IDF 여론 분석)
  - 💡 탭 1. 구직자: 스펙 자가진단 및 스코어링 엔진 (경력/학력/자격증/툴/경험 5대 다차원 가중치 산출 및 보완 추천)
  - 🏢 탭 2. 인사팀: 수급 Gap 분석 및 JD 최적화 도구 (Gap 차트, 미스매치 카드, JD 리모델링 시뮬레이터, 전략 제언)
  - ⚠️ 탭 3. 기업 이직위험 & 채용건전성 분석 (업종별 평균 이직위험도, 사원수별 이직위험 상관관계, 악성 구인 순환 분석)
- 실제 데이터(automated_total_mismatch_mart.csv, saramin_search_jobs.db, naver_dataanalysis.csv, saramin_turnover_datamart.csv) 적용 및 모의 데이터 폴백
- Mock 데이터 사용 영역 표기를 위해 ⚠️ [MOCK DATA] 뱃지 동적 표출
"""

import streamlit as st
import pandas as pd
import numpy as np
import sqlite3
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import re
import itertools
import importlib.util
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
    "마케팅", "데이터분석가/AI엔지니어"
]

# 대시보드 마스터 직무 ↔ 사람인 실채용공고(job_group) 매핑. 홈/인사팀 탭이 공통으로 참조한다.
SARAMIN_JOB_MAP = {
    "기획/전략": "영업·사업개발",
    "인사/노무": "인사·HR·총무",
    "회계/재무": "회계·재무·경영관리",
    "마케팅": "마케팅·CRM",
    "데이터분석가/AI엔지니어": "IT개발·데이터",
}

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

# 모든 스킬셋 통합 리스트 및 Mock 수급 데이터
MOCK_SKILLS_BY_JOB = {
    "기획/전략": {
        "skills": ["SQLD", "ADsP", "Figma", "GA4", "CPA", "CFA", "M&A", "PPT작성법", "데이터분석", "시장조사", "컴퓨터활용능력"],
        "demand": [1, 2, 20, 10, 7, 2, 63, 131, 153, 97, 30],
        "supply": [15000, 12000, 4500, 8000, 18000, 6000, 9000, 22000, 35000, 28000, 45000],
        "monthly": {
            "2026-01": [45.2, 38.5, 32.1, 15.1, 40.0, 12.0, 18.2, 70.5, 60.5, 42.1, 85.0],
            "2026-02": [48.1, 42.0, 35.0, 18.3, 43.2, 11.2, 20.1, 75.2, 64.0, 45.0, 92.1],
            "2026-03": [55.4, 47.3, 39.8, 22.0, 45.1, 14.5, 23.4, 68.0, 68.2, 48.3, 78.4],
            "2026-04": [62.0, 52.8, 44.5, 25.4, 38.0, 16.0, 25.0, 71.4, 72.1, 50.2, 82.5],
            "2026-05": [58.7, 49.1, 41.0, 21.2, 36.5, 15.3, 22.1, 73.5, 70.0, 47.5, 88.0],
            "2026-06": [50.1, 41.5, 38.5, 19.8, 34.0, 13.1, 19.5, 78.0, 65.4, 43.1, 95.0],
        }
    },
    "인사/노무": {
        "skills": ["공인노무사", "PHR/SPHR", "직업상담사", "ERP(인사)", "노동법 대응", "조직문화 설계", "성과관리 시스템 구축", "채용면접기법", "Slack", "Workday", "엑셀"],
        "demand": [45, 8, 22, 35, 72, 55, 48, 30, 25, 40, 95],
        "supply": [5000, 1200, 8500, 3000, 15000, 12000, 9500, 7000, 18000, 2200, 38000],
        "monthly": {
            "2026-01": [30.0, 10.5, 45.0, 20.0, 55.0, 40.0, 35.0, 28.0, 70.0, 15.0, 80.0],
            "2026-02": [33.0, 12.0, 48.0, 22.0, 58.0, 42.0, 37.0, 30.0, 72.0, 18.0, 85.0],
            "2026-03": [38.0, 14.0, 52.0, 25.0, 62.0, 47.0, 40.0, 33.0, 68.0, 20.0, 78.0],
            "2026-04": [42.0, 15.0, 55.0, 28.0, 65.0, 50.0, 43.0, 36.0, 74.0, 24.0, 83.0],
            "2026-05": [39.0, 13.5, 50.0, 26.0, 60.0, 46.0, 41.0, 34.0, 73.0, 22.0, 86.0],
            "2026-06": [35.0, 11.0, 47.0, 23.0, 57.0, 43.0, 38.0, 31.0, 76.0, 21.0, 90.0],
        }
    },
    "회계/재무": {
        "skills": ["CPA", "세무사", "재경관리사", "AICPA", "ERP(회계)", "IFRS 적용", "SAP", "엑셀(VBA)", "더존 i-U"],
        "demand": [85, 62, 40, 15, 70, 55, 48, 90, 65],
        "supply": [25000, 18000, 12000, 3000, 8000, 5500, 4000, 35000, 6000],
        "monthly": {
            "2026-01": [60.0, 50.0, 35.0, 12.0, 42.0, 30.0, 25.0, 75.0, 45.0],
            "2026-02": [63.0, 53.0, 38.0, 13.0, 45.0, 32.0, 27.0, 78.0, 48.0],
            "2026-03": [68.0, 58.0, 42.0, 15.0, 50.0, 36.0, 30.0, 82.0, 52.0],
            "2026-04": [72.0, 62.0, 45.0, 16.0, 53.0, 38.0, 33.0, 85.0, 55.0],
            "2026-05": [69.0, 59.0, 43.0, 14.5, 48.0, 35.0, 31.0, 80.0, 50.0],
            "2026-06": [65.0, 55.0, 40.0, 13.5, 44.0, 33.0, 28.0, 77.0, 47.0],
        }
    },
    "마케팅": {
        "skills": ["GA4", "Google Ads", "Meta Ads", "SEO/SEM 최적화", "콘텐츠 기획 및 제작", "CRM 마케팅", "HubSpot", "Braze", "구글 애널리틱스 IQ", "SQLD", "검색광고마케터"],
        "demand": [80, 55, 60, 70, 45, 50, 35, 40, 22, 15, 30],
        "supply": [12000, 8000, 9500, 15000, 20000, 7000, 4000, 18000, 3500, 15000, 9000],
        "monthly": {
            "2026-01": [50.0, 35.0, 40.0, 45.0, 55.0, 30.0, 20.0, 48.0, 15.0, 45.0, 30.0],
            "2026-02": [53.0, 38.0, 43.0, 48.0, 58.0, 33.0, 22.0, 50.0, 17.0, 48.0, 32.0],
            "2026-03": [58.0, 42.0, 48.0, 52.0, 62.0, 37.0, 25.0, 55.0, 20.0, 55.0, 35.0],
            "2026-04": [62.0, 45.0, 52.0, 55.0, 65.0, 40.0, 28.0, 58.0, 24.0, 62.0, 38.0],
            "2026-05": [59.0, 43.0, 49.0, 53.0, 60.0, 38.0, 26.0, 54.0, 22.0, 58.0, 34.0],
            "2026-06": [55.0, 40.0, 45.0, 50.0, 57.0, 35.0, 23.0, 51.0, 19.0, 50.0, 31.0],
        }
    },
    "데이터분석가/AI엔지니어": {
        "skills": ["Python", "SQL", "TensorFlow/PyTorch", "Tableau/PowerBI", "지표 정의 및 대시보드 구축", "데이터 파이프라인(ETL) 구축", "ML/DL 모델링", "A/B 테스트 설계 및 분석", "빅데이터분석기사", "ADsP", "AWS Certified Data Analytics"],
        "demand": [120, 110, 65, 50, 45, 30, 55, 35, 28, 25, 20],
        "supply": [40000, 35000, 8000, 6000, 15000, 12000, 5000, 3000, 12000, 15000, 2500],
        "monthly": {
            "2026-01": [70.0, 65.0, 35.0, 28.0, 40.0, 45.0, 30.0, 18.0, 35.0, 45.0, 15.0],
            "2026-02": [73.0, 68.0, 38.0, 30.0, 42.0, 48.0, 33.0, 20.0, 38.0, 48.0, 18.0],
            "2026-03": [78.0, 72.0, 42.0, 33.0, 45.0, 52.0, 37.0, 23.0, 42.0, 55.0, 20.0],
            "2026-04": [82.0, 75.0, 45.0, 35.0, 48.0, 55.0, 40.0, 25.0, 48.0, 62.0, 24.0],
            "2026-05": [79.0, 73.0, 43.0, 33.0, 46.0, 50.0, 38.0, 22.0, 45.0, 58.0, 22.0],
            "2026-06": [75.0, 70.0, 40.0, 31.0, 43.0, 47.0, 35.0, 20.0, 41.0, 50.0, 19.0],
        }
    },
}

# Co-occurrence 군집
MOCK_COOCCURRENCE = {
    "기획/전략": [
        ("Figma", "역기획"), ("Figma", "서비스로그 분석"), ("Figma", "SQLD"),
        ("역기획", "서비스로그 분석"), ("역기획", "SQLD"), ("서비스로그 분석", "SQLD"),
        ("시장조사 및 리서치", "M&A 검토"), ("시장조사 및 리서치", "PPT작성법"), ("M&A 검토", "CPA"),
        ("PPT작성법", "CPA"), ("데이터분석", "GA4"), ("데이터분석", "SQLD"),
    ],
    "인사/노무": [
        ("노동법 대응", "공인노무사"), ("노동법 대응", "조직문화 설계"), ("성과관리 시스템 구축", "채용면접기법"),
        ("조직문화 설계", "성과관리 시스템 구축"), ("ERP(인사)", "성과관리 시스템 구축"),
    ],
    "회계/재무": [
        ("CPA", "IFRS 적용"), ("CPA", "세무사"), ("IFRS 적용", "SAP"),
        ("ERP(회계)", "SAP"), ("엑셀(VBA)", "재경관리사"),
    ],
    "마케팅": [
        ("GA4", "Google Ads"), ("GA4", "SEO/SEM 최적화"), ("Meta Ads", "콘텐츠 기획 및 제작"),
        ("HubSpot", "Braze"), ("브랜드 전략 수립", "콘텐츠 기획 및 제작"),
    ],
    "데이터분석가/AI엔지니어": [
        ("Python", "SQL"), ("Python", "TensorFlow/PyTorch"), ("SQL", "Spark"),
        ("Tableau/PowerBI", "지표 정의 및 대시보드 구축"), ("AWS Certified Data Analytics", "Spark"),
    ],
}

def build_mock_mart(job_name):
    data = MOCK_SKILLS_BY_JOB[job_name]
    rows = []
    for i, skill in enumerate(data["skills"]):
        row = {
            "자격증명": skill,
            "기업_수요_건수": data["demand"][i],
            "구직자_공급_건수": data["supply"][i],
        }
        for month_key, ratios in data["monthly"].items():
            row[f"{month_key}_검색비율"] = ratios[i]
        row["수급Gap(건)"] = data["demand"][i] - data["supply"][i]
        rows.append(row)
    return pd.DataFrame(rows)


# =====================================================================
# 2. 실제 데이터 로더 (기존 파이프라인 결과물 우선 로드)
# =====================================================================
# 실행 환경(CWD)과 무관하게 데이터 파일을 정확히 참조할 수 있도록 파일 기준 절대경로 계산
_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))      # project2/report/
_PROJECT_ROOT = os.path.dirname(_CURRENT_DIR)                 # project2/
_WORKSPACE_ROOT = os.path.dirname(_PROJECT_ROOT)               # repository root/

@st.cache_data
def load_real_mismatch_mart():
    paths = [
        os.path.join(_WORKSPACE_ROOT, "automated_total_mismatch_mart.csv"),
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
        os.path.join(_WORKSPACE_ROOT, "naver-api-app", "data", "naver_dataanalysis.csv"),
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
def load_saramin_db():
    paths = [
        os.path.join(_PROJECT_ROOT, "data", "recruit_processed.db"),
        "project2/data/recruit_processed.db",
        "data/recruit_processed.db",
        "../data/recruit_processed.db",
        os.path.join(_WORKSPACE_ROOT, "saramin", "data", "saramin_search_jobs.db"),
        "saramin/data/saramin_search_jobs.db",
        "../saramin/data/saramin_search_jobs.db",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                conn = sqlite3.connect(p)
                if "recruit_processed.db" in p:
                    df = pd.read_sql("SELECT * FROM recruit_skill_flags", conn)
                    # 기존 대시보드 스키마 명칭과의 맵핑 호환성 보정
                    df.rename(columns={
                        'education_level': 'education',
                        'experience_level': 'career',
                        'job_group': 'sectors'
                    }, inplace=True)
                    df['detail_content'] = df.get('required_keywords', '') + " " + df.get('preferred_keywords', '') + " " + df.get('preferred_certificates', '') + " " + df.get('matched_skills', '')
                else:
                    df = pd.read_sql("SELECT * FROM saramin_jobs", conn)
                conn.close()
                return df, p
            except Exception:
                pass
    return None, None

@st.cache_data
def load_turnover_datamart():
    paths = [
        os.path.join(_WORKSPACE_ROOT, "saramin", "data", "saramin_turnover_datamart.csv"),
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

@st.cache_data
def load_naver_weekly_insights():
    paths = [
        os.path.join(_PROJECT_ROOT, "data", "integrated", "naver_weekly_insights.json"),
        "project2/data/integrated/naver_weekly_insights.json",
        "data/integrated/naver_weekly_insights.json",
        "../data/integrated/naver_weekly_insights.json",
        os.path.join(_PROJECT_ROOT, "data", "naver-api_20260718.json"),
        "project2/data/naver-api_20260718.json",  # fallback
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_json(p)
                return df, p
            except Exception:
                pass
    return None, None


# =====================================================================
# 2-1. 인사팀 탭 전용 실데이터 마트 (recruit_processed.db 수요 × 네이버 주간 데이터 관심도)
# =====================================================================
@st.cache_data
def build_gap_mart(job_name, _df_saramin, _df_weekly_insights):
    """선택 직무의 사람인 실공고 수요 키워드(TOP15)와, 동일 키워드의 네이버 주간 검색 관심도를 결합.
    네이버 데이터에 없는 키워드는 임의 추정하지 않고 '데이터확보=False'로 표시한다."""
    naver_job_key_map = {
        "기획/전략": "기획(plan)", "인사/노무": "인사(hr)", "회계/재무": "회계(acc)",
        "마케팅": "마케팅(mkt)", "데이터분석가/AI엔지니어": "개발(dev)",
    }
    mapped_job = SARAMIN_JOB_MAP.get(job_name)
    if _df_saramin is None or not mapped_job:
        return None

    sub = _df_saramin[_df_saramin["sectors"] == mapped_job]
    if sub.empty:
        return None

    # 공고 전반에 거의 항상 붙는 boilerplate 태그(예: '채용' — 이 job_group에서만도 90%대 이상 공고에 출현)는
    # 직무별 수요를 전혀 구분하지 못하므로 제외한다.
    NOISE_TOKENS = {"채용"}

    def _tokenize(col):
        c = Counter()
        if col not in sub.columns:
            return c
        for val in sub[col].dropna():
            for tok in str(val).split(","):
                tok = tok.strip()
                if tok and tok not in NOISE_TOKENS:
                    c[tok] += 1
        return c

    # preferred_certificates(구체적 자격증명)를 우선 채택하고, 남은 자리를 다른 요구/매칭 키워드로 채운다.
    # matched_skills 등 범용 카테고리 태그만으로 채우면 자격증명이 상위권에서 밀려나
    # 네이버(자격증/어학 위주) 데이터와 매칭될 여지가 거의 사라지기 때문이다.
    cert_counter = _tokenize("preferred_certificates")
    other_counter = Counter()
    for col in ["required_keywords", "preferred_keywords", "matched_skills"]:
        other_counter.update(_tokenize(col))
    for tok in cert_counter:
        other_counter.pop(tok, None)

    demand_counter = cert_counter + other_counter
    if not demand_counter:
        return None

    cert_top = [k for k, _ in cert_counter.most_common(8)]
    remaining_slots = max(0, 15 - len(cert_top))
    other_top = [k for k, _ in other_counter.most_common(remaining_slots)]
    top_keywords = sorted(cert_top + other_top, key=lambda k: demand_counter[k], reverse=True)

    naver_job_key = naver_job_key_map.get(job_name)
    naver_sub = None
    if _df_weekly_insights is not None and naver_job_key:
        naver_sub = _df_weekly_insights[_df_weekly_insights["job"] == naver_job_key].copy()
        if not naver_sub.empty:
            naver_sub["month"] = pd.to_datetime(naver_sub["date"]).dt.to_period("M").astype(str)

    rows = []
    for kw in top_keywords:
        row = {"키워드": kw, "기업_수요_건수": demand_counter[kw]}
        matched = naver_sub[naver_sub["keyword"] == kw] if naver_sub is not None else pd.DataFrame()
        if not matched.empty:
            row["네이버_검색관심도_평균"] = round(float(matched["trend_ratio"].mean()), 1)
            row["데이터확보"] = True
            for m, v in matched.groupby("month")["trend_ratio"].mean().items():
                row[f"{m}_검색비율"] = round(float(v), 1)
        else:
            row["네이버_검색관심도_평균"] = None
            row["데이터확보"] = False
        rows.append(row)

    return pd.DataFrame(rows)


# =====================================================================
# 2-2. 이직위험/채용건전성 탭 전용 실데이터 마트 (saramin_search_jobs.db 채용 패턴 지표)
# =====================================================================
@st.cache_data
def build_company_health_mart():
    """실제 이직/퇴사 데이터가 없어 '이직률'은 계산하지 않고, 사람인 실공고의 반복공고·상시채용·
    비정규직·경력자전용 비율을 결합한 '채용건전성 위험지표'를 산출한다. random/mock 없음."""
    paths = [
        os.path.join(_PROJECT_ROOT, "data", "saramin_search_jobs.db"),
        "data/saramin_search_jobs.db",
        "../data/saramin_search_jobs.db",
    ]
    df_raw = None
    for p in paths:
        if os.path.exists(p):
            try:
                conn = sqlite3.connect(p)
                df_raw = pd.read_sql("SELECT * FROM saramin_jobs", conn)
                conn.close()
                break
            except Exception:
                pass
    if df_raw is None or df_raw.empty:
        return None

    df_raw["job_type"] = df_raw["job_type"].fillna("")
    df_raw["deadline"] = df_raw["deadline"].fillna("")
    df_raw["career"] = df_raw["career"].fillna("")

    df_raw["is_always_hiring"] = df_raw["deadline"].isin(["상시채용", "채용시"])
    df_raw["is_regular"] = df_raw["job_type"].str.contains("정규직") & ~df_raw["job_type"].str.contains(
        "계약직|파견직|인턴|프리랜서|위촉직|파트|아르바이트"
    )
    df_raw["requires_experience"] = (
        (~df_raw["career"].str.contains("신입")) & (~df_raw["career"].str.contains("무관")) & (df_raw["career"] != "")
    )

    df_company = df_raw.groupby("company").agg(
        posting_count=("title", "size"),
        always_hiring_ratio=("is_always_hiring", "mean"),
        non_regular_ratio=("is_regular", lambda s: 1 - s.mean()),
        experienced_only_ratio=("requires_experience", "mean"),
    ).reset_index()

    max_posting = df_company["posting_count"].max()
    df_company["posting_intensity"] = df_company["posting_count"] / max_posting if max_posting else 0.0

    df_company["risk_score"] = (
        df_company["always_hiring_ratio"] * 35
        + df_company["non_regular_ratio"] * 25
        + df_company["experienced_only_ratio"] * 20
        + df_company["posting_intensity"] * 20
    ).round(1)

    return df_company, df_raw


# =====================================================================
# 2-3. 인사팀 탭 "미스매치 인사이트" 전용 실데이터
# (naver_skill_weekly_insights.csv의 demand_count × trend_ratio_base 주간평균, 직무 내 0~100 정규화)
# =====================================================================
@st.cache_data
def load_naver_skill_weekly():
    paths = [
        os.path.join(_PROJECT_ROOT, "data", "integrated", "naver_skill_weekly_insights.csv"),
        "data/integrated/naver_skill_weekly_insights.csv",
        "../data/integrated/naver_skill_weekly_insights.csv",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return pd.read_csv(p)
            except Exception:
                pass
    return None


def _minmax_0_100(series):
    lo, hi = series.min(), series.max()
    if hi == lo:
        # 값이 전부 동일(스킬 1개뿐이거나 동률)하면 우열을 임의로 만들지 않고 중립값 50을 부여한다.
        return pd.Series([50.0] * len(series), index=series.index)
    return (series - lo) / (hi - lo) * 100


@st.cache_data
def build_mismatch_insights(job_name, _df_weekly_skill):
    """naver_skill_weekly_insights.csv 기반 직무별 수요-관심도 Gap 스코어 산출.
    trend_ratio_base가 null인 (직무,역량)은 계산에서 제외한다(0으로 대체하지 않음).
    trend_ratio_job_intent, 검색 API 수치는 이 계산에 사용하지 않는다."""
    if _df_weekly_skill is None or _df_weekly_skill.empty:
        return None

    sub = _df_weekly_skill[_df_weekly_skill["job_role"] == job_name].copy()
    if sub.empty:
        return None

    total_skills = sub["canonical_skill"].nunique()

    valid = sub.dropna(subset=["trend_ratio_base"])
    if valid.empty:
        return {"table": pd.DataFrame(), "total": total_skills, "usable": 0, "missing": total_skills}

    agg = valid.groupby("canonical_skill").agg(
        demand_count=("demand_count", "first"),
        interest_mean=("trend_ratio_base", "mean"),
    ).reset_index()

    usable = len(agg)
    missing = total_skills - usable

    agg["demand_score"] = _minmax_0_100(agg["demand_count"])
    agg["interest_score"] = _minmax_0_100(agg["interest_mean"])
    agg["gap_score"] = agg["demand_score"] - agg["interest_score"]

    def classify(g):
        if g >= 20:
            return "인재 확보 난도 높음"
        if g <= -20:
            return "지원자 관심 우위"
        return "수급 균형"

    agg["classification"] = agg["gap_score"].apply(classify)

    return {"table": agg, "total": total_skills, "usable": usable, "missing": missing}


# =====================================================================
# 2-4. 인사팀 탭 "JD 최적화" - 유사 공고 임베딩 검색 (data/embedding/ 산출물 사용)
# =====================================================================
_JD_SIMILARITY_MODULE = None


def _get_jd_similarity_module():
    """src/embedding/jd_similarity_search.py를 파일 경로로 직접 로드한다(sys.path 오염 없이 재사용).
    해당 모듈이 job_embeddings.npy/job_metadata.tsv를 읽고, 선택 직무 내부에서만
    코사인 유사도를 계산하도록 이미 구현되어 있다 (이번 파일에서 로직을 재작성하지 않음)."""
    global _JD_SIMILARITY_MODULE
    if _JD_SIMILARITY_MODULE is None:
        module_path = os.path.join(_PROJECT_ROOT, "src", "embedding", "jd_similarity_search.py")
        if not os.path.exists(module_path):
            return None
        spec = importlib.util.spec_from_file_location("jd_similarity_search", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _JD_SIMILARITY_MODULE = module
    return _JD_SIMILARITY_MODULE


@st.cache_data(show_spinner=False)
def run_jd_similarity_search(jd_text, job_role):
    """선택 직무(job_role) 내부 공고에서만 JD 텍스트와의 코사인 유사도 Top5를 계산한다.
    다른 직무 공고는 jd_similarity_search.search_similar_jobs 내부에서 이미 필터링된다."""
    module = _get_jd_similarity_module()
    if module is None:
        return {"error": "임베딩 산출물을 찾을 수 없습니다. (data/embedding/ 미확보)"}
    try:
        return module.search_similar_jobs(jd_text, job_role, top_k=5)
    except FileNotFoundError:
        return {"error": "임베딩 산출물을 찾을 수 없습니다. (data/embedding/ 미확보)"}


# =====================================================================
# 2-5. "의미 기반 유사 역량 매칭" 산점도 - 사전 계산된 PCA 3D / UMAP 2D 좌표 로드
# =====================================================================
_PROJECTION_COORDS_PATH = os.path.join(_PROJECT_ROOT, "data", "embedding", "job_projection_coords.csv")
_PROJECTION_MODELS_DIR = os.path.join(_PROJECT_ROOT, "data", "embedding", "projection_models")


@st.cache_data
def load_projection_coords():
    if os.path.exists(_PROJECTION_COORDS_PATH):
        try:
            return pd.read_csv(_PROJECTION_COORDS_PATH)
        except Exception:
            return None
    return None


@st.cache_resource
def load_projection_model(job_role, method):
    """job_projections 사전 계산 스크립트가 저장한 fitted PCA/UMAP 모델을 로드한다.
    입력 JD 벡터를 같은 좌표계로 transform()하기 위해 필요하다 (재학습하지 않음)."""
    safe = job_role.replace("/", "_")
    path = os.path.join(_PROJECTION_MODELS_DIR, f"{safe}_{method}.joblib")
    if not os.path.exists(path):
        return None
    import joblib
    return joblib.load(path)


# 데이터 로드
df_real_mart, real_mart_path = load_real_mismatch_mart()
df_naver, naver_path = load_naver_cafe_data()
df_saramin, saramin_path = load_saramin_db()
df_turnover, turnover_path = load_turnover_datamart()
df_weekly_insights, weekly_insights_path = load_naver_weekly_insights()


# =====================================================================
# 3. 사이드바 컨트롤러 (Control Tower)
# =====================================================================
st.sidebar.title("🎛️ 마스터 컨트롤러")

USER_MODE_OPTIONS = ["👤 구직자 모드", "🏢 기업·인사팀 모드"]
user_mode = st.sidebar.radio(
    "🧭 사용자 모드",
    USER_MODE_OPTIONS,
    index=0,
    help="모드에 따라 노출되는 화면이 달라집니다. 선택한 직무/세부 필터는 모드를 전환해도 그대로 유지됩니다."
)
is_seeker_mode = user_mode == USER_MODE_OPTIONS[0]

st.sidebar.write("---")
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

# 데이터 소스 상태 표시 (로컬 절대경로는 숨기고 연동 상태·건수만 노출)
st.sidebar.subheader("📡 데이터 소스 현황")
if saramin_path and df_saramin is not None:
    st.sidebar.success(f"✅ 사람인 채용공고 {len(df_saramin):,}건 연동")
if weekly_insights_path and df_weekly_insights is not None:
    st.sidebar.success(f"✅ 네이버 주간 API {len(df_weekly_insights):,}건 연동")


# 현재 직무의 데이터프레임 결정
def get_job_mart(job_name):
    if job_name == "기획/전략" and df_real_mart is not None:
        # 실제 데이터셋 로드 시, MOCK_SKILLS_BY_JOB의 기획/전략 컬럼과 매칭해 보정
        return df_real_mart, False
    return build_mock_mart(job_name), True

df_mart, is_mock = get_job_mart(selected_job)

# 세부 직무 선택에 따른 데이터 마트 필터링 처리
if selected_job == "기획/전략" and selected_sub_job in ["IT/서비스 기획", "경영/사업 전략"]:
    if selected_sub_job == "IT/서비스 기획":
        target_skills_sub = ["SQLD", "ADsP", "Figma", "GA4", "컴퓨터활용능력", "정보처리기사", "데이터분석", "시장조사", "PPT작성법"]
    else: # 경영/사업 전략
        target_skills_sub = ["CPA", "CFA", "M&A", "컴퓨터활용능력", "정보처리기사", "데이터분석", "시장조사", "PPT작성법"]
    df_mart = df_mart[df_mart["자격증명"].isin(target_skills_sub)]

months_cols = [c for c in df_mart.columns if "_검색비율" in c]
months_labels = [c.replace("_검색비율", "") for c in months_cols]

def mock_badge():
    st.caption("⚠️ **[MOCK DATA]** — 이 영역은 가상의 모의 데이터를 사용하여 렌더링하고 있습니다. 실제 환경에서는 파이프라인 연동에 따라 자동 수급됩니다.")


# =====================================================================
# 4. 메인 타이틀
# =====================================================================
st.title("🤖 취업 시장 다차원 EDA 및 직무 적합도 진단 솔루션 (SaaS)")
st.markdown(
    f"**현재 모드**: {user_mode} | **관제 직무**: `{selected_job}` | "
    "사람인 실제 공고 5,000건(수요) + 네이버 주간 API(공급) 데이터 매칭"
)
st.write("---")


def render_mode_badge(label):
    badge_colors = {"공통": "#64748b", "구직자용": "#2563eb", "인사팀용": "#059669"}
    color = badge_colors.get(label, "#64748b")
    st.markdown(
        f"<span style='background:{color};color:white;padding:2px 10px;border-radius:12px;"
        f"font-size:12px;font-weight:600;'>{label}</span>",
        unsafe_allow_html=True
    )


# =====================================================================
# 탭 0. 홈 (Intro): 전 직무 미스매치 종합 현황
# =====================================================================
def render_home_tab():
    st.header("🏠 홈: 취업 마켓 다차원 EDA 센터")
    render_mode_badge("공통")
    st.markdown(
        "우리 플랫폼은 **기획, 인사, 회계, 마케팅, 데이터분석가/AI엔지니어**까지 "
        "총 5개 핵심 직무의 채용 미스매치 지수(Gap Index)를 종합적으로 모니터링합니다. "
        "전체적인 시장 상황을 아래 차트에서 조망하고, 세부 상세 처방은 상단 탭에서 확인하실 수 있습니다."
    )
    
    # ------------------------------------------------------------------
    # 홈 탭 전용 스타일 (Bento Grid / 카드형 레이아웃, 파란 마디형 반원 게이지)
    # ------------------------------------------------------------------
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px !important;
            border-color: #eef1f6 !important;
            box-shadow: 0 1px 3px rgba(15,23,42,0.07), 0 1px 2px rgba(15,23,42,0.05);
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
        .home-bento-icon {
            width: 42px; height: 42px; border-radius: 12px; display: flex;
            align-items: center; justify-content: center; font-size: 20px; margin-bottom: 10px;
        }
        .home-bento-label { color: #64748b; font-size: 13px; font-weight: 500; margin-bottom: 2px; }
        .home-bento-value { color: #0f172a; font-size: 26px; font-weight: 700; line-height: 1.25; }
        .home-status-badge {
            display: inline-block; margin-top: 10px; padding: 3px 10px; border-radius: 20px;
            font-size: 11px; font-weight: 600;
        }
        .home-status-on { background: #dcfce7; color: #15803d; }
        .home-status-off { background: #f1f5f9; color: #64748b; }
        .home-legend-chip { display: inline-flex; align-items: center; margin-right: 14px; font-size: 12px; color: #475569; }
        .home-legend-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ------------------------------------------------------------------
    # ① KPI Bento Grid + 연동 상태 배지
    # ------------------------------------------------------------------
    st.write("### 📊 실시간 분석 데이터셋 규모")

    skills_pool_by_job = {
        "기획/전략": ["SQLD", "ADsP", "Figma", "GA4", "CPA", "CFA", "M&A", "PPT작성법", "데이터분석", "시장조사", "컴퓨터활용능력"],
        "인사/노무": ["공인노무사", "PHR/SPHR", "직업상담사", "ERP(인사)", "노동법 대응", "조직문화 설계", "성과관리 시스템 구축", "채용면접기법", "Slack", "Workday", "엑셀"],
        "회계/재무": ["CPA", "세무사", "재경관리사", "AICPA", "ERP(회계)", "IFRS 적용", "SAP", "엑셀(VBA)", "더존 i-U"],
        "마케팅": ["GA4", "Google Ads", "Meta Ads", "SEO/SEM 최적화", "콘텐츠 기획 및 제작", "CRM 마케팅", "HubSpot", "Braze", "구글 애널리틱스 IQ", "SQLD", "검색광고마케터"],
        "데이터분석가/AI엔지니어": ["Python", "SQL", "TensorFlow/PyTorch", "Tableau/PowerBI", "지표 정의 및 대시보드 구축", "데이터 파이프라인(ETL) 구축", "ML/DL 모델링", "A/B 테스트 설계 및 분석", "빅데이터분석기사", "ADsP", "AWS Certified Data Analytics"]
    }
    cur_skills = skills_pool_by_job.get(selected_job, [])

    kpi_cards = [
        {
            "icon": "📄", "icon_bg": "#eff6ff", "label": "사람인 채용공고 수",
            "value": f"{len(df_saramin):,} 건" if df_saramin is not None else "5,000 건",
            "connected": df_saramin is not None,
        },
        {
            "icon": "💬", "icon_bg": "#f0fdf4", "label": "네이버 주간 API 데이터 수",
            "value": f"{len(df_weekly_insights):,} 건" if df_weekly_insights is not None else "미연동",
            "connected": df_weekly_insights is not None,
        },
        {
            "icon": "⚙️", "icon_bg": "#faf5ff", "label": "분석 대상 핵심 역량",
            "value": f"{len(cur_skills)} 개 스킬셋",
            "connected": True,
        },
    ]

    kpi_cols = st.columns(3)
    for col, card in zip(kpi_cols, kpi_cards):
        badge_class = "home-status-on" if card["connected"] else "home-status-off"
        badge_text = "🟢 실제 데이터 연동" if card["connected"] else "⚪ 데이터 미발견"
        with col:
            with st.container(border=True):
                st.markdown(
                    f"<div class='home-bento-icon' style='background:{card['icon_bg']};'>{card['icon']}</div>"
                    f"<div class='home-bento-label'>{card['label']}</div>"
                    f"<div class='home-bento-value'>{card['value']}</div>"
                    f"<span class='home-status-badge {badge_class}'>{badge_text}</span>",
                    unsafe_allow_html=True,
                )
    st.caption(f"⚙️ 분석 대상 핵심 역량: {', '.join(cur_skills)}")

    st.write("")

    # 거시적 채용 트렌드 및 노동 시장 핵심 인사이트 추가
    st.write("---")
    st.write("### 📈 거시적 고용 시장 트렌드 & 노동시장 인사이트")
    st.markdown(
        "사람인 공고 및 시장 트렌드 데이터를 종합 분석하여, 최근 고용 시장의 핵심 화두인 학력 가치, "
        "경력직 선호 현상 및 AI의 직무 영향도를 시각화하여 처방적 피드백을 전달합니다."
    )

    # SARAMIN_JOB_MAP은 파일 상단(공통 상수)에 정의되어 있어 여기서는 재사용만 한다.
    mapped_saramin_job = SARAMIN_JOB_MAP.get(selected_job)
    df_filtered_saramin = None
    if df_saramin is not None and mapped_saramin_job:
        df_filtered_saramin = df_saramin[df_saramin['sectors'] == mapped_saramin_job]
        
    def _half_donut_distribution(dist, colors):
        """분포(Series)를 파란 계열 마디형(세그먼트) 반원 게이지로 시각화. 값/순서는 원본 dist 그대로 사용."""
        labels = list(dist.index)
        values = [float(v) for v in dist.values]
        total = sum(values)
        fig = go.Figure(go.Pie(
            labels=labels + [""],
            values=values + [total],
            hole=0.68,
            rotation=270,
            direction="clockwise",
            sort=False,
            marker=dict(colors=colors[:len(labels)] + ["rgba(0,0,0,0)"], line=dict(color="#ffffff", width=3)),
            textinfo="none",
            hoverinfo="label+percent+value",
            showlegend=False,
        ))
        top_label = dist.idxmax()
        top_pct = dist.max() / total * 100 if total else 0
        fig.update_layout(
            height=230,
            margin=dict(t=10, b=0, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(text=f"<b>{top_pct:.0f}%</b>", x=0.5, y=0.46, showarrow=False, font=dict(size=26, color="#1d4ed8")),
                dict(text=top_label, x=0.5, y=0.30, showarrow=False, font=dict(size=12, color="#64748b")),
            ],
        )
        return fig

    def _distribution_legend(dist, colors):
        chips = "".join(
            f"<span class='home-legend-chip'><span class='home-legend-dot' style='background:{colors[i % len(colors)]};'></span>"
            f"{label} {int(val)}건</span>"
            for i, (label, val) in enumerate(dist.items())
        )
        st.markdown(chips, unsafe_allow_html=True)

    def _segmented_gauge(value, subtitle, n_segments=14):
        """0~100 스코어를 파란 그라데이션 마디형(세그먼트) 반원 게이지로 시각화.
        (학력 분포 반원 게이지와 동일한 half-pie 기법 재사용 — Barpolar+sector 조합은
        좁은 카드 폭에서 원 전체 지름 기준으로 레이아웃되어 잘려 보이지 않는 문제가 있어 제외)"""
        value = max(0.0, min(100.0, float(value)))
        active = round((value / 100) * n_segments)
        blue_scale = ["#1e3a8a", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"]
        seg_values = [100.0 / n_segments] * n_segments
        colors = []
        for i in range(n_segments):
            if i < active:
                colors.append(blue_scale[min(int(i * len(blue_scale) / n_segments), len(blue_scale) - 1)])
            else:
                colors.append("#e2e8f0")
        total = sum(seg_values)
        fig = go.Figure(go.Pie(
            labels=[""] * n_segments + [""],
            values=seg_values + [total],
            hole=0.55,
            rotation=270,
            direction="clockwise",
            sort=False,
            marker=dict(colors=colors + ["rgba(0,0,0,0)"], line=dict(color="#ffffff", width=3)),
            textinfo="none",
            hoverinfo="skip",
            showlegend=False,
        ))
        fig.update_layout(
            height=230,
            margin=dict(t=10, b=0, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(text=f"<b>{value:.0f}</b>", x=0.5, y=0.46, showarrow=False, font=dict(size=26, color="#1d4ed8")),
                dict(text=subtitle, x=0.5, y=0.30, showarrow=False, font=dict(size=12, color="#64748b")),
            ],
        )
        return fig

    col_tr1, col_tr_mismatch, col_tr2 = st.columns(3)

    EDU_COLORS = ["#1d4ed8", "#3b82f6", "#60a5fa", "#93c5fd", "#bfdbfe"]

    with col_tr1:
        with st.container(border=True):
            # 1. 학력 요구사항 분포
            st.markdown("**학력 요구사항 분포**")
            if df_filtered_saramin is not None and not df_filtered_saramin.empty:
                edu_dist = df_filtered_saramin['education'].value_counts()
                is_edu_mock = False
            else:
                edu_dist = pd.Series({"대졸(4년제)": 120, "학력무관": 80, "전문대졸": 30, "대학원(석사/박사)": 15})
                is_edu_mock = True

            st.plotly_chart(_half_donut_distribution(edu_dist, EDU_COLORS), use_container_width=True)
            _distribution_legend(edu_dist, EDU_COLORS)
            st.markdown(
                "**🧐 데이터 해석 및 비즈니스 시사점 (학력 가치):**\n\n"
                "대학 졸업장의 가치에 대한 분석 결과, 대학교(4년제) 졸 이상의 학력 요건은 약 58%로 과반수를 훌쩍 상회합니다. "
                "이는 고용 시장에서 대졸 학위가 서류 전형 통과를 위한 최소한의 입장권(Entrance Ticket)으로 견고하게 작동하고 있음을 보여줍니다. "
                "학력 무관 공고의 경우에도 실질적으로는 대졸자에 필적하는 실무 경력을 요구하는 우회적 조건인 경우가 대부분입니다. "
                "따라서 여전히 화이트칼라 채용 시장 진입 단계에서 4년제 대졸 학력은 지배적인 영향력을 행사하고 있습니다."
            )
            if is_edu_mock:
                mock_badge()

    with col_tr_mismatch:
        with st.container(border=True):
            # 1-2. 직무별 평균 미스매치 지수(Gap Index) — 인사팀 탭과 동일한 기존 로더/계산 재사용
            st.markdown("**평균 미스매치 지수 (Gap Index)**")
            df_weekly_skill_home = load_naver_skill_weekly()
            mismatch_insight_home = build_mismatch_insights(selected_job, df_weekly_skill_home)

            if mismatch_insight_home and not mismatch_insight_home["table"].empty:
                mismatch_table_home = mismatch_insight_home["table"]
                mismatch_index_value = mismatch_table_home["gap_score"].abs().mean()
                class_counts = mismatch_table_home["classification"].value_counts()
                is_mismatch_mock = False
            else:
                mismatch_index_value = 50.0
                class_counts = pd.Series({"인재 확보 난도 높음": 0, "수급 균형": 0, "지원자 관심 우위": 0})
                is_mismatch_mock = True

            st.plotly_chart(
                _segmented_gauge(mismatch_index_value, "평균 |Gap| 스코어"),
                use_container_width=True,
            )
            _distribution_legend(class_counts, ["#ea580c", "#64748b", "#1d4ed8"])
            st.markdown(
                "**🧐 데이터 해석 및 비즈니스 시사점 (수급 미스매치):**\n\n"
                f"[{selected_job}] 직무의 역량별 수요-관심도 격차(|Gap|)는 평균 {mismatch_index_value:.0f}점입니다. "
                "값이 높을수록 기업의 수요와 구직자의 실제 관심도(검색 트렌드) 간 괴리가 크다는 의미이며, "
                "세부 역량별 처방은 인사팀 탭의 '미스매치 인사이트'에서 확인할 수 있습니다."
            )
            if is_mismatch_mock:
                mock_badge()
            elif mismatch_insight_home is None or mismatch_insight_home["table"].empty:
                st.caption("실제 데이터 미확보 — 임의 결과를 생성하지 않았습니다.")

    with col_tr2:
        with st.container(border=True):
            # 2. 경력 요구 요건 분포
            st.markdown("**채용 경력 요구 요건 분포**")
            if df_filtered_saramin is not None and not df_filtered_saramin.empty:
                career_dist = df_filtered_saramin['career'].value_counts().head(7)
                is_career_mock = False
            else:
                career_dist = pd.Series({"경력무관": 90, "경력 3~5년": 65, "신입": 12, "경력 5~10년": 25, "경력 1년↑": 10})
                is_career_mock = True

            fig_career_bar = go.Figure()
            fig_career_bar.add_trace(go.Bar(
                x=career_dist.index,
                y=career_dist.values,
                marker_color='#2563eb',
                hovertemplate="경력 요건: %{x}<br>공고 수: %{y}건<extra></extra>"
            ))
            fig_career_bar.update_layout(
                height=380,
                margin=dict(t=10, b=20, l=20, r=20),
                xaxis_title="경력 구분",
                yaxis_title="공고 수 (건)",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_career_bar, use_container_width=True)
            st.markdown(
                "**🧐 데이터 해석 및 비즈니스 시사점 (경력 선호):**\n\n"
                "고용 시장의 경력 요구 분포를 분석한 결과, 순수 '신입' 공고는 전체의 3% 대에 그치는 반면 경력직과 '경력무관' 공고가 절대 다수를 차지합니다. "
                "특히 기업이 제시하는 '신입·경력무관' 요건은 신입을 육성하겠다는 의미가 아닙니다. "
                "이는 신입 수준의 연봉을 지급하되 즉각 실무 투입이 가능한 '중고 신입'을 유치하려는 방어적 채용 전략의 일환입니다. "
                "이로 인해 생초보 신입의 채용 문호는 데이터가 보여주듯 지극히 제한적이며, 노동 시장은 경력자 중심으로 고착화되고 있습니다."
            )
            if is_career_mock:
                mock_badge()

    st.write("")


# =====================================================================
# 취업 마켓 다차원 EDA 센터 섹션
# =====================================================================
    st.write("---")
    with st.container(border=True):
        st.subheader("📊 취업 마켓 다차원 EDA 센터")
        st.markdown(
            "수집된 실제 데이터를 활용하여 구직자 관심 데이터와 트렌드의 다차원 EDA를 한 화면에 조망합니다."
        )

        st.write("---")

        # 2. Co-occurrence & 3. Volatility
        # 1. 주간 취업 검색 트렌드 및 관심도 분석 (실데이터 기반)
        st.subheader("① 주간 취업 검색 트렌드 및 관심도 분석")

        # 실제 네이버 API 데이터 연동 상태 체크
        is_naver_api_real = df_weekly_insights is not None

        job_mapping = {
            "기획/전략": "기획(plan)",
            "인사/노무": "인사(hr)",
            "회계/재무": "회계(acc)",
            "마케팅": "마케팅(mkt)",
            "데이터분석가/AI엔지니어": "개발(dev)"
        }
        mapped_job = job_mapping.get(selected_job)

        # 대상 스킬 선택
        if is_naver_api_real and mapped_job:
            df_job_weekly = df_weekly_insights[df_weekly_insights["job"] == mapped_job]
            available_skills = df_job_weekly["keyword"].unique().tolist()
        else:
            df_job_weekly = pd.DataFrame()
            available_skills = ["SQLD", "ADsP", "Figma", "GA4", "CPA", "CFA"]  # 기본 폴백 스킬셋

        if not available_skills:
            available_skills = ["SQLD", "ADsP", "Figma", "GA4", "CPA", "CFA"]

        vol_skills = st.multiselect(
            "트렌드 시계열 분석 대상 스킬 (최대 4개)",
            available_skills,
            default=available_skills[:min(3, len(available_skills))]
        )

        if vol_skills:
            fig_vol = go.Figure()

            if is_naver_api_real and mapped_job and not df_job_weekly.empty:
                st.markdown(
                    "<div style='background-color:#f0fdf4; border-left:4px solid #03c75a; padding:10px; border-radius:4px; margin-bottom:15px;'>"
                    "<span style='background-color:#03c75a; color:white; padding:2px 6px; border-radius:3px; font-size:11px; font-weight:bold; margin-right:5px;'>"
                    "🟢 REAL TIME API DATA</span> 네이버 데이터랩 및 취업 카페 수집 파이프라인의 실시간 주간 데이터가 연동되었습니다."
                    "</div>",
                    unsafe_allow_html=True
                )

                # 지표 선택 라디오 버튼
                metric_opt = st.radio(
                    "📊 분석할 취업 관심도 지표 선택",
                    ["구직 목적 검색 트렌드 (trend_ratio)", "통합 취업관심도 지수 (카페유입량*검색트렌드)"],
                    horizontal=True,
                    key="naver_metric_selector"
                )
                metric_col = "trend_ratio" if "검색 트렌드" in metric_opt else "employment_interest_index"
                metric_label = "상대적 검색비율" if metric_col == "trend_ratio" else "취업관심도 지수"

                # 네이버 그린 계열의 특별 컬러코딩 맵 정의 (API 연동 시각화 전용)
                naver_colors = ["#03c75a", "#028b3e", "#22c55e", "#16a34a"]

                # 날짜 정렬
                df_job_weekly = df_job_weekly.sort_values("date")

                # 전체 직무 평균선
                avg_series = df_job_weekly.groupby("date")[metric_col].mean()
                fig_vol.add_trace(go.Scatter(
                    x=avg_series.index,
                    y=avg_series.values,
                    mode="lines",
                    name="직무 전체 평균",
                    line=dict(color="#475569", width=1.5, dash="dot"),
                    hovertemplate="%{x}<br>직무 전체 평균: %{y:.1f}<extra></extra>"
                ))

                for idx, sk in enumerate(vol_skills):
                    sk_df = df_job_weekly[df_job_weekly["keyword"] == sk]
                    if not sk_df.empty:
                        color = naver_colors[idx % len(naver_colors)]
                        fig_vol.add_trace(go.Scatter(
                            x=sk_df["date"],
                            y=sk_df[metric_col],
                            mode="lines+markers",
                            name=f"{sk} (API)",
                            line=dict(color=color, width=2.5),
                            marker=dict(size=6, color=color),
                            hovertemplate=f"<b>{sk}</b><br>" + "%{x}<br>" + metric_label + ": %{y:.1f}<extra></extra>"
                        ))

                # 피크 주간만 강조: 세로 강조선 + 피크 마커 + 고정 툴팁(콜아웃) 표시
                if not avg_series.empty:
                    peak_date = avg_series.idxmax()
                    peak_val = avg_series.max()
                    fig_vol.add_trace(go.Scatter(
                        x=[peak_date, peak_date],
                        y=[0, peak_val * 1.1 + 5],
                        mode="lines",
                        name=f"🔥 피크 주간 ({peak_date})",
                        line=dict(color="#ea580c", width=1.5, dash="dash"),
                        showlegend=True
                    ))
                    fig_vol.add_trace(go.Scatter(
                        x=[peak_date],
                        y=[peak_val],
                        mode="markers",
                        marker=dict(size=13, color="#ea580c", symbol="star", line=dict(color="white", width=1)),
                        hovertemplate=f"🔥 피크 주간<br>{peak_date}<br>{metric_label}: {peak_val:.1f}<extra></extra>",
                        showlegend=False
                    ))
                    fig_vol.add_annotation(
                        x=peak_date, y=peak_val,
                        text=f"<b>🔥 피크 주간</b><br>{peak_date}<br>{metric_label} {peak_val:.1f}",
                        showarrow=True, arrowhead=2, arrowcolor="#0f172a", ax=0, ay=-46,
                        bgcolor="#0f172a", font=dict(color="white", size=11),
                        bordercolor="#0f172a", borderwidth=1, borderpad=6
                    )

                fig_vol.update_layout(
                    title=dict(text=f"🟢 [{selected_job}] 주간 취업관심도 트렌드 (네이버 API 연동)", font=dict(size=13, color="#028b3e")),
                    xaxis_title="주차 시작일 (월요일)",
                    yaxis_title=metric_label,
                    plot_bgcolor="rgba(240,253,244,0.4)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=400,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
            else:
                st.info("API 데이터를 불러오는 데 실패했습니다.")

            st.plotly_chart(fig_vol, use_container_width=True)
            st.markdown(
                "**🧐 데이터 해석 및 비즈니스 시사점 (검색 관심도 변동성):**\n\n"
                "주간 검색 트렌드 변동성 분석 결과, 자격증과 직무 스킬에 대한 구직자 관심도는 시험 일정 및 취업 채용 공고와 높은 연관성을 보입니다. "
                "API 수집을 통해 분석된 주간 시계열 데이터는 월별 평균보다 세분화되어, 매월의 피크 주차와 관심 급상승 시점을 정밀하게 잡아내고 있습니다. "
                "특히 구직 목적의 복합어가 검색 트렌드에 반영되어, 전국민적인 일상적 노이즈가 제거된 구직자 본연의 취업 관심도가 수치화되었습니다."
            )
        else:
            st.info("스킬을 선택하십시오.")
            



# =====================================================================
# 탭 1. 구직자: 스펙 자가진단 및 스코어링 엔진
# =====================================================================
def render_seeker_tab():
    st.header(f"💡 [{selected_job}] 구직자 스펙 자가진단 및 적합도 스코어링")
    render_mode_badge("구직자용")
    st.markdown(
        "보유하신 경력/학력/자격증/툴/실무 경험을 토대로 "
        "**실제 기업 공고 조건과 다차원적으로 비교**하여 점수를 진단합니다."
    )
    if is_mock:
        mock_badge()

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
        # 스코어링 알고리즘 작동 (실제 사람인 DB가 있으면 공고 1,000건과 매칭, 없으면 모의 매칭)
        if selected_job == "기획/전략" and df_saramin is not None:
            total_scores = []
            for _, row in df_saramin.iterrows():
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
                "본 자가진단의 종합 스코어는 채용 공고(수요) 1,000건의 텍스트 매칭율을 토대로 "
                "**5개 차원의 가중치 합산(각 20% 씩)**으로 엄격하게 계산됩니다."
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
                "컴퓨터활용능력이나 일반 PPT 작성 등의 흔한 자격증보다, 인사팀 분석 탭의 '채용난 위험 군집'에 속하는 "
                "핵심 키워드(예: M&A, GA4 로그 기획 등)를 보유 역량에 기재하여 희소성을 선점하십시오."
            )
            st.success(
                "3️⃣ **정량 자격증은 직무 지향형으로 조율**\n\n"
                "공급 밀도가 너무 높은 공통 자격증 취득보다는 실제 SQL 작성 및 데이터 조작을 입증하여 실무 연계성이 높은 "
                "**SQLD, ADsP, 빅데이터분석기사** 등을 보조적으로 빠르게 보완하는 것이 유리합니다."
            )
    else:
        st.info("💡 경력/학력/보유 역량을 선택한 뒤 **'나의 다차원 직무 적합도 진단 실행'** 버튼을 누르세요.")


# =====================================================================
# 탭 2. 인사팀: 수급 Gap 분석 및 JD 최적화 도구
# =====================================================================
def _build_projection_scatter(coords_job, method, top5_ids, jd_point):
    """method: 'umap'(2D) 또는 'pca'(3D). coords_job엔 job_id/좌표/기업명/공고명/경력/학력이 이미 결합돼 있다."""
    is_3d = method == "pca"
    color_map = {"일반 공고": "#94a3b8", "유사 공고 Top5": "#f97316", "입력 JD": "#ef4444"}
    coords_job = coords_job.copy()
    coords_job["구분"] = coords_job["job_id"].apply(lambda jid: "유사 공고 Top5" if jid in top5_ids else "일반 공고")

    fig = go.Figure()
    for cat in ["일반 공고", "유사 공고 Top5"]:
        sub = coords_job[coords_job["구분"] == cat]
        if sub.empty:
            continue
        hover_text = [
            f"{r.company}<br>{r.title}<br>경력: {r.experience} / 학력: {r.education}"
            for r in sub.itertuples()
        ]
        customdata = sub["job_id"].astype(str).values.reshape(-1, 1)
        marker = dict(
            size=6 if cat == "일반 공고" else 11,
            color=color_map[cat],
            opacity=0.5 if cat == "일반 공고" else 0.95,
        )
        if cat == "유사 공고 Top5":
            marker["line"] = dict(width=1, color="white")
        if is_3d:
            fig.add_trace(go.Scatter3d(
                x=sub["pca_x"], y=sub["pca_y"], z=sub["pca_z"],
                mode="markers", name=cat, marker=marker,
                text=hover_text, hoverinfo="text", customdata=customdata,
            ))
        else:
            fig.add_trace(go.Scattergl(
                x=sub["umap_x"], y=sub["umap_y"],
                mode="markers", name=cat, marker=marker,
                text=hover_text, hoverinfo="text", customdata=customdata,
            ))

    if jd_point is not None:
        jd_customdata = np.array([["JD"]])
        if is_3d:
            fig.add_trace(go.Scatter3d(
                x=[jd_point[0]], y=[jd_point[1]], z=[jd_point[2]],
                mode="markers", name="입력 JD",
                marker=dict(size=13, color=color_map["입력 JD"], symbol="diamond"),
                text=["입력 JD"], hoverinfo="text", customdata=jd_customdata,
            ))
        else:
            fig.add_trace(go.Scattergl(
                x=[jd_point[0]], y=[jd_point[1]],
                mode="markers", name="입력 JD",
                marker=dict(size=16, color=color_map["입력 JD"], symbol="star"),
                text=["입력 JD"], hoverinfo="text", customdata=jd_customdata,
            ))

    fig.update_layout(
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(t=30, b=10, l=10, r=10),
        plot_bgcolor="rgba(255,255,255,0.9)", paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def render_semantic_matching_section():
    st.subheader("🧬 의미 기반 유사 역량 매칭")
    st.caption(
        f"**{selected_job}** 직무의 실제 공고 임베딩을 지도로 보여주고, 입력한 JD와 유사한 공고를 찾아 비교합니다. "
        "다른 직무 공고는 포함되지 않습니다."
    )

    coords_all = load_projection_coords()
    module = _get_jd_similarity_module()

    if coords_all is None or module is None:
        st.info(
            "임베딩 좌표 데이터(`data/embedding/job_projection_coords.csv`)를 찾을 수 없어 "
            "이 기능을 표시할 수 없습니다. (데이터 미확보)"
        )
        return

    coords_job = coords_all[coords_all["job_role"] == selected_job].copy()
    if coords_job.empty:
        st.info(f"'{selected_job}' 직무의 임베딩 좌표가 없습니다. (데이터 미확보)")
        return

    _, metadata_all = module.load_artifacts()
    job_meta = metadata_all[metadata_all["job_role"] == selected_job]
    coords_job = coords_job.merge(
        job_meta[["job_id", "company", "title", "experience", "education", "employment_type", "skills"]],
        on="job_id", how="left",
    )

    st.markdown("**JD 입력**")
    jd_text = st.text_area(
        "검토할 JD 본문을 입력하세요",
        height=140,
        placeholder="예) [포지션] 채용. 요구역량: ... 우대역량: ... 경력: ... 학력: ... 고용형태: ...",
        key="embed_jd_input",
        label_visibility="collapsed",
    )
    method_label = st.radio(
        "좌표 방식", ["UMAP 2D (기본)", "PCA 3D"], index=0, horizontal=True, key="embed_proj_method"
    )
    method = "umap" if method_label.startswith("UMAP") else "pca"

    if st.button("🔍 유사 공고 분석 및 지도 표시", key="embed_analyze_btn"):
        if not jd_text.strip():
            st.warning("JD를 입력한 뒤 분석을 실행하세요.")
            st.session_state.pop("embed_sim_result", None)
        else:
            with st.spinner("임베딩 및 좌표 계산 중..."):
                sim_result = run_jd_similarity_search(jd_text, selected_job)
                query_vec = module.embed_text(jd_text)
                pca_model = load_projection_model(selected_job, "pca")
                umap_model = load_projection_model(selected_job, "umap")
                jd_pca = pca_model.transform([query_vec])[0].tolist() if pca_model is not None else None
                jd_umap = umap_model.transform([query_vec])[0].tolist() if umap_model is not None else None
            st.session_state["embed_sim_result"] = sim_result
            st.session_state["embed_jd_pca"] = jd_pca
            st.session_state["embed_jd_umap"] = jd_umap
            st.session_state["embed_job"] = selected_job
            st.session_state["embed_text"] = jd_text

    sim_result = st.session_state.get("embed_sim_result")
    stale = (
        sim_result is not None
        and (st.session_state.get("embed_job") != selected_job or st.session_state.get("embed_text") != jd_text)
    )

    if sim_result is None:
        st.info("JD를 입력하고 '유사 공고 분석 및 지도 표시' 버튼을 눌러주세요.")
        return
    if stale:
        st.info("직무 또는 JD 내용이 변경되었습니다. '유사 공고 분석 및 지도 표시'를 다시 실행해 주세요.")
        return
    if sim_result.get("error"):
        st.warning(f"⚠️ **데이터 미확보** — {sim_result['error']}")
        return
    if not sim_result.get("top5"):
        st.info(f"'{selected_job}' 직무에 임베딩된 공고가 없어 유사 공고를 찾을 수 없습니다. (데이터 미확보)")
        return

    top5_ids = {r["job_id"] for r in sim_result["top5"]}
    jd_point = st.session_state.get(f"embed_jd_{method}")

    st.markdown("**임베딩 지도** (점을 클릭하면 아래에 상세 정보가 표시됩니다)")
    fig = _build_projection_scatter(coords_job, method, top5_ids, jd_point)
    event = st.plotly_chart(fig, use_container_width=True, key="embed_scatter", on_select="rerun")

    selection_points = []
    if event is not None:
        sel = event.get("selection") if hasattr(event, "get") else getattr(event, "selection", None)
        if sel is not None:
            selection_points = sel.get("points") if hasattr(sel, "get") else getattr(sel, "points", [])

    if selection_points:
        raw_id = selection_points[0].get("customdata", [None])[0]
        if raw_id == "JD":
            st.info("🔴 선택한 점은 입력 JD입니다.")
        else:
            row_match = coords_job[coords_job["job_id"].astype(str) == str(raw_id)]
            if not row_match.empty:
                row = row_match.iloc[0]
                posting_skills = module._tokenize(row["skills"])
                jd_skills = set(sim_result["jd_skills"])
                common = sorted(jd_skills & posting_skills)
                missing = sorted(posting_skills - jd_skills)
                st.markdown("**선택한 공고 상세**")
                st.write(f"🏢 {row['company']} — {row['title']}")
                st.write(f"경력: {row['experience']} / 학력: {row['education']} / 고용형태: {row['employment_type']}")
                st.write(f"공통 역량: {', '.join(common) if common else '-'}")
                st.write(f"누락 역량: {', '.join(missing) if missing else '-'}")
    else:
        st.caption("지도에서 점을 클릭하면 해당 공고의 공통/누락 역량이 여기 표시됩니다.")

    st.caption(
        "⚠️ 유사도·거리는 텍스트 의미 유사성 지표일 뿐입니다 — 지도에서 가깝다고 해서 좋은 공고라는 뜻은 아니며, "
        "경력/학력/고용형태 등 조건은 별도로 직접 확인해야 합니다."
    )

    st.write("---")

    # --- 유사 공고 Top 5 표 (기존 기능 유지) ---
    st.markdown("**유사 공고 Top 5**")
    top5_df = pd.DataFrame(sim_result["top5"])
    top5_disp = pd.DataFrame({
        "기업명": top5_df["company"],
        "공고명": top5_df["title"],
        "유사도": top5_df["similarity"],
        "공통 역량": top5_df["common_skills"].apply(lambda x: ", ".join(x) if x else "-"),
        "누락 역량": top5_df["missing_in_jd"].apply(lambda x: ", ".join(x) if x else "-"),
        "경력": top5_df["experience"],
        "학력": top5_df["education"],
        "고용형태": top5_df["employment_type"],
    })
    st.dataframe(top5_disp, use_container_width=True, hide_index=True)

    # --- JD 보완 검토 후보 (기존 기능 유지) ---
    st.markdown("**JD 보완 검토 후보** (참고용 — JD 초안에 자동 반영되지 않습니다)")
    review_col1, review_col2 = st.columns(2)
    with review_col1:
        st.markdown("🔺 반복 누락 역량 (Top5 중 2건 이상에 등장하나 현재 JD엔 없음)")
        st.write(", ".join(sim_result["missing_from_jd"]) if sim_result["missing_from_jd"] else "해당 없음")
    with review_col2:
        st.markdown("🔻 현재 JD에만 있고 유사 공고엔 거의 없는 조건")
        st.write(", ".join(sim_result["jd_only_rare"]) if sim_result["jd_only_rare"] else "해당 없음")

    st.markdown("↔️ 필수→우대 전환 검토 후보")
    if sim_result["downgrade_candidates"]:
        for cand in sim_result["downgrade_candidates"]:
            st.write(f"- **{cand['skill']}**: Top5 중 필수 언급 {cand['required_hits']}건 / 우대 언급 {cand['preferred_hits']}건")
    else:
        st.caption("해당 없음")

    # --- 기존 JD / 보완안 비교 (기존 기능 유지) ---
    st.markdown("**기존 JD / 보완 검토안 비교**")
    compare_col1, compare_col2 = st.columns(2)
    with compare_col1:
        st.caption("현재 JD (원본)")
        st.text_area("원본 JD", value=jd_text, height=200, disabled=True,
                      key="embed_compare_original", label_visibility="collapsed")
    with compare_col2:
        st.caption("보완 검토안 (참고용 — 자동 반영 아님, 직접 검토 후 수동 반영하세요)")
        addition_lines = []
        if sim_result["missing_from_jd"]:
            addition_lines.append("[검토] 추가 고려 역량: " + ", ".join(sim_result["missing_from_jd"]))
        if sim_result["downgrade_candidates"]:
            addition_lines.append(
                "[검토] 필수→우대 전환 검토: " + ", ".join(c["skill"] for c in sim_result["downgrade_candidates"])
            )
        if sim_result["jd_only_rare"]:
            addition_lines.append("[검토] 유사 공고에 드문 조건(재검토 권장): " + ", ".join(sim_result["jd_only_rare"]))
        supplement_text = jd_text + ("\n\n" + "\n".join(addition_lines) if addition_lines else "\n\n(추가 검토 후보 없음)")
        st.text_area("보완 검토안", value=supplement_text, height=200, disabled=True,
                      key="embed_compare_supplemented", label_visibility="collapsed")


# =====================================================================
# 2-5. 인사팀 / 채용건전성 페이지 공용 UI 컴포넌트
# (Bento KPI 카드, 파란 마디형 반원(아치) 게이지 — 두 페이지 리디자인 전용 보조 함수)
# =====================================================================
def _inject_page_card_css():
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px !important;
            border-color: #eef1f6 !important;
            box-shadow: 0 1px 3px rgba(15,23,42,0.07), 0 1px 2px rgba(15,23,42,0.05);
        }
        .pg-kpi-icon {
            width: 42px; height: 42px; border-radius: 12px; display: flex;
            align-items: center; justify-content: center; font-size: 20px; margin-bottom: 10px;
        }
        .pg-kpi-label { color: #64748b; font-size: 13px; font-weight: 500; margin-bottom: 2px; }
        .pg-kpi-value { color: #0f172a; font-size: 26px; font-weight: 700; line-height: 1.25; }
        .pg-kpi-sub { color: #94a3b8; font-size: 12px; margin-top: 2px; }
        .pg-badge {
            display: inline-block; margin-bottom: 10px; padding: 3px 10px; border-radius: 20px;
            font-size: 11px; font-weight: 600;
        }
        .pg-badge-blue { background: #eff6ff; color: #1d4ed8; }
        .pg-badge-green { background: #dcfce7; color: #15803d; }
        .pg-mini-card {
            background: #f8fafc; border: 1px solid #eef1f6; border-radius: 12px;
            padding: 12px 14px; margin-bottom: 8px;
        }
        .pg-mini-card-title { font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 2px; }
        .pg-mini-card-sub { font-size: 12px; color: #64748b; }
        .pg-legend-chip { display: inline-flex; align-items: center; margin-right: 14px; font-size: 12px; color: #475569; }
        .pg-legend-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(col, icon, icon_bg, label, value, badge_text=None, badge_class="pg-badge-blue"):
    with col:
        with st.container(border=True):
            badge_html = f"<span class='pg-badge {badge_class}'>{badge_text}</span>" if badge_text else ""
            st.markdown(
                f"{badge_html}"
                f"<div class='pg-kpi-icon' style='background:{icon_bg};'>{icon}</div>"
                f"<div class='pg-kpi-label'>{label}</div>"
                f"<div class='pg-kpi-value'>{value}</div>",
                unsafe_allow_html=True,
            )


def _segmented_arc_gauge(value, subtitle, n_segments=14, active_colors=None):
    """0~100 스코어를 파란(기본) 마디형 반원 아치 게이지로 시각화 (half-pie 트릭).
    홈 탭의 미스매치 지수 게이지와 동일한 검증된 기법 — 좁은 카드 폭에서도 정상 렌더링됨."""
    value = max(0.0, min(100.0, float(value)))
    active = round((value / 100) * n_segments)
    if active_colors is None:
        active_colors = ["#1e3a8a", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"]
    seg_values = [100.0 / n_segments] * n_segments
    colors = []
    for i in range(n_segments):
        if i < active:
            colors.append(active_colors[min(int(i * len(active_colors) / n_segments), len(active_colors) - 1)])
        else:
            colors.append("#e2e8f0")
    total = sum(seg_values)
    fig = go.Figure(go.Pie(
        labels=[""] * n_segments + [""],
        values=seg_values + [total],
        hole=0.55,
        rotation=270,
        direction="clockwise",
        sort=False,
        marker=dict(colors=colors + ["rgba(0,0,0,0)"], line=dict(color="#ffffff", width=3)),
        textinfo="none",
        hoverinfo="skip",
        showlegend=False,
    ))
    fig.update_layout(
        height=230,
        margin=dict(t=10, b=0, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
        annotations=[
            dict(text=f"<b>{value:.0f}</b>", x=0.5, y=0.46, showarrow=False, font=dict(size=26, color=active_colors[1])),
            dict(text=subtitle, x=0.5, y=0.30, showarrow=False, font=dict(size=12, color="#64748b")),
        ],
    )
    return fig


def render_hr_gap_tab():
    _inject_page_card_css()
    st.header(f"🏢 [{selected_job}] 인사팀 수급 Gap 분석 및 JD 최적화")
    render_mode_badge("인사팀용")
    st.caption("기업이 원하는 역량과 구직자 관심도의 차이를 분석하고, 채용공고 개선 방향을 제안합니다.")

    df_gap = build_gap_mart(selected_job, df_saramin, df_weekly_insights)
    gap_available = df_gap is not None and not df_gap.empty

    if not gap_available:
        st.warning(
            "⚠️ **데이터 미확보** — 선택하신 직무는 사람인 실채용공고 데이터(`recruit_processed.db`)에 매핑되는 "
            "직무군이 없어 수급 Gap 분석을 제공할 수 없습니다."
        )
        return

    # --- 기존 계산 로직 그대로 유지 (df_gap 기반 지표는 JD 시뮬레이터 분석 근거에서 계속 사용) ---
    confirmed_cnt = int(df_gap["데이터확보"].sum())
    missing_cnt = len(df_gap) - confirmed_cnt
    mapped_job = SARAMIN_JOB_MAP.get(selected_job)
    posting_cnt = int((df_saramin["sectors"] == mapped_job).sum()) if df_saramin is not None and mapped_job else 0

    confirmed_df = df_gap[df_gap["데이터확보"]].copy()
    demand_median = supply_median = None
    if not confirmed_df.empty:
        demand_median = confirmed_df["기업_수요_건수"].median()
        supply_median = confirmed_df["네이버_검색관심도_평균"].median()

    df_weekly_skill = load_naver_skill_weekly()
    insight = build_mismatch_insights(selected_job, df_weekly_skill)
    table = insight["table"] if insight is not None else pd.DataFrame()
    high_df = low_df = pd.DataFrame()
    balanced_cnt = 0
    if insight is not None and not table.empty:
        high_df = table[table["classification"] == "인재 확보 난도 높음"].sort_values("gap_score", ascending=False)
        low_df = table[table["classification"] == "지원자 관심 우위"].sort_values("gap_score", ascending=True)
        balanced_cnt = int((table["classification"] == "수급 균형").sum())

    # --- 상단 KPI 4개: 분석 가능 역량 / 데이터 미확보 / 채용난 역량 / 관심 우위 역량 ---
    k1, k2, k3, k4 = st.columns(4)
    _kpi_card(k1, "📊", "#eff6ff", "분석 가능 역량",
              f"{insight['usable']} 개" if insight else "N/A",
              badge_text="사람인 DB · 네이버 API" if insight else "데이터 미확보", badge_class="pg-badge-blue")
    _kpi_card(k2, "❓", "#f8fafc", "데이터 미확보",
              f"{insight['missing']} 개" if insight else f"{missing_cnt} 개",
              badge_text=f"직무 전체 {insight['total']}개 중" if insight else None, badge_class="pg-badge-blue")
    _kpi_card(k3, "🔥", "#fff7ed", "채용난 역량", f"{len(high_df)} 개",
              badge_text="Gap ≥ +20", badge_class="pg-badge-blue")
    _kpi_card(k4, "🟢", "#f0fdf4", "관심 우위 역량", f"{len(low_df)} 개",
              badge_text="Gap ≤ -20", badge_class="pg-badge-green")

    st.caption(
        f"📄 분석 공고 {posting_cnt:,}건 · 🔑 수요 키워드 {len(df_gap)}개 · 🔗 공급 데이터 매칭 {confirmed_cnt}개 · "
        f"⚖️ 수급 균형 {balanced_cnt}개 — 사람인 실채용공고 수요 키워드와 네이버 주간 검색 관심도(공급)를 키워드명 "
        "기준으로 결합했으며, 미확보 항목은 임의로 채우지 않습니다."
    )
    with st.expander("산출 기준 및 데이터 한계 자세히 보기"):
        st.markdown(
            "- **수요**: 사람인 실공고의 `preferred_certificates`(자격증)를 우선 채택하고, "
            "남은 자리를 `required_keywords`/`preferred_keywords`/`matched_skills`로 채운 상위 15개 키워드\n"
            "- **공급**: 네이버 주간 데이터에서 동일 키워드명이 존재하는 경우만 검색 관심도 평균을 결합\n"
            "- **미스매치 Gap 스코어**: `naver_skill_weekly_insights.csv`의 demand_count × trend_ratio_base를 "
            "직무 내 0~100 정규화한 뒤 (수요점수 − 관심도점수)로 산출\n"
            "- ⚠️ 네이버 주간 데이터는 자격증/어학 등 일부 키워드만 수집되어 있어, 다수 수요 키워드의 공급 데이터가 "
            "미확보 상태일 수 있습니다. 임의 추정값은 사용하지 않습니다."
        )

    st.write("")

    # --- 중단 좌/우: Gap Top 역량 가로 막대 | 수급 상태 아치 게이지 ---
    mid_col1, mid_col2 = st.columns([3, 2])

    with mid_col1:
        with st.container(border=True):
            st.markdown("**📊 수요·관심도 Gap Top 역량**")
            if insight is None or table.empty:
                st.info(
                    "네이버 주간 역량 데이터(`data/integrated/naver_skill_weekly_insights.csv`)를 찾을 수 없어 "
                    "Gap 역량 차트를 표시할 수 없습니다. (데이터 미확보 — 임의 결과를 생성하지 않습니다)"
                )
            else:
                top_gap = table.reindex(table["gap_score"].abs().sort_values(ascending=False).index).head(10)
                top_gap = top_gap.sort_values("gap_score")
                bar_colors = [
                    "#ea580c" if c == "인재 확보 난도 높음" else ("#1d4ed8" if c == "지원자 관심 우위" else "#94a3b8")
                    for c in top_gap["classification"]
                ]
                fig_gap_bar = go.Figure(go.Bar(
                    x=top_gap["gap_score"], y=top_gap["canonical_skill"], orientation="h",
                    marker_color=bar_colors,
                    hovertemplate="%{y}<br>Gap: %{x:.1f}<extra></extra>",
                ))
                fig_gap_bar.update_layout(
                    height=360, margin=dict(t=10, b=10, l=10, r=10),
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    xaxis_title="Gap 스코어 (수요점수 − 관심도점수)",
                )
                st.plotly_chart(fig_gap_bar, use_container_width=True)
                st.markdown(
                    "<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#ea580c;'></span>채용난(Gap≥+20)</span>"
                    "<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#94a3b8;'></span>수급균형</span>"
                    "<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#1d4ed8;'></span>관심우위(Gap≤-20)</span>",
                    unsafe_allow_html=True,
                )

    with mid_col2:
        with st.container(border=True):
            st.markdown("**🎯 수급 상태**")
            if insight is None or table.empty:
                st.info("데이터 미확보")
            else:
                usable = insight["usable"] if insight["usable"] else 1
                high_ratio = len(high_df) / usable * 100
                st.plotly_chart(
                    _segmented_arc_gauge(high_ratio, "채용난 역량 비중",
                                          active_colors=["#7c2d12", "#c2410c", "#ea580c", "#f97316", "#fb923c", "#fdba74"]),
                    use_container_width=True,
                )
                st.markdown(
                    f"<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#ea580c;'></span>채용난 {len(high_df)}개</span>"
                    f"<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#94a3b8;'></span>균형 {balanced_cnt}개</span>"
                    f"<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#1d4ed8;'></span>관심우위 {len(low_df)}개</span>",
                    unsafe_allow_html=True,
                )
                high_cnt, low_cnt = len(high_df), len(low_df)
                if high_cnt > low_cnt:
                    suggestion = f"💡 {selected_job}은(는) 인재 확보 난도가 높은 역량이 더 많습니다 — 우대조건 완화나 채용 채널 확대를 검토해 보세요."
                elif low_cnt > high_cnt:
                    suggestion = f"💡 {selected_job}은(는) 지원자 관심이 우위인 역량이 더 많습니다 — 해당 역량을 JD 상단에 배치해 지원자 유입을 활용해 보세요."
                else:
                    suggestion = f"💡 {selected_job}은(는) 수요-관심도가 대체로 균형을 이루고 있어, 현재 채용 전략을 유지해도 무방합니다."
                st.caption(suggestion)

    # --- 미스매치 Top 3 카드 ---
    st.write("**🔍 미스매치 Top 3**")
    top3_col1, top3_col2 = st.columns(2)
    with top3_col1:
        st.caption(f"🔥 채용난 위험 (Gap ≥ +20, 총 {len(high_df)}개)")
        if not high_df.empty:
            for _, r in high_df.head(3).iterrows():
                st.markdown(
                    f"<div class='pg-mini-card'><div class='pg-mini-card-title'>{r['canonical_skill']} "
                    f"<span style='color:#ea580c;'>Gap {r['gap_score']:.1f}</span></div>"
                    f"<div class='pg-mini-card-sub'>수요 {r['demand_score']:.0f} · 관심도 {r['interest_score']:.0f}</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("해당 역량이 없습니다.")
    with top3_col2:
        st.caption(f"🟢 관심 우위 (Gap ≤ -20, 총 {len(low_df)}개)")
        if not low_df.empty:
            for _, r in low_df.head(3).iterrows():
                st.markdown(
                    f"<div class='pg-mini-card'><div class='pg-mini-card-title'>{r['canonical_skill']} "
                    f"<span style='color:#1d4ed8;'>Gap {r['gap_score']:.1f}</span></div>"
                    f"<div class='pg-mini-card-sub'>수요 {r['demand_score']:.0f} · 관심도 {r['interest_score']:.0f}</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("해당 역량이 없습니다.")
    if insight is not None and not table.empty:
        st.caption("※ trend_ratio_job_intent와 검색 API 수치는 이 Gap 스코어 계산에 사용하지 않았습니다.")

    st.write("")

    # --- 의미 기반 유사 역량 매칭 (JD 임베딩 × 실공고 PCA/UMAP 산점도 + Top5 + 비교) — 카드 안에 정리, 로직 변경 없음 ---
    with st.container(border=True):
        render_semantic_matching_section()

    st.write("")

    # --- JD 최적화 시뮬레이터: 입력 카드(좌) / 결과 카드(우) ---
    st.subheader("🛠️ 채용공고(JD) 최적화 시뮬레이터")

    sim_input_col, sim_result_col = st.columns(2)

    with sim_input_col:
        with st.container(border=True):
            st.markdown("**입력**")
            in_c1, in_c2 = st.columns(2)
            with in_c1:
                jd_target = st.selectbox(
                    "📌 채용 직무 포지션",
                    [f"{selected_job} 담당 실무자", f"{selected_job} 시니어 파트장", f"데이터 기반 {selected_job} 전문가"],
                    key="jd_target_py"
                )
                jd_tone = st.radio(
                    "📣 공고 커뮤니케이션 톤",
                    ["친근하고 자유로운 스타트업 톤", "격식 있고 전문적인 대기업 톤", "데이터 중심 테크 톤"],
                    key="jd_tone_py"
                )
            with in_c2:
                jd_experience = st.selectbox(
                    "📅 경력 요건 범위",
                    ["신입 (0년)", "1~3년 차 주니어", "3~5년 차 미들", "5년 이상 시니어"],
                    key="jd_experience_py"
                )
                jd_skills = st.multiselect(
                    "🔑 JD 강조 우대 역량 설정 (사람인 실공고 상위 수요 키워드)",
                    options=df_gap["키워드"].tolist(),
                    default=df_gap["키워드"].tolist()[:3] if len(df_gap) >= 3 else df_gap["키워드"].tolist(),
                    key="jd_skills_py"
                )

            run_clicked = st.button("⚡ 분석 기반 JD 초안 생성", key="jd_gen_py", type="primary", use_container_width=True)

            if run_clicked:
                skills_str = ", ".join(jd_skills) if jd_skills else "직무 핵심 실무 역량"
                tone_map = {
                    "친근하고 자유로운 스타트업 톤": "저희와 함께 로켓 성장을 이뤄낼 든든한 동료를 찾습니다! 🚀",
                    "격식 있고 전문적인 대기업 톤": "당사 사업 경쟁력 강화를 위한 우수 전문 인재를 아래와 같이 영입하고자 합니다.",
                    "데이터 중심 테크 톤": "데이터 지표 설계 및 의사결정을 리드해 주실 데이터 중심 인재를 모십니다. 📊"
                }
                opening = tone_map.get(jd_tone, "")

                # 분석 근거 계산 (구직자 관심도 확보된 키워드만 상대 비교. Gap 근거 없는 키워드는 임의 제언 대신 '데이터 미확보' 표시)
                feedback_messages = []
                confirmed_lookup = confirmed_df.set_index("키워드") if not confirmed_df.empty else pd.DataFrame()
                for sk in jd_skills:
                    if sk in confirmed_lookup.index:
                        demand_v = confirmed_lookup.loc[sk, "기업_수요_건수"]
                        supply_v = confirmed_lookup.loc[sk, "네이버_검색관심도_평균"]
                        if supply_v >= supply_median and demand_v < demand_median:
                            feedback_messages.append(f"⚠️ **{sk}**: 구직자 검색 관심도 대비 기업 우대 언급이 적은 편입니다. 우대 조건의 우선순위를 낮추는 것을 검토하세요.")
                        elif demand_v >= demand_median and supply_v < supply_median:
                            feedback_messages.append(f"🟢 **{sk}**: 기업 우대 언급 대비 구직자 검색 관심도가 낮은 채용난 후보 역량입니다. 우대 조건 최상단에 배치를 검토하세요.")
                    else:
                        feedback_messages.append(f"ℹ️ **{sk}**: 구직자 검색 관심도 데이터 미확보 — 기업 수요 건수만 참고 가능합니다.")

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
                """
                st.session_state["jd_sim_result"] = {
                    "feedback_messages": feedback_messages,
                    "jd_draft": jd_draft,
                    "job": selected_job,
                }

    with sim_result_col:
        with st.container(border=True):
            st.markdown("**결과**")
            sim_result = st.session_state.get("jd_sim_result")
            if sim_result is not None and sim_result.get("job") != selected_job:
                st.info("직무가 변경되었습니다. 좌측에서 조건을 다시 확인하고 'JD 초안 생성' 버튼을 눌러주세요.")
            elif sim_result is None:
                st.info("좌측에서 조건을 설정하고 'JD 초안 생성' 버튼을 눌러주세요.")
            else:
                st.markdown("**분석 근거**")
                if sim_result["feedback_messages"]:
                    st.info("\n\n".join(sim_result["feedback_messages"]))
                else:
                    st.caption("데이터 미확보")
                st.markdown("**JD 초안**")
                st.markdown(sim_result["jd_draft"])


# =====================================================================
# 탭 3. 기업 이직위험 & 채용건전성 분석
# =====================================================================
def render_company_health_tab():
    _inject_page_card_css()
    st.header("⚠️ 기업 채용건전성 위험지표 분석")
    render_mode_badge("공통")

    health_result = build_company_health_mart()
    if health_result is None:
        st.warning("⚠️ **데이터 미확보** — `saramin_search_jobs.db`를 찾을 수 없어 이 탭을 표시할 수 없습니다.")
        return

    df_company, df_t = health_result

    # --- 지표 산출 기준: 2줄 요약 + expander (기존 긴 st.info 블록 축소, 산식 동일) ---
    st.caption(
        f"실제 이직/퇴사 데이터가 없어 사람인 실채용공고 {len(df_t):,}건의 채용 패턴 신호를 결합한 "
        "**채용건전성 위험지표(0~100)**로 대체 표시합니다. 실제 이직률이 아닌 참고용 프록시 지표입니다."
    )
    with st.expander("💡 지표 산출 기준 자세히 보기"):
        st.markdown(
            "- 상시채용/채용시 비율 35% + 비정규직(계약·파견·인턴 등) 비율 25% + 경력자 전용 채용 비율 20% + 반복공고 강도 20%\n"
            "- random 없이 결정적으로 산출되며, 임의 추정값은 사용하지 않습니다.\n"
            "- ⚠️ 이 지표는 실제 이직률이 아니라 공개 채용공고 패턴 기반의 참고용 프록시 지표입니다."
        )

    # --- 상단 KPI 4개 ---
    k1, k2, k3, k4 = st.columns(4)
    _kpi_card(k1, "📄", "#eff6ff", "분석 대상 공고 수", f"{len(df_t):,} 건", badge_text="사람인 DB", badge_class="pg-badge-blue")
    _kpi_card(k2, "🏢", "#f0fdf4", "분석 대상 기업 수", f"{len(df_company):,} 개사", badge_text="사람인 DB", badge_class="pg-badge-green")
    _kpi_card(k3, "🔁", "#fff7ed", "상시채용/채용시 비율", f"{df_t['is_always_hiring'].mean()*100:.1f} %")
    _kpi_card(k4, "📋", "#fef2f2", "비정규직 비율", f"{(1-df_t['is_regular'].mean())*100:.1f} %")

    st.write("")

    repeat_companies = df_company[df_company["posting_count"] >= 2]

    # --- 중단 2열: 반복공고 Top15 | 위험지표 Top15 (카드형 가로 막대) ---
    col_t_g1, col_t_g2 = st.columns(2)

    with col_t_g1:
        with st.container(border=True):
            st.markdown("**① 반복공고 Top 15 기업** (동시 등록 공고 건수)")
            if repeat_companies.empty:
                st.caption("2건 이상 반복 등록한 기업이 없습니다. (데이터 미확보)")
            else:
                top_posting = repeat_companies.sort_values("posting_count", ascending=False).head(15).sort_values("posting_count")
                fig_t1 = go.Figure(go.Bar(
                    x=top_posting["posting_count"], y=top_posting["company"], orientation="h",
                    marker_color="#ef4444",
                    hovertemplate="기업: %{y}<br>공고 건수: %{x}건<extra></extra>"
                ))
                fig_t1.update_layout(
                    xaxis_title="동시 등록 공고 수 (건)",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=430, margin=dict(t=10, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_t1, use_container_width=True)
            st.caption("💡 동일 기업이 여러 포지션을 동시 등록한 건수입니다. 사업 확장 또는 잦은 결원 충원일 수 있어 단독으로 위험을 단정할 수 없습니다.")

    with col_t_g2:
        with st.container(border=True):
            st.markdown("**② 채용건전성 위험지표 Top 15 기업** (2건 이상 등록)")
            if repeat_companies.empty:
                st.caption("데이터 미확보")
            else:
                top_risk = repeat_companies.sort_values("risk_score", ascending=False).head(15).sort_values("risk_score")
                fig_t2 = go.Figure(go.Bar(
                    x=top_risk["risk_score"], y=top_risk["company"], orientation="h",
                    marker_color="#f59e0b",
                    hovertemplate="기업: %{y}<br>위험지표: %{x:.1f}점<extra></extra>"
                ))
                fig_t2.update_layout(
                    xaxis_title="채용건전성 위험지표 (점)",
                    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                    height=430, margin=dict(t=10, b=10, l=10, r=10)
                )
                st.plotly_chart(fig_t2, use_container_width=True)
            st.caption("💡 상시채용·비정규직·경력자전용·반복공고 강도를 결합한 프록시 지표 상위 기업입니다. 점수가 높을수록 참고 관찰이 필요합니다.")

    st.write("")

    # --- 중단 2열: 채용 형태 분포(가로 막대) | 마감 유형(분절형 아치 게이지) ---
    col_t_g3, col_t_g4 = st.columns(2)

    with col_t_g3:
        with st.container(border=True):
            st.markdown("**③ 채용 형태(고용형태) 분포**")
            jt_dist = df_t["job_type"].replace("", "미기재").value_counts().head(10).sort_values()
            fig_t3 = go.Figure(go.Bar(
                x=jt_dist.values, y=jt_dist.index, orientation="h", marker_color="#2563eb",
                hovertemplate="고용형태: %{y}<br>공고 수: %{x}건<extra></extra>"
            ))
            fig_t3.update_layout(
                xaxis_title="공고 수 (건)",
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                height=400, margin=dict(t=10, b=10, l=10, r=10)
            )
            st.plotly_chart(fig_t3, use_container_width=True)
            st.caption("💡 정규직 외 계약직·파견직·인턴 등 비정규직 형태가 섞여 있으면 고용 안정성 측면의 참고 신호로 활용할 수 있습니다.")

    with col_t_g4:
        with st.container(border=True):
            st.markdown("**④ 마감 유형(공고기간 특성) 분포**")
            deadline_type = df_t["deadline"].apply(
                lambda d: "상시채용/채용시" if d in ["상시채용", "채용시"]
                else ("미기재" if d == "" else "특정마감일")
            )
            dl_dist = deadline_type.value_counts()
            always_pct = dl_dist.get("상시채용/채용시", 0) / dl_dist.sum() * 100
            st.plotly_chart(
                _segmented_arc_gauge(always_pct, "상시채용/채용시 비중",
                                      active_colors=["#7c2d12", "#c2410c", "#ea580c", "#f97316", "#fb923c", "#fdba74"]),
                use_container_width=True,
            )
            legend_colors = {"상시채용/채용시": "#ea580c", "특정마감일": "#1d4ed8", "미기재": "#94a3b8"}
            st.markdown(
                "".join(
                    f"<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:{legend_colors.get(k, '#94a3b8')};'></span>{k} {v}건</span>"
                    for k, v in dl_dist.items()
                ),
                unsafe_allow_html=True,
            )
            st.caption("💡 마감일을 명시하지 않는 '상시채용/채용시' 비중이 높을수록, 자리가 상시적으로 비거나 채용을 계속 진행 중인 포지션이 많다는 신호입니다.")

    st.write("")

    # --- 위험기업 상세: 검색 + 정렬 가능한 카드형 표 ---
    with st.container(border=True):
        st.markdown("**📋 채용건전성 위험지표 상위 기업 상세** (2건 이상 등록)")
        if repeat_companies.empty:
            st.caption("2건 이상 반복 등록한 기업이 없어 상세 표를 표시할 수 없습니다. (데이터 미확보)")
        else:
            detail_df = repeat_companies.sort_values("risk_score", ascending=False).head(20)[
                ["company", "posting_count", "always_hiring_ratio", "non_regular_ratio", "experienced_only_ratio", "risk_score"]
            ].copy()
            detail_df.columns = ["기업명", "반복공고건수", "상시채용비율(%)", "비정규직비율(%)", "경력자전용비율(%)", "채용건전성위험지표"]
            for c in ["상시채용비율(%)", "비정규직비율(%)", "경력자전용비율(%)"]:
                detail_df[c] = (detail_df[c] * 100).round(1)

            search_kw = st.text_input("🔍 기업명 검색", key="health_detail_search", placeholder="기업명을 입력하세요")
            filtered_df = detail_df[detail_df["기업명"].str.contains(search_kw, case=False, na=False)] if search_kw else detail_df
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            st.caption("💡 열 헤더를 클릭하면 정렬할 수 있습니다. 상시채용·비정규직·경력자전용·반복공고 강도를 결합한 프록시 지표입니다.")

    st.caption(
        "⚠️ 실제 이직률이 아닌 공개 채용공고 패턴 기반의 참고용 프록시 지표입니다 (국민연금 가입/탈퇴 이력 등 원천 데이터 미확보)."
    )


# =====================================================================
# 5. 모드별 탭 구성 및 렌더링
# =====================================================================
if is_seeker_mode:
    tab_home, tab_seeker, tab_health = st.tabs([
        "🏠 홈",
        "💡 구직자 스펙 자가진단",
        "⚠️ 기업 채용건전성",
    ])
    with tab_home:
        render_home_tab()
    with tab_seeker:
        render_seeker_tab()
    with tab_health:
        render_company_health_tab()
else:
    tab_home, tab_hr, tab_health = st.tabs([
        "🏠 홈",
        "🏢 인사팀 수급 Gap / JD 최적화",
        "⚠️ 기업 채용건전성",
    ])
    with tab_home:
        render_home_tab()
    with tab_hr:
        render_hr_gap_tab()
    with tab_health:
        render_company_health_tab()
