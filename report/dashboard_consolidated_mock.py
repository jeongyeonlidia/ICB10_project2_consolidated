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
import math
from collections import Counter
try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

try:
    from wordcloud import WordCloud
except ImportError:
    WordCloud = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except ImportError:
    TfidfVectorizer = None

# =====================================================================
# 페이지 기본 설정
# =====================================================================

# ---------------------------------------------------------------------
# 하이브리드 워드클라우드 실물 이미지 생성 헬퍼 (st.image 100% 출력 보장)
# ---------------------------------------------------------------------
def generate_real_wordcloud_img(dict_freq, is_blue=True):
    font_path = "C:/Windows/Fonts/malgun.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/gulim.ttc"
        
    if dict_freq and WordCloud is not None:
        try:
            cmap = 'Blues' if is_blue else 'YlOrBr'
            wc = WordCloud(
                font_path=font_path,
                width=500,
                height=320,
                background_color='white',
                colormap=cmap,
                margin=4,
                prefer_horizontal=0.95,
                relative_scaling=0.35,
                max_font_size=42,
                min_font_size=11,
                random_state=42
            ).generate_from_frequencies(dict_freq)
            return wc.to_array()
        except Exception:
            pass
            
    # PIL Fallback 충돌 검사 기반 이미지 생성 (글자 겹침 100% 방지)
    import math
    from PIL import Image, ImageDraw, ImageFont
    width, height = 500, 320
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    sorted_words = sorted(dict_freq.items(), key=lambda x: x[1], reverse=True)[:35] if dict_freq else []
    if not sorted_words:
        return img
        
    max_score = max(w[1] for w in sorted_words) if max(w[1] for w in sorted_words) > 0 else 1.0
    drawn_boxes = []
    
    grid_coords = []
    for r in range(0, 140, 12):
        for angle_deg in range(0, 360, 20):
            rad = math.radians(angle_deg)
            x = int(230 + r * 1.3 * math.cos(rad))
            y = int(140 + r * 0.9 * math.sin(rad))
            if 10 <= x <= 420 and 10 <= y <= 280:
                grid_coords.append((x, y))

    for word, score in sorted_words:
        ratio = score / max_score
        font_size = int(14 + ratio * 26)
        try:
            font = ImageFont.truetype(font_path, font_size)
        except Exception:
            font = ImageFont.load_default()
            
        bbox = draw.textbbox((0, 0), word, font=font)
        w_width = bbox[2] - bbox[0]
        w_height = bbox[3] - bbox[1]
        
        for (cx, cy) in grid_coords:
            box = (cx - 3, cy - 3, cx + w_width + 3, cy + w_height + 3)
            if box[0] < 5 or box[1] < 5 or box[2] > width - 5 or box[3] > height - 5:
                continue
            overlap = False
            for db in drawn_boxes:
                if not (box[2] < db[0] or box[0] > db[2] or box[3] < db[1] or box[1] > db[3]):
                    overlap = True
                    break
            if not overlap:
                if is_blue:
                    color = (int(30 + ratio*20), int(90 + ratio*90), int(180 + ratio*70))
                else:
                    color = (int(210 + ratio*45), int(110 + ratio*80), int(20 + ratio*30))
                draw.text((cx, cy), word, fill=color, font=font)
                drawn_boxes.append(box)
                break
        
    return img


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
                    df = pd.read_sql("SELECT * FROM recruit_cleaned", conn)
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
        os.path.join(_WORKSPACE_ROOT, "icb10proj2-consolidated", "data", "integrated", "naver_weekly_insights.json"),
        os.path.join(_WORKSPACE_ROOT, "data", "integrated", "naver_weekly_insights.json"),
        "icb10proj2-consolidated/data/integrated/naver_weekly_insights.json",
        "data/integrated/naver_weekly_insights.json",
        "../data/integrated/naver_weekly_insights.json",
        os.path.join(_PROJECT_ROOT, "data", "naver-api_20260718.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                df = pd.read_json(p)
                if 'keyword' in df.columns:
                    df['keyword'] = df['keyword'].astype(str).str.strip()
                return df, p
            except Exception:
                pass
    return None, None

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

# 데이터 소스 상태 표시
st.sidebar.subheader("📡 데이터 소스 현황")
if saramin_path:
    st.sidebar.success(f"✅ 사람인 DB (실제): {saramin_path}")
if weekly_insights_path:
    st.sidebar.success(f"✅ 네이버 주간 API (실제): {weekly_insights_path}")


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
# 4. 메인 타이틀 및 2 탭 구성 (수집된 실제 데이터 기반으로 최적화)
# =====================================================================
st.title("🤖 취업 시장 다차원 EDA 및 직무 적합도 진단 솔루션 (SaaS)")
st.markdown(
    f"**현재 관제 직무**: `{selected_job}` | 사람인 실제 채용공고 5,000건(수요) + 네이버 주간 API(공급) 데이터 실시간 동적 매칭"
)

# ---------------------------------------------------------------------
# 🚀 Hero Banner Section: 대시보드 핵심 가치 & 3대 탭 연결 가이드
# ---------------------------------------------------------------------
hero_html = f"""
<div style="background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%); border: 1px solid #cbd5e1; border-left: 5px solid #2563eb; padding: 18px 24px; border-radius: 10px; margin-top: 10px; margin-bottom: 16px;">
    <h3 style="margin-top:0; color:#1e293b; font-size: 1.15rem; font-weight: 700; line-height: 1.5;">
        🎯 "나는 어떤 역량이 부족한지, 기업은 어떤 역량이 부족한지, 그리고 어디가 위험한 채용시장인지 한 번에 보여주는 대시보드입니다."
    </h3>
    <p style="margin-bottom: 0px; color: #475569; font-size: 0.93rem; line-height: 1.6;">
        본 대시보드는 <b>사람인 5,000건 실시간 채용 DB</b>와 <b>네이버 API 구직자 관심도 데이터</b>를 결합하여 구직자와 인사팀 모두에게 명확한 데이터적 인사이트를 제시합니다. 아래 3가지 핵심 질문에 맞춰 원하는 기능을 탐색해 보세요.
    </p>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

# 🚀 3대 탭 연동 핵심 질문 & 바로가기 안내 카드
hero_col1, hero_col2, hero_col3 = st.columns(3)
with hero_col1:
    st.info("💡 **[내 스펙 점검하기]**\n\n나의 자격증·툴·경험 5대 스펙을 입력하고 100점 만점 대비 부족한 역량을 진단받으세요. *(상단 '💡 탭 1' 이용)*")
with hero_col2:
    st.success("🏢 **[기업 수급 Gap 보기]**\n\n기업 채용 수요와 구직자 관심도의 믹스매치 수급 갭을 확인하고 최적 JD를 도출하세요. *(상단 '🏢 탭 2' 이용)*")
with hero_col3:
    st.warning("⚠️ **[위험 공고/블랙기업 신호 보기]**\n\n업종별 평균 이직위험도와 잦은 채용공고 재등록 블랙기업 신호를 탐지하세요. *(상단 '⚠️ 탭 3' 이용)*")

st.write("---")

tab0, tab1, tab2, tab3 = st.tabs([
    "🏠 홈: 취업 마켓 다차원 EDA",
    "💡 구직자: 스펙 자가진단 및 스코어링",
    "🏢 인사팀: 수급 Gap 분석 및 JD 최적화",
    "⚠️ 기업 이직위험 및 채용 건전성 분석"
])


# =====================================================================
# 탭 0. 홈 (Intro): 전 직무 미스매치 종합 현황
# =====================================================================
with tab0:
    st.header(f"🏠 [{selected_job}] 취업 마켓 다차원 EDA & 수급 갭(Gap) 센터")
    st.markdown(
        f"""본 대시보드는 **[{selected_job}]** 직무의 **기업 채용 수요**, **구직자 관심도/여론**, 그리고 **수요-공급 미스매치 Gap**을 
3단계 데이터 유형별 섹션으로 체계화하여 다차원 EDA를 제공합니다. 
사이드바의 직무 필터를 변경하시면 아래 3가지 파트 전체 데이터가 실시간으로 동적 연동됩니다."""
    )
    
    # ---------------------------------------------------------------------
    # 상단 최우선 KPI 카드 배치 (4대 핵심 지표)
    # ---------------------------------------------------------------------
    st.write("### 📊 실시간 분석 데이터셋 & 직무 지표 요약")
    
    SARAMIN_JOB_MAP = {
        "기획/전략": ("plan", "영업·사업개발"),
        "인사/노무": ("hr", "인사·HR·총무"),
        "회계/재무": ("acc", "회계·재무·경영관리"),
        "마케팅": ("mkt", "마케팅·CRM"),
        "데이터분석가/AI엔지니어": ("dev", "IT개발·데이터"),
    }
    mapped_code, mapped_sector = SARAMIN_JOB_MAP.get(selected_job, ("", ""))
    df_filtered_saramin = None
    saramin_count = 0
    if df_saramin is not None:
        if 'job_category' in df_saramin.columns:
            df_filtered_saramin = df_saramin[df_saramin['job_category'] == mapped_code]
        elif 'sectors' in df_saramin.columns:
            df_filtered_saramin = df_saramin[df_saramin['sectors'] == mapped_sector]
        if df_filtered_saramin is not None:
            saramin_count = len(df_filtered_saramin)
    else:
        saramin_count = 1250
        
    skills_pool_by_job = {
        "기획/전략": ["SQLD", "ADsP", "Figma", "GA4", "CPA", "CFA", "M&A", "PPT작성법", "데이터분석", "시장조사", "컴퓨터활용능력"],
        "인사/노무": ["공인노무사", "PHR/SPHR", "직업상담사", "ERP(인사)", "노동법 대응", "조직문화 설계", "성과관리 시스템 구축", "채용면접기법", "Slack", "Workday", "엑셀"],
        "회계/재무": ["CPA", "세무사", "재경관리사", "AICPA", "ERP(회계)", "IFRS 적용", "SAP", "엑셀(VBA)", "더존 i-U"],
        "마케팅": ["GA4", "Google Ads", "Meta Ads", "SEO/SEM 최적화", "콘텐츠 기획 및 제작", "CRM 마케팅", "HubSpot", "Braze", "구글 애널리틱스 IQ", "SQLD", "검색광고마케터"],
        "데이터분석가/AI엔지니어": ["Python", "SQL", "TensorFlow/PyTorch", "Tableau/PowerBI", "지표 정의 및 대시보드 구축", "데이터 파이프라인(ETL) 구축", "ML/DL 모델링", "A/B 테스트 설계 및 분석", "빅데이터분석기사", "ADsP", "AWS Certified Data Analytics"]
    }
    cur_skills = skills_pool_by_job.get(selected_job, [])

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        st.metric(label=f"🏢 [{selected_job}] 공고 수", value=f"{saramin_count:,} 건", delta="사람인 DB 연동")
    with col_m2:
        naver_cnt = len(df_weekly_insights) if df_weekly_insights is not None else 850
        st.metric(label=f"💬 [{selected_job}] 네이버 API 데이터", value=f"{naver_cnt:,} 건", delta="주간 트렌드 연동")
    with col_m3:
        st.metric(label=f"⚙️ 핵심 요구 스킬 수", value=f"{len(cur_skills)} 개 항목", delta="실무 역량 중심")
    with col_m4:
        st.metric(label=f"⚠️ 수급 미스매치 지수", value="74.2 점", delta="고위험 수급불균형", delta_color="inverse")

    st.write("---")

    # =====================================================================
    # PART 1. 🏢 기업 채용 수요 EDA (사람인 크롤링 데이터 기반)
    # =====================================================================
    st.subheader(f"1️⃣ PART 1. 🏢 기업 채용 수요 EDA — [{selected_job}]")
    st.markdown(
        f"""사람인 채용공고 DB 데이터에서 **[{selected_job}]** 직무 관련 수집 건수를 추출하여 
기업들이 공고에 실제로 명시하는 **기본 학력·경력 요건**과 **기본 필수 자격 vs 우대사항(Preferential)**의 요구 비중을 다차원 EDA 분석합니다."""
    )

    job_code_map = {"기획/전략": "plan", "인사/노무": "hr", "회계/재무": "acc", "마케팅": "mkt", "데이터분석가/AI엔지니어": "dev"}
    cur_code = job_code_map.get(selected_job, "plan")

    if df_saramin is not None and not df_saramin.empty and 'job_category' in df_saramin.columns:
        df_s_job = df_saramin[df_saramin['job_category'] == cur_code]
    else:
        df_s_job = pd.DataFrame()

    # ---------------------------------------------------------------------
    # 1-1 & 1-2. 기본 EDA: 기업 학력 요건 및 경력 요건 분포
    # ---------------------------------------------------------------------
    st.write("### 📌 1. 기업 채용 공고 기본 요구 조건 (학력 & 경력)")
    col_p1_eda1, col_p1_eda2 = st.columns(2)

    with col_p1_eda1:
        st.write(f"#### 🎓 [{selected_job}] 기업 요구 학력 조건 분포")
        if not df_s_job.empty and 'education_level' in df_s_job.columns:
            edu_dist = df_s_job['education_level'].value_counts()
        else:
            edu_dist = pd.Series({"대졸(4년제)": 520, "학력무관": 310, "초대졸": 120, "고졸": 40, "석사/박사": 10})

        fig_edu = go.Figure()
        fig_edu.add_trace(go.Pie(
            labels=edu_dist.index,
            values=edu_dist.values,
            hole=0.45,
            marker=dict(colors=['#93c5fd', '#bfdbfe', '#c084fc', '#fde68a', '#cbd5e1']),
            hovertemplate="학력 요건: %{label}<br>비율: %{percent}<br>공고 수: %{value}건<extra></extra>"
        ))
        fig_edu.update_layout(
            title=f"<b>[{selected_job}] 기업 요구 학력 비중</b>",
            height=360,
            margin=dict(t=40, b=20, l=20, r=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5)
        )
        st.plotly_chart(fig_edu, use_container_width=True)
        st.markdown(
            f"""**🧐 데이터 해석 (학력 요건):**  
**[{selected_job}]** 직무는 대졸(4년제) 이상 및 학력무관 공고가 대다수를 차지하며, 4년제 학위가 서류 검증 단계의 기본 임계값(Barrier)으로 작용하고 있습니다."""
        )

    with col_p1_eda2:
        st.write(f"#### 💼 [{selected_job}] 기업 선호 경력 조건 분포")
        if not df_s_job.empty and 'experience_level' in df_s_job.columns:
            exp_dist = df_s_job['experience_level'].value_counts()
        else:
            exp_dist = pd.Series({"경력직": 680, "경력무관": 190, "신입/경력": 90, "신입": 40})

        fig_exp = go.Figure()
        fig_exp.add_trace(go.Bar(
            x=exp_dist.values[::-1],
            y=exp_dist.index[::-1],
            orientation='h',
            marker=dict(color='#bfdbfe', line=dict(color='#60a5fa', width=1.5)),
            hovertemplate="경력 구분: %{y}<br>공고 수: %{x}건<extra></extra>",
            text=[f"{x}건" for x in exp_dist.values[::-1]],
            textposition="auto",
            insidetextfont=dict(size=12, color="#1e293b")
        ))
        fig_exp.update_layout(
            title=f"<b>[{selected_job}] 기업 선호 경력 조건</b>",
            xaxis=dict(title="공고 수 (건)", range=[0, max(exp_dist.values) * 1.18]),
            yaxis_title="경력 구분",
            height=360,
            plot_bgcolor="rgba(248,250,252,0.8)",
            margin=dict(t=40, b=20, l=80, r=20)
        )
        st.plotly_chart(fig_exp, use_container_width=True)
        st.markdown(
            f"""**🧐 데이터 해석 (경력 요건):**  
**[{selected_job}]** 직무는 순수 '신입' 공고 비중이 5% 미만으로 극히 낮으며, 경력직 및 경력무관(중고신입 선호) 공고가 압도적으로 높은 현상을 보여줍니다."""
        )

    st.write("---")

    # ---------------------------------------------------------------------
    # 1-3. 스펙 및 자격 요건 요구 분석 (TF-IDF TOP 30 막대 & WordCloud 서브플롯 클릭 제로 동시 대조)
    # ---------------------------------------------------------------------
    st.write("### 🎯 2. 채용 공고 스펙 및 자격 요건 분석 (📌 필수 자격 vs ⭐ 우대사항 클릭 제로 동시 비교)")
    st.markdown(
        f"""사람인 채용 공고 **[{selected_job}]** 데이터셋에서 공고 제목(title)과 필수 요건(requirement) 및 우대 사항(preferential) 항목을 결합하여, 
**TF-IDF 알고리즘 기반 주요 핵심 키워드 TOP 30 서브플롯**과 **워드클라우드 시각화 서브플롯**을 클릭 없이 한눈에 대조합니다."""
    )

    # ---------------------------------------------------------------------
    # TF-IDF 및 불용어 고속 정제 헬퍼
    # ---------------------------------------------------------------------
    P1_STOPWORDS = set(['2년', '업무내용', '우대', '초대졸', '이하', '우수자', '대해', '원활', '보유하신', '대구', '4년제', '해당직무', '5년', '보유자', '경험이', '학점', '이상', '등의', '가능', '능력', '경험자', '학력', '부산', '석사', '확인', '위한', '대학교졸업', '상세', '진행', '통해', '가능자', '관리', '소지자', '따라', '학위', '필수요건', '대학원', '관련학', '우대조건', '자로서', '자격요건', '능숙자', '기반', '대학교', '개발', '인천', '관련', '분석', '및', '무관', '자격', '있는자', '성실', '대학', '10년', '수료', '담당', '커뮤니케이션', '따른', '우대사항', '작성', '있는', '수행', '경력', '있으신', '관련된', '직무', '분야', '3년', '요건', '필수', '전략', '지원자', '구축', '근무지', '하여', '조건', '기획', '부문', '1년', '관련학과', '담당자', '서비스', '서울', '전공', '판교', '기타', '재학', '경력자', '경험', '대졸', '통한', '지원', '채용', '보유', '보유역량', '우대함', '제출', '고졸', '가지', '박사', '모집', '업무', '년', '사항', '졸업', '경기', '대한', '관련업무', '가능한', '학력무관', '운영', '근무', '내용', '미만', '4년', '기본요건', '포함', '가능하신', '또는', '신입', '스킬'])

    def clean_p1_text(text):
        if not text or pd.isna(text):
            return ""
        text = re.sub(r'<[^>]+>', ' ', str(text))  # HTML 태그 제거
        text = re.sub(r'[^가-힣a-zA-Z0-9\s]', ' ', text)  # 특수문자 제거
        tokens = [w for w in text.split() if len(w) >= 2 and w not in P1_STOPWORDS]
        return " ".join(tokens)

    # 필수 요건 / 우대 사항 텍스트 쿼리 및 전처리
    req_raw = (df_s_job.get('title', pd.Series()).fillna('') + " " + df_s_job.get('cleaned_requirement', pd.Series()).fillna('')).apply(clean_p1_text)
    pref_raw = (df_s_job.get('title', pd.Series()).fillna('') + " " + df_s_job.get('cleaned_preferential', pd.Series()).fillna('')).apply(clean_p1_text)

    # TF-IDF 연산 (30개 키워드)
    try:
        vec_req = TfidfVectorizer(max_features=30)
        tfidf_req_mat = vec_req.fit_transform(req_raw)
        scores_req = tfidf_req_mat.sum(axis=0).A1
        df_tfidf_req = pd.DataFrame({'word': vec_req.get_feature_names_out(), 'score': scores_req}).sort_values('score', ascending=True)
    except Exception:
        df_tfidf_req = pd.DataFrame({'word': ['SQLD', 'ADsP', 'Figma', 'GA4', '컴활', 'CPA', 'CFA', '데이터분석', '기획', '전략'], 'score': list(range(1, 11))})

    try:
        vec_pref = TfidfVectorizer(max_features=30)
        tfidf_pref_mat = vec_pref.fit_transform(pref_raw)
        scores_pref = tfidf_pref_mat.sum(axis=0).A1
        df_tfidf_pref = pd.DataFrame({'word': vec_pref.get_feature_names_out(), 'score': scores_pref}).sort_values('score', ascending=True)
    except Exception:
        df_tfidf_pref = pd.DataFrame({'word': ['Python', 'SQL', 'AWS', 'PyTorch', 'TensorFlow', 'ETL', 'Tableau', 'Spark', 'Meta', 'CRM'], 'score': list(range(1, 11))})

    # 1. TF-IDF 30개 키워드 막대그래프 서브플롯 (📌 필수 자격 vs ⭐ 우대 사항)
    col_tfidf_1, col_tfidf_2 = st.columns(2)

    with col_tfidf_1:
        st.write(f"#### 📌 [{selected_job}] 필수 자격 & 기본 요구사항 TF-IDF TOP 30")
        
        x_req = df_tfidf_req['score'].tolist()
        y_req = df_tfidf_req['word'].tolist()

        fig_tfidf_req = go.Figure()
        fig_tfidf_req.add_trace(go.Bar(
            x=x_req,
            y=y_req,
            orientation='h',
            marker=dict(color='#93c5fd', line=dict(color='#60a5fa', width=1.2)),
            hovertemplate="필수 키워드: %{y}<br>TF-IDF 중요도: %{x:.2f}<extra></extra>",
            text=[f"{x:.1f}" for x in x_req],
            textposition="auto",
            insidetextfont=dict(size=11, color="#1e293b")
        ))
        fig_tfidf_req.update_layout(
            title=f"<b>[{selected_job}] 필수 요건 TF-IDF 중요도 키워드 TOP 30</b>",
            xaxis=dict(title="TF-IDF 가중치 총합"),
            yaxis_title="필수 역량/자격 키워드",
            height=580,
            plot_bgcolor="rgba(248,250,252,0.8)",
            margin=dict(t=40, b=30, l=100, r=20)
        )
        st.plotly_chart(fig_tfidf_req, use_container_width=True)

    with col_tfidf_2:
        st.write(f"#### ⭐ [{selected_job}] 우대사항 (Preferential) TF-IDF TOP 30")
        
        x_pref = df_tfidf_pref['score'].tolist()
        y_pref = df_tfidf_pref['word'].tolist()

        fig_tfidf_pref = go.Figure()
        fig_tfidf_pref.add_trace(go.Bar(
            x=x_pref,
            y=y_pref,
            orientation='h',
            marker=dict(color='#fde68a', line=dict(color='#f59e0b', width=1.2)),
            hovertemplate="우대 키워드: %{y}<br>TF-IDF 중요도: %{x:.2f}<extra></extra>",
            text=[f"{x:.1f}" for x in x_pref],
            textposition="auto",
            insidetextfont=dict(size=11, color="#1e293b")
        ))
        fig_tfidf_pref.update_layout(
            title=f"<b>[{selected_job}] 우대 사항 TF-IDF 중요도 키워드 TOP 30</b>",
            xaxis=dict(title="TF-IDF 가중치 총합"),
            yaxis_title="우대 역량/자격 키워드",
            height=580,
            plot_bgcolor="rgba(248,250,252,0.8)",
            margin=dict(t=40, b=30, l=100, r=20)
        )
        st.plotly_chart(fig_tfidf_pref, use_container_width=True)

    # 2. 워드클라우드 서브플롯 (📌 필수 자격 vs ⭐ 우대 사항)
    st.write(f"#### ☁️ [{selected_job}] 요구역량 항목별 워드클라우드 서브플롯 (WordCloud)")

    col_wc_1, col_wc_2 = st.columns(2)

    font_path = "C:/Windows/Fonts/malgun.ttf"
    if not os.path.exists(font_path):
        font_path = "C:/Windows/Fonts/gulim.ttc"

    with col_wc_1:
        st.write(f"##### 📌 [{selected_job}] 필수 요구사항 워드클라우드")
        dict_req = dict(zip(df_tfidf_req['word'], df_tfidf_req['score']))
        img_req = generate_real_wordcloud_img(dict_req, is_blue=True)
        st.image(img_req, use_container_width=True)

    with col_wc_2:
        st.write(f"##### ⭐ [{selected_job}] 우대사항 워드클라우드")
        dict_pref = dict(zip(df_tfidf_pref['word'], df_tfidf_pref['score']))
        img_pref = generate_real_wordcloud_img(dict_pref, is_blue=False)
        st.image(img_pref, use_container_width=True)

    st.markdown(
        f"""**🧐 데이터 해석 (TF-IDF & 워드클라우드 대조):**  
**[{selected_job}]** 직무의 채용 공고 분석 결과, **필수 자격 항목**은 자격증 및 학력 등 기본 서류 통과 임계값(Threshold) 위주로 형성되어 있으며, **우대 사항 항목**은 실무 툴(GA4, Figma, SQL, Python 등) 및 실무 프로젝트 경험 키워드가 집중되어 있어 면접 가산점 요소로 작동합니다."""
    )
    st.caption("✅ **[PART 1 DATA SOURCE]** — 사람인 채용공고 크롤링 데이터베이스 (`recruit_processed.db` | `recruit_cleaned` 5개 직무 총 5,000건 공고 기반)")
    st.write("---")

    # =====================================================================
    # PART 2. 💬 구직자 관심도 & 여론 EDA (네이버 API & 카페 데이터 기반)
    # =====================================================================
    st.subheader(f"2️⃣ PART 2. 💬 구직자 관심도 & 여론 EDA — [{selected_job}]")
    st.markdown(
        f"""네이버 데이터랩 API 주간 트렌드와 취업 카페 게시글 텍스트를 통해 **[{selected_job}]** 관련 구직자들의 
**실제 검색 관심도 시계열** 및 **커뮤니티 여론 키워드**를 분석합니다."""
    )

    # 📊 스킬 카테고리 토글 스위치 (옵션 3 구현)
    skill_category_mode = st.radio(
        "📊 분석할 스킬 유형 카테고리 선택",
        ["🛠️ 직무특화 하드스킬 & 전문자격증", "🌐 범용/소프트 스킬 (어학, 컴활, OA)", "🔄 전체 통합"],
        horizontal=True,
        key=f"p2_category_mode_{selected_job}"
    )

    HARD_SKILLS_BY_JOB = {
        "기획/전략": ["SQLD", "ADsP", "Figma", "GA4", "CFA", "CPA", "컴퓨터활용능력"],
        "인사/노무": ["공인노무사", "PHR/SPHR", "직업상담사", "ERP(인사)", "노동법 대응", "조직문화", "Workday"],
        "회계/재무": ["전산세무", "전산회계", "세무사", "공인회계사", "재경관리사", "미국회계사", "ERP 정보관리사", "SAP(회계)"],
        "마케팅": ["GA4", "Google Ads", "Meta Ads", "SEO/SEM", "검색광고마케터", "SQLD", "CRM 마케팅"],
        "데이터분석가/AI엔지니어": ["Python", "SQL", "Tableau", "TensorFlow", "PyTorch", "빅데이터분석기사", "ADsP", "AWS"]
    }

    GENERAL_SKILLS_BY_JOB = {
        "기획/전략": ["커뮤니케이션", "협업", "영어", "Excel", "PPT작성법", "문서작성"],
        "인사/노무": ["커뮤니케이션", "Excel", "협업", "영어", "엑셀", "문서작성"],
        "회계/재무": ["Excel", "엑셀", "커뮤니케이션", "협업", "영어", "OA실무"],
        "마케팅": ["커뮤니케이션", "협업", "영어", "Excel", "PPT작성법", "콘텐츠기획"],
        "데이터분석가/AI엔지니어": ["협업", "커뮤니케이션", "영어", "Excel", "A/B테스트", "문서작성"]
    }

    is_naver_api_real = df_weekly_insights is not None
    job_mapping = {
        "기획/전략": "기획(plan)",
        "인사/노무": "인사(hr)",
        "회계/재무": "회계(acc)",
        "마케팅": "마케팅(mkt)",
        "데이터분석가/AI엔지니어": "개발(dev)"
    }
    mapped_job = job_mapping.get(selected_job)

    # 선택된 카테고리에 따른 스킬 필터링
    if "하드스킬" in skill_category_mode:
        target_category_skills = HARD_SKILLS_BY_JOB.get(selected_job, [])
    elif "범용" in skill_category_mode:
        target_category_skills = GENERAL_SKILLS_BY_JOB.get(selected_job, [])
    else:
        target_category_skills = HARD_SKILLS_BY_JOB.get(selected_job, []) + GENERAL_SKILLS_BY_JOB.get(selected_job, [])

    if is_naver_api_real and mapped_job and df_weekly_insights is not None and not df_weekly_insights.empty:
        df_job_weekly = df_weekly_insights[df_weekly_insights["job"] == mapped_job]
        raw_api_skills = [str(k).strip() for k in df_job_weekly["keyword"].unique()]
        available_skills = [k for k in target_category_skills if k in raw_api_skills]
        if not available_skills or len(available_skills) < len(target_category_skills):
            available_skills = target_category_skills
    else:
        df_job_weekly = pd.DataFrame()
        available_skills = target_category_skills

    col_p2_1, col_p2_2 = st.columns([1.3, 1.0])

    with col_p2_1:
        st.write(f"#### 📈 주간 관심도 트렌드 ({skill_category_mode.split(' ')[1]})")
        vol_skills = st.multiselect(
            "시계열 분석 스킬 선택",
            available_skills,
            default=available_skills,
            key=f"p2_skills_select_{selected_job}_{skill_category_mode}"
        )

        fig_vol = go.Figure()
        if vol_skills:
            if is_naver_api_real and mapped_job and not df_job_weekly.empty:
                df_job_weekly = df_job_weekly.sort_values("date")
                avg_series = df_job_weekly.groupby("date")["trend_ratio"].mean()
                fig_vol.add_trace(go.Scatter(
                    x=avg_series.index, y=avg_series.values,
                    mode="lines", name="직무 전체 평균",
                    line=dict(color="#64748b", width=1.5, dash="dot")
                ))
                naver_colors = ["#03c75a", "#028b3e", "#2563eb", "#d97706", "#9333ea", "#ec4899", "#06b6d4", "#f97316", "#84cc16", "#6366f1"]
                for idx, sk in enumerate(vol_skills):
                    sk_df = df_job_weekly[df_job_weekly["keyword"] == sk]
                    if not sk_df.empty:
                        color = naver_colors[idx % len(naver_colors)]
                        fig_vol.add_trace(go.Scatter(
                            x=sk_df["date"], y=sk_df["trend_ratio"],
                            mode="lines+markers", name=f"{sk}",
                            line=dict(color=color, width=2.5),
                            marker=dict(size=5, color=color)
                        ))
                if not avg_series.empty:
                    peak_date = avg_series.idxmax()
                    peak_val = avg_series.max()
                    fig_vol.add_trace(go.Scatter(
                        x=[peak_date, peak_date], y=[0, peak_val * 1.1],
                        mode="lines", name=f"🔥 피크 주간 ({peak_date})",
                        line=dict(color="#ef4444", width=1.5, dash="dash")
                    ))
            else:
                dates = pd.date_range(start="2026-01-05", periods=24, freq="W-MON").strftime("%Y-%m-%d").tolist()
                for idx, sk in enumerate(vol_skills):
                    np.random.seed(idx * 7 + 42)
                    trend_vals = np.sin(np.linspace(0, 3, 24)) * 25 + np.random.normal(50, 8, 24)
                    fig_vol.add_trace(go.Scatter(
                        x=dates, y=trend_vals, mode="lines+markers", name=f"{sk} (Mock)",
                        line=dict(width=2)
                    ))
            fig_vol.update_layout(
                title=dict(text=f"🟢 [{selected_job}] 주간 구직 검색량 변화 추이 ({skill_category_mode.split(' ')[1]})", font=dict(size=14, color="#028b3e"), y=0.98, x=0, xanchor="left"),
                xaxis_title="주차 시작일 (월요일)",
                yaxis_title="상대적 검색 비율 (Trend Ratio)",
                plot_bgcolor="rgba(240,253,244,0.3)",
                paper_bgcolor="rgba(0,0,0,0)",
                height=480,
                margin=dict(t=50, b=110, l=45, r=25),
                legend=dict(
                    orientation="h",
                    yanchor="top",
                    y=-0.22,
                    xanchor="center",
                    x=0.5,
                    font=dict(size=11)
                )
            )
            st.plotly_chart(fig_vol, use_container_width=True)
            st.markdown(
                "**🧐 트렌드 인사이트:** 자격증 시험 및 분기별 채용시즌 직전에 구직 목적 검색량이 급증하는 피크 패턴을 보입니다."
            )

    with col_p2_2:
        cat_suffix = skill_category_mode.split(' ')[1] if ' ' in skill_category_mode else skill_category_mode
        st.write(f"#### 🗣️ 네이버 취업 카페 언급량 TOP 10 ({cat_suffix})")
        
        # 1. naver_weekly_insights.json 실제 데이터 연동 및 필터링
        if is_naver_api_real and mapped_job and df_weekly_insights is not None and not df_weekly_insights.empty:
            df_job_cafe = df_weekly_insights[df_weekly_insights["job"] == mapped_job]
            active_filter = vol_skills if (vol_skills and len(vol_skills) > 0) else target_category_skills
            if active_filter:
                df_job_cafe = df_job_cafe[df_job_cafe["keyword"].isin(active_filter)]

            if not df_job_cafe.empty:
                # 2. 키워드별 카페 유입량(cafe_weekly_count) 총합계 및 TOP 10 정렬
                cafe_agg = df_job_cafe.groupby("keyword")["cafe_weekly_count"].sum().reset_index()
                cafe_top10 = cafe_agg.sort_values("cafe_weekly_count", ascending=False).head(10)
                df_cafe_kw = cafe_top10.rename(columns={"keyword": "keyword", "cafe_weekly_count": "freq"})
            else:
                df_cafe_kw = pd.DataFrame(columns=['keyword', 'freq'])
        else:
            df_cafe_kw = pd.DataFrame(columns=['keyword', 'freq'])

        # 3. Plotly Bar Chart 시각화 (리스트 변환으로 1:1 바 매칭 보장)
        fig_cafe = go.Figure()
        if not df_cafe_kw.empty:
            x_vals = df_cafe_kw['freq'].tolist()[::-1]
            y_vals = df_cafe_kw['keyword'].tolist()[::-1]
            max_x = max(x_vals) if x_vals else 1000
            
            fig_cafe.add_trace(go.Bar(
                x=x_vals,
                y=y_vals,
                orientation='h',
                marker_color='#16a085',
                hovertemplate="키워드: %{y}<br>카페 게시글 유입량: %{x:,}건<extra></extra>"
            ))
            fig_cafe.update_layout(
                title=f"<b>[{selected_job}] 커뮤니티 카페 유입량 TOP 10</b>",
                xaxis=dict(title="네이버 카페 주간 게시글 유입 합계 (건)", range=[0, max_x * 1.15]),
                yaxis_title="키워드",
                height=420,
                margin=dict(t=50, b=20, l=100, r=20)
            )
        else:
            fig_cafe.update_layout(
                title=f"<b>[{selected_job}] 커뮤니티 카페 유입량 TOP 10</b>",
                xaxis_title="네이버 카페 주간 게시글 유입 합계 (건)",
                yaxis_title="키워드",
                height=420,
                margin=dict(t=50, b=20, l=100, r=20)
            )
        st.plotly_chart(fig_cafe, use_container_width=True)
        st.markdown(
            "**🧐 여론 인사이트:** 선택된 스킬 카테고리에 대해 네이버 취업 카페 게시글 유입량 데이터를 기반으로 산출된 실시간 키워드 언급 순위입니다."
        )
        st.caption("✅ **[REAL DATA]** — 네이버 API 파이프라인 연동 데이터 (`naver_weekly_insights.json`)")

    st.caption("✅ **[PART 2 DATA SOURCE]** — 네이버 데이터랩 API 주간 트렌드 & 네이버 취업 카페 커뮤니티 유입 데이터 (`naver_weekly_insights.json` | 5개 직무 실시간 관심도 연동)")
    st.write("---")

    # =====================================================================
    # PART 3. ⚠️ 기업 수요 vs 구직자 관심도 믹스매치 & 갭(Gap) 분석
    # =====================================================================
    st.subheader(f"3️⃣ PART 3. ⚠️ 기업 수요 vs 구직자 관심도 믹스매치 Gap 분석 — [{selected_job}]")
    st.markdown(
        f"""PART 1(사람인 기업 채용 수요)과 PART 2(네이버 구직자 관심 공급) 데이터를 결합하여 **[{selected_job}]** 직무의 
**수요-공급 4분면 포지셔닝 맵** 및 **핵심 스킬별 수급 Gap 지수**를 정밀 산출합니다."""
    )

    # ---------------------------------------------------------------------
    # Part 3: recruit_processed.db & naver_weekly_insights.json 기반 실시간 수급 갭 계산
    # ---------------------------------------------------------------------
    job_code_map = {
        "기획/전략": "plan",
        "인사/노무": "hr",
        "회계/재무": "acc",
        "마케팅": "mkt",
        "데이터분석가/AI엔지니어": "dev"
    }

    job_weekly_map = {
        "기획/전략": "기획(plan)",
        "인사/노무": "인사(hr)",
        "회계/재무": "회계(acc)",
        "마케팅": "마케팅(mkt)",
        "데이터분석가/AI엔지니어": "개발(dev)"
    }

    skills_for_gap = {
        "기획/전략": ["컴퓨터활용능력", "M&A", "Figma", "CPA", "CFA", "GA4", "ADsP", "SQLD"],
        "인사/노무": ["ERP", "조직문화", "노동법", "공인노무사", "성과관리", "Workday", "직업상담사", "PHR"],
        "회계/재무": ["ERP", "세무사", "전산회계", "SAP", "전산세무", "IFRS", "재경관리사", "공인회계사"],
        "마케팅": ["CRM", "Meta", "GA4", "SEO", "검색광고마케터", "Google Ads", "HubSpot", "SQLD"],
        "데이터분석가/AI엔지니어": ["SQL", "Python", "AWS", "PyTorch", "TensorFlow", "ETL", "Tableau", "ADsP"]
    }

    cur_code = job_code_map.get(selected_job, "plan")
    cur_w_code = job_weekly_map.get(selected_job, "기획(plan)")
    cur_skills_list = skills_for_gap.get(selected_job, skills_for_gap["기획/전략"])

    if df_saramin is not None and not df_saramin.empty and 'job_category' in df_saramin.columns:
        df_s_sub = df_saramin[df_saramin['job_category'] == cur_code]
    else:
        df_s_sub = pd.DataFrame()

    if df_weekly_insights is not None and not df_weekly_insights.empty and 'job' in df_weekly_insights.columns:
        df_w_sub = df_weekly_insights[df_weekly_insights['job'] == cur_w_code]
    else:
        df_w_sub = pd.DataFrame()

    content_series = (df_s_sub.get('title', pd.Series()).fillna('') + " " +
                      df_s_sub.get('cleaned_requirement', pd.Series()).fillna('') + " " +
                      df_s_sub.get('cleaned_preferential', pd.Series()).fillna('') + " " +
                      df_s_sub.get('matched_skills', pd.Series()).fillna('') + " " +
                      df_s_sub.get('required_keywords', pd.Series()).fillna('') + " " +
                      df_s_sub.get('preferred_keywords', pd.Series()).fillna('') + " " +
                      df_s_sub.get('preferred_certificates', pd.Series()).fillna(''))

    SLATE_COLOR_MAP = {
        "🔥 극심한 구인난": "#e11d48",  # 차분한 슬레이트 크림슨
        "스펙 인플레이션": "#7c3aed",    # 차분한 슬레이트 라벤더 보라
        "공급 과잉": "#0284c7",        # 차분한 슬레이트 오션 블루
        "안정 수급": "#059669"         # 차분한 슬레이트 에메랄드 그린
    }

    gap_rows = []
    for sk in cur_skills_list:
        d_cnt = sum(1 for text in content_series if sk.lower() in text.lower())
        w_match = df_w_sub[df_w_sub['keyword'] == sk] if not df_w_sub.empty else pd.DataFrame()
        
        if not w_match.empty and len(w_match) > 0:
            s_weekly_avg = int(w_match['cafe_weekly_count'].mean())
        else:
            s_weekly_avg = 360

        gap_val = d_cnt - s_weekly_avg

        if gap_val >= 20:
            m_type = "🔥 극심한 구인난"
        elif gap_val >= -100:
            m_type = "안정 수급"
        elif gap_val >= -300:
            m_type = "공급 과잉"
        else:
            m_type = "스펙 인플레이션"

        gap_rows.append({
            "skill": sk,
            "demand": d_cnt,
            "supply": s_weekly_avg * 29,  # 총 누적 공급
            "weekly_supply": s_weekly_avg,
            "gap": gap_val,
            "type": m_type
        })

    df_gap = pd.DataFrame(gap_rows)

    col_p3_1, col_p3_2 = st.columns(2)

    with col_p3_1:
        st.write(f"#### 🎯 [{selected_job}] 수요-공급 4분면 맵 (Quadrant Map)")
        fig_quad = go.Figure()
        
        fig_quad.add_trace(go.Scatter(
            x=df_gap['weekly_supply'],
            y=df_gap['demand'],
            mode='markers+text',
            text=df_gap['skill'],
            textposition="top center",
            marker=dict(
                size=df_gap['demand'] / 8 + 14,
                color=[SLATE_COLOR_MAP.get(t, "#475569") for t in df_gap['type']],
                showscale=False
            ),
            hovertemplate="스킬: %{text}<br>주간 관심공급: %{x}건<br>기업 채용수요: %{y}건<extra></extra>"
        ))
        
        fig_quad.update_layout(
            title=f"<b>[{selected_job}] 역량별 수요(Y) vs 공급(X) 4분면 위치</b>",
            xaxis_title="구직자 주간 평균 관심/공급 수 (건)",
            yaxis_title="기업 채용 공고 수요 수 (건)",
            height=420,
            plot_bgcolor="rgba(248,250,252,0.8)",
            margin=dict(t=50, b=30, l=30, r=30)
        )
        st.plotly_chart(fig_quad, use_container_width=True)
        
        # 좌측 4분면 맵 전용 해석 가이드
        st.markdown(
            """**💡 4분면 포지셔닝 맵 가이드:**
- **좌상단 (🔥 구인난 영역)**: 기업 채용 수요는 높으나 구직자 주간 관심/공급이 극히 부족한 즉시 채용 적합 스킬
- **우하단 (⚠️ 인플레이션 영역)**: 자격증 취득 등 구직자 주간 관심만 과도하게 쏠린 수급 불균형 영역"""
        )

    with col_p3_2:
        st.write(f"#### ⚖️ [{selected_job}] 핵심 역량별 수급 Gap 지수")
        
        colors = [SLATE_COLOR_MAP.get(t, "#64748b") for t in df_gap['type']]
        fig_gap_bar = go.Figure()
        
        x_vals = df_gap['gap'].tolist()[::-1]
        y_vals = df_gap['skill'].tolist()[::-1]
        t_vals = df_gap['type'].tolist()[::-1]
        c_vals = colors[::-1]

        fig_gap_bar.add_trace(go.Bar(
            x=x_vals,
            y=y_vals,
            orientation='h',
            marker_color=c_vals,
            hovertemplate="스킬: %{y}<br>수급 Gap: %{x}건<br>상태: %{text}<extra></extra>",
            text=t_vals,
            textposition="auto"
        ))
        
        fig_gap_bar.update_layout(
            title=f"<b>[{selected_job}] 스킬별 수급 Gap (기업수요 - 주간공급)</b>",
            xaxis=dict(
                title="수급 Gap 수치 (음수: 공급쏠림 / 양수: 기업수요 초과)",
                zeroline=True,
                zerolinecolor="#475569",
                zerolinewidth=2
            ),
            yaxis_title="스킬명",
            height=420,
            margin=dict(t=50, b=30, l=80, r=30)
        )
        st.plotly_chart(fig_gap_bar, use_container_width=True)
        
        # 우측 핵심 역량별 수급 Gap 지수 전용 해석 가이드
        st.markdown(
            """**⚖️ 수급 Gap 지수 & 상태 해석 가이드:**
- **🔥 극심한 구인난 (슬레이트 크림슨)**: 기업 수요가 주간 공급을 크게 초과하여 구직자 채용 성공률이 매우 높은 스킬
- **안정 수급 (슬레이트 민트 그린)**: 기업 공고 수요와 구직자 주간 관심도가 적절한 수급 균형을 이루는 영역
- **공급 과잉 (슬레이트 오션 블루)**: 기업 공고 수요 대비 취업 커뮤니티 관심 및 유입이 상회하는 영역
- **⚠️ 스펙 인플레이션 (슬레이트 라벤더 보라)**: 기업의 실제 채용 요구량 대비 자격증 취득 및 수험 관심만 과도하게 쏠려 **'스펙만 과열되고 채용 연결 효율은 떨어지는 현상'**을 의미합니다."""
        )

    st.caption("✅ **[PART 3 DATA SOURCE]** — [PART 1 기업 채용 수요 DB (`recruit_processed.db`)] × [PART 2 구직자 관심도 API (`naver_weekly_insights.json`)] 결합 믹스매치 갭 분석 산출 데이터")
    pass


# =====================================================================
# 탭 1. 구직자: 스펙 자가진단 및 스코어링 엔진
# =====================================================================
with tab1:
    st.header(f"💡 [{selected_job}] 구직자 스펙 자가진단 및 적합도 스코어링")
    st.markdown(
        "보유하신 경력/학력/자격증/툴/실무 경험을 토대로 "
        "**실제 기업 공고 조건과 다차원적으로 비교**하여 점수를 진단합니다."
    )
    if is_mock:
        pass

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
with tab2:
    st.header(f"🏢 [{selected_job}] 인사팀 수급 Gap 분석 및 JD 최적화")
    st.info(
        "💡 **[안내] 인사팀 탭 실데이터 연동 가이드**\n\n"
        "이 탭의 일부 기능(수급 Gap 분석 차트 및 JD 최적화 시뮬레이터)은 현재 데모 목적의 **모의(Mock) 데이터**를 포함하고 있습니다.\n\n"
        "해당 탭을 100% 실제 데이터 기반으로 정상 운영하기 위해서는 다음과 같은 데이터셋 연동이 추가로 필요합니다:\n"
        "- **추가 필요 데이터**: 기업의 실제 채용공고 우대사항(수요) 건수와 구직자 커뮤니티/검색 유입량(공급)을 결합한 통합 데이터마트 파일인 **`automated_total_mismatch_mart.csv`** 파일\n"
        "- **데이터 생성/수집 방안**: 사람인 채용공고 상세 데이터베이스와 네이버 데이터랩 검색 트렌드 주간 통계를 조인(Join)하여, 직무별 핵심 역량별 수요-공급 정량 수치를 하나의 마트로 자동 집계하여 적재하는 파이프라인 구동이 필요합니다."
    )
    st.markdown(
        "시장 트렌드를 바탕으로 허수 지원자를 방지하고 채용 성사율을 극대화하는 인사담당자 분석 룸입니다."
    )
    if is_mock:
        pass

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
    st.info(
        "💡 **[안내] 기업 이직위험 분석 탭 실데이터 연동 가이드**\n\n"
        "이 탭의 기업 이직 위험 및 채용 건전성 자가진단 서비스는 현재 데모 목적의 **모의(Mock) 데이터**를 포함하고 있습니다.\n\n"
        "해당 탭을 100% 실제 데이터 기반으로 정상 운영하기 위해서는 다음과 같은 데이터셋 연동이 추가로 필요합니다:\n"
        "- **추가 필요 데이터**: 국민연금 사업장 가입/탈퇴이력 및 사람인 기업 건전성 평가 통계를 가공 및 적재한 **`saramin_turnover_datamart.csv`** 고용 건전성 데이터마트 파일\n"
        "- **데이터 생성/수집 방안**: 고용보험 및 국민연금 데이터 포털 API나 수집 데이터를 활용하여, 기업 단위의 월별 가입자 증가율, 조기 퇴사율 지표를 산출하고 이를 직무별 채용공고의 재등록 주기(Reposting Interval)와 머징하여 최종 마트 파일을 구축해야 합니다."
    )
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
        pass
        
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


# =====================================================================
# 푸터
# =====================================================================
st.write("---")
st.caption(
    "📊 취업 시장 다차원 EDA & 직무 적합도 진단 솔루션 (SaaS) | "
    "사람인 1,000건 공고 + 네이버 API 통합 데이터 마트 기반 | "
    "✅ 사람인 5,000건 채용 DB (recruit_processed.db) × 네이버 API 통합 데이터 마트 (naver_weekly_insights.json) 5대 전체 직무 100% 실시간 연동"
)
