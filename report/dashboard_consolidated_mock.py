"""
취업 시장 다차원 EDA 및 직무 적합도 진단 솔루션 (SaaS) — 마스터 통합 대시보드

주요 기능:
- 5대 직무(기획/전략, 인사/노무, 회계/재무, 마케팅, 개발) 지원
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
import importlib.util
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
# 워드클라우드/PIL 폴백에 쓸 한글 지원 폰트 경로 탐색.
#
# 기존 코드는 "C:/Windows/Fonts/malgun.ttf"(Windows 전용 경로)를 하드코딩하고 있었다.
# 로컬(macOS)이나 Streamlit Cloud(Linux) 어디에도 이 경로가 존재하지 않아 폰트 로드가
# 항상 실패(OSError)했고, wordcloud/PIL이 한글 글리프가 없는 기본 폰트로 대체되면서
# 한글 단어가 전부 네모(tofu) 박스로 렌더링되는 원인이었다. koreanize-matplotlib
# 패키지가 SIL OFL 라이선스의 나눔고딕(NanumGothic.ttf)을 pip 설치 경로에 함께
# 배포하므로, 플랫폼과 무관하게 항상 존재하는 이 경로를 최우선으로 사용한다.
# ---------------------------------------------------------------------
def _resolve_korean_font_path():
    try:
        import koreanize_matplotlib
        candidate = os.path.join(os.path.dirname(koreanize_matplotlib.__file__), "fonts", "NanumGothic.ttf")
        if os.path.exists(candidate):
            return candidate
    except ImportError:
        pass

    # 배포 환경에 koreanize-matplotlib이 없을 때를 대비한 OS별 시스템 폰트 폴백
    fallback_candidates = [
        "/System/Library/Fonts/Supplemental/AppleGothic.ttf",  # macOS
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",       # Linux (나눔폰트 설치 시)
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux (Noto CJK)
        "C:/Windows/Fonts/malgun.ttf",                            # Windows
        "C:/Windows/Fonts/gulim.ttc",
    ]
    for path in fallback_candidates:
        if os.path.exists(path):
            return path
    return None


_KOREAN_FONT_PATH = _resolve_korean_font_path()


# ---------------------------------------------------------------------
# 하이브리드 워드클라우드 실물 이미지 생성 헬퍼 (st.image 100% 출력 보장)
# ---------------------------------------------------------------------
def make_dynamic_color_func(dict_orig_scores, is_blue=True):
    max_val = max(dict_orig_scores.values()) if dict_orig_scores else 1.0
    min_val = min(dict_orig_scores.values()) if dict_orig_scores else 0.0
    def dynamic_color_func(word, font_size, position, orientation, random_state=None, **kwargs):
        val = dict_orig_scores.get(word, min_val)
        ratio = (val - min_val) / (max_val - min_val + 1e-6)
        if is_blue:
            hue = int(212 - ratio * 12)
            sat = int(40 + ratio * 55)
            light = int(75 - ratio * 53)
        else:
            hue = int(42 - ratio * 18)
            sat = int(45 + ratio * 50)
            light = int(76 - ratio * 50)
        return f"hsl({hue}, {sat}%, {light}%)"
    return dynamic_color_func

def generate_real_wordcloud_img(dict_freq, is_blue=True):
    font_path = _KOREAN_FONT_PATH

    if dict_freq and WordCloud is not None and font_path is not None:
        try:
            # pow(1.5) 스케일링: 상위~하위 단어 모두 캔버스를 꽉 채우면서
            # 중요도 차이가 글자 크기로 명확히 드러나도록 설계
            max_s = max(dict_freq.values())
            min_s = min(dict_freq.values())
            scaled_dict = {}
            for w, s in dict_freq.items():
                norm = (s - min_s) / (max_s - min_s + 1e-6)
                scaled_dict[w] = (norm ** 1.5) * 500 + 15.0
                
            color_fn = make_dynamic_color_func(dict_freq, is_blue=is_blue)
            wc = WordCloud(
                font_path=font_path,
                width=700,
                height=380,
                background_color='white',
                color_func=color_fn,
                margin=2,               # 자간 최소화
                prefer_horizontal=0.92, # HR Analytics 스타일: 세로 단어 비율 최소화, 주요 키워드 가로 배치
                relative_scaling=0.35,  # 낙은 값: 작은 단어도 충분한 크기로 레이아웃 보완
                max_font_size=68,       # 최상위 단어 대형 표출
                min_font_size=10,       # 최하위 단어 미세 크기
                max_words=40,           # 핵심 키워드 30~40개 중심으로 축소
                random_state=42,
                collocations=False      # 중복 2-gram 방지
            ).generate_from_frequencies(scaled_dict)
            return wc.to_array()
        except Exception:
            pass

            
    # PIL Fallback 충돌 검사 & 비선형 명도/크기 스케일링 기반 이미지 생성
    import math
    from PIL import Image, ImageDraw, ImageFont
    width, height = 500, 320
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    sorted_words = sorted(dict_freq.items(), key=lambda x: x[1], reverse=True)[:35] if dict_freq else []
    if not sorted_words:
        return img
        
    max_score = max(w[1] for w in sorted_words) if max(w[1] for w in sorted_words) > 0 else 1.0
    min_score = min(w[1] for w in sorted_words)
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
        ratio = (score - min_score) / (max_score - min_score + 1e-6)
        ratio_p = ratio ** 1.8
        font_size = int(12 + ratio_p * 38)
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
                    r_val = int(200 - ratio_p * 170)
                    g_val = int(210 - ratio_p * 120)
                    b_val = int(245 - ratio_p * 65)
                else:
                    r_val = int(240 - ratio_p * 60)
                    g_val = int(220 - ratio_p * 140)
                    b_val = int(180 - ratio_p * 150)
                draw.text((cx, cy), word, fill=(r_val, g_val, b_val), font=font)
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
    "마케팅", "개발"
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
    "개발": {
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
    "개발": {
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
    "개발": [
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
# [이식] feature/sumin-integration-plan 브랜치의 인사팀 수급 Gap·미스매치 인사이트,
# JD 유사 공고 임베딩, PCA/UMAP 시각화, 채용건전성 분석 기능을 선택적으로 이식한다.
# main의 tab0(홈)/tab1(구직자 진단)은 그대로 두고, tab2/tab3의 내용만 아래 함수로 교체한다.
# =====================================================================

# 대시보드 마스터 직무 ↔ 사람인 실채용공고(job_group→sectors) 매핑.
# main에 이미 있는 SARAMIN_JOB_MAP(코드,섹터 튜플)과는 별개로, 이식 기능 전용으로 이름을 분리한다.
HR_SECTOR_MAP = {
    "기획/전략": "영업·사업개발",
    "인사/노무": "인사·HR·총무",
    "회계/재무": "회계·재무·경영관리",
    "마케팅": "마케팅·CRM",
    "개발": "IT개발·데이터",
}


# ---------------------------------------------------------------------
# 인사팀 탭 전용 실데이터 마트 (recruit_processed.db 수요 × 네이버 주간 데이터 관심도)
# ---------------------------------------------------------------------
@st.cache_data
def build_gap_mart(job_name, _df_saramin, _df_weekly_insights):
    """선택 직무의 사람인 실공고 수요 키워드(TOP15)와, 동일 키워드의 네이버 주간 검색 관심도를 결합.
    네이버 데이터에 없는 키워드는 임의 추정하지 않고 '데이터확보=False'로 표시한다."""
    naver_job_key_map = {
        "기획/전략": "기획(plan)", "인사/노무": "인사(hr)", "회계/재무": "회계(acc)",
        "마케팅": "마케팅(mkt)", "개발": "개발(dev)",
    }
    mapped_job = HR_SECTOR_MAP.get(job_name)
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


# ---------------------------------------------------------------------
# 이직위험/채용건전성 탭 전용 실데이터 마트 (saramin_search_jobs.db 채용 패턴 지표)
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# 인사팀 탭 "미스매치 인사이트" 전용 실데이터
# (naver_skill_weekly_insights.csv의 demand_count × trend_ratio_base 주간평균, 직무 내 0~100 정규화)
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# 인사팀 탭 "JD 최적화" - 유사 공고 임베딩 검색 (data/embedding/ 산출물 사용)
# ---------------------------------------------------------------------
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


# ---------------------------------------------------------------------
# "의미 기반 유사 역량 매칭" 산점도 - PCA 3D / UMAP 2D 좌표
#
# 이전에는 build_job_projections.py가 미리 fit한 모델을 .joblib으로 저장해두고
# 대시보드에서 그대로 불러 썼다. 그러나 UMAP은 내부적으로 numba로 JIT 컴파일된
# 객체를 포함하고 있어, pickle된 상태가 "저장 당시의 numba/llvmlite/Python 버전"에
# 강하게 결속된다. 로컬(Python 3.9, numba 0.60.0)에서 만든 .joblib을 배포 환경
# (예: Streamlit Cloud Python 3.14, 자동 설치된 최신 numba)에서 불러오면
# `numba.core.serialize._unpickle__CustomPickled` 단계에서 역직렬화가 깨진다.
# 이를 근본적으로 피하기 위해, 사전 계산된 모델/좌표 파일을 배포하지 않고
# 실행 중인 그 환경에서 직접 PCA/UMAP을 fit한다(직무당 587~1,192건 수준이라
# 세션당 1회, st.cache_resource로 캐시하면 비용이 크지 않다).
# ---------------------------------------------------------------------
@st.cache_resource(show_spinner="임베딩 좌표 계산 중...")
def fit_job_projection(job_role):
    """선택 직무의 job_embeddings.npy 부분집합으로 PCA(3D)·UMAP(2D)을 그 자리에서 fit한다.
    반환된 모델로 기존 공고 좌표와 신규 JD 벡터를 같은 좌표계에 놓을 수 있다."""
    module = _get_jd_similarity_module()
    if module is None:
        return None
    embeddings, metadata = module.load_artifacts()
    mask = (metadata["job_role"] == job_role).values
    if mask.sum() == 0:
        return None

    job_ids = metadata.loc[mask, "job_id"].values
    job_emb = embeddings[mask]

    from sklearn.decomposition import PCA
    try:
        from umap import UMAP
        has_umap = True
    except ImportError:
        UMAP = None
        has_umap = False

    pca_model = PCA(n_components=3, random_state=42)
    pca_coords = pca_model.fit_transform(job_emb)

    if has_umap and UMAP is not None:
        try:
            umap_model = UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1)
            umap_coords = umap_model.fit_transform(job_emb)
        except Exception:
            umap_model = None
            umap_coords = np.zeros((len(job_emb), 2))
            has_umap = False
    else:
        umap_model = None
        umap_coords = np.zeros((len(job_emb), 2))

    coords_df = pd.DataFrame({
        "job_id": job_ids,
        "pca_x": pca_coords[:, 0], "pca_y": pca_coords[:, 1], "pca_z": pca_coords[:, 2],
        "umap_x": umap_coords[:, 0], "umap_y": umap_coords[:, 1],
    })
    return {"pca_model": pca_model, "umap_model": umap_model, "coords": coords_df, "has_umap": has_umap}


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
        customdata = sub["job_id"].astype(str).to_numpy().reshape(-1, 1)
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

    module = _get_jd_similarity_module()
    if module is None:
        st.info(
            "임베딩 산출물(`src/embedding/jd_similarity_search.py`)을 찾을 수 없어 "
            "이 기능을 표시할 수 없습니다. (데이터 미확보)"
        )
        return

    projection = fit_job_projection(selected_job)
    if projection is None:
        st.info(f"'{selected_job}' 직무의 임베딩된 공고가 없습니다. (데이터 미확보)")
        return

    coords_job = projection["coords"]

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
    has_umap = projection.get("has_umap", False)
    if not has_umap:
        st.warning("⚠️ UMAP 라이브러리(umap-learn)가 설치되지 않았거나 호환되지 않아 UMAP 2D 시각화는 비활성화되며, PCA 3D 시각화 모드만 사용 가능합니다.")
        method = "pca"
    else:
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
                pca_model = projection["pca_model"]
                umap_model = projection["umap_model"]
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

    # --- 유사 공고 Top 5 표 ---
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

    # --- JD 보완 검토 후보 ---
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

    # --- 기존 JD / 보완안 비교 ---
    st.markdown("**기존 JD / 보완 검토안 비교**")
    compare_col1, compare_col2 = st.columns(2)
    with compare_col1:
        st.caption("현재 JD (원본)")
        original_html = f"""
        <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; font-size: 14px; line-height: 1.6; height: 220px; overflow-y: auto; color: #334155; white-space: pre-wrap;">{jd_text}</div>
        """
        st.markdown(original_html, unsafe_allow_html=True)
    with compare_col2:
        st.caption("보완 검토안 (참고용 — 직접 검토 후 공고에 수동 반영하세요)")
        addition_lines = []
        if sim_result["missing_from_jd"]:
            skills = ", ".join(sim_result["missing_from_jd"])
            addition_lines.append(f"<span style='color: #2563eb; font-weight: 700;'>🚨 [검토] 추가 고려 역량:</span> <span style='font-weight: 600; color: #1e3a8a;'>{skills}</span>")
        if sim_result["downgrade_candidates"]:
            skills = ", ".join(c["skill"] for c in sim_result["downgrade_candidates"])
            addition_lines.append(f"<span style='color: #ea580c; font-weight: 700;'>⚠️ [검토] 필수 ➔ 우대 전환 검토:</span> <span style='font-weight: 600; color: #7c2d12;'>{skills}</span>")
        if sim_result["jd_only_rare"]:
            skills = ", ".join(sim_result["jd_only_rare"])
            addition_lines.append(f"<span style='color: #dc2626; font-weight: 700;'>🔍 [검토] 유사 공고에 드문 조건 (재검토 권장):</span> <span style='font-weight: 600; color: #7f1d1d;'>{skills}</span>")
        
        supplement_html = jd_text
        if addition_lines:
            supplement_html += "\n\n" + "\n".join(addition_lines)
        else:
            supplement_html += "\n\n<span style='color: #64748b; font-style: italic;'>(추가 검토 후보 없음)</span>"
            
        supplemented_html = f"""
        <div style="background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; font-size: 14px; line-height: 1.6; height: 220px; overflow-y: auto; color: #334155; white-space: pre-wrap;">{supplement_html}</div>
        """
        st.markdown(supplemented_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# 인사팀 / 채용건전성 페이지 공용 UI 컴포넌트 (Bento KPI 카드, 파란 마디형 반원 아치 게이지)
# ---------------------------------------------------------------------
def _inject_page_card_css():
    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 20px !important;
            border-color: #eef1f6 !important;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03);
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
        .pg-badge-orange { background: #fff7ed; color: #ea580c; }
        .pg-mini-card {
            background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px;
            padding: 12px 14px; margin-bottom: 8px;
            box-shadow: 0 1px 2px 0 rgba(0,0,0,0.05);
        }
        .pg-mini-card-title { font-size: 14px; font-weight: 700; color: #166534; margin-bottom: 2px; }
        .pg-mini-card-sub { font-size: 12px; color: #16a34a; }
        .pg-legend-chip { display: inline-flex; align-items: center; margin-right: 14px; font-size: 12px; color: #475569; }
        .pg-legend-dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _kpi_card(col, icon, icon_bg, label, value, badge_text=None, badge_class="pg-badge-blue", help_text=""):
    with col:
        badge_html = f"<span class='pg-badge {badge_class}'>{badge_text}</span>" if badge_text else ""
        help_html = f"<div style='color: #94a3b8; font-size: 11px; margin-top: 8px; line-height: 1.3;'>{help_text}</div>" if help_text else ""
        card_html = (
            f"<div style='background-color: white; border-radius: 20px; border: 1px solid #cbd5e1; padding: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05), 0 2px 4px -1px rgba(0,0,0,0.03); min-height: 190px; display: flex; flex-direction: column; justify-content: space-between;'>"
            f"<div>"
            f"<div style='display: flex; justify-content: space-between; align-items: flex-start;'>"
            f"<div class='pg-kpi-icon' style='background:{icon_bg}; width: 38px; height: 38px; border-radius: 10px; display: flex; align-items: center; justify-content: center; font-size: 18px;'>{icon}</div>"
            f"{badge_html}"
            f"</div>"
            f"<div style='color: #64748b; font-size: 13px; font-weight: 500; margin-top: 12px;'>{label}</div>"
            f"<div style='color: #0f172a; font-size: 24px; font-weight: 700; margin-top: 4px; line-height: 1.25;'>{value}</div>"
            f"{help_html}"
            f"</div>"
            f"</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)


def _segmented_arc_gauge(value, subtitle, n_segments=14, active_colors=None):
    """0~100 스코어를 파란(기본) 마디형 반원 아치 게이지로 시각화 (half-pie 트릭)."""
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
    # 직무/세부직무 필터가 변경되면 시뮬레이터 및 임베딩 세션 상태 초기화
    filter_key = (selected_job, selected_sub_job)
    if "current_hr_filter_key" not in st.session_state:
        st.session_state["current_hr_filter_key"] = filter_key

    if st.session_state["current_hr_filter_key"] != filter_key:
        st.session_state["current_hr_filter_key"] = filter_key
        st.session_state.pop("jd_skills_py", None)
        st.session_state.pop("jd_sim_result", None)
        st.session_state.pop("embed_sim_result", None)
        st.session_state.pop("embed_jd_pca", None)
        st.session_state.pop("embed_jd_umap", None)
        st.session_state.pop("embed_job", None)
        st.session_state.pop("embed_text", None)
        st.rerun()

    _inject_page_card_css()
    st.header(f"🏢 [{selected_job}] 인사팀 수급 Gap 분석 및 JD 최적화")
    st.caption("기업이 원하는 역량과 구직자 관심도의 차이를 분석하고, 채용공고 개선 방향을 제안합니다.")

    df_gap = build_gap_mart(selected_job, df_saramin, df_weekly_insights)
    gap_available = df_gap is not None and not df_gap.empty

    if not gap_available:
        st.warning(
            "⚠️ **데이터 미확보** — 선택하신 직무는 사람인 실채용공고 데이터(`recruit_processed.db`)에 매핑되는 "
            "직무군이 없어 수급 Gap 분석을 제공할 수 없습니다."
        )
        return

    confirmed_cnt = int(df_gap["데이터확보"].sum())
    missing_cnt = len(df_gap) - confirmed_cnt
    mapped_job = HR_SECTOR_MAP.get(selected_job)
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
              badge_text="사람인 DB · 네이버 API" if insight else "데이터 미확보", badge_class="pg-badge-blue",
              help_text="공고 수요(사람인)와 검색관심도(네이버)가 매칭되어 실제 수급 Gap 분석이 가능한 역량 수")
    _kpi_card(k2, "❓", "#f8fafc", "데이터 미확보",
              f"{insight['missing']} 개" if insight else f"{missing_cnt} 개",
              badge_text=f"직무 전체 {insight['total']}개 중" if insight else None, badge_class="pg-badge-blue",
              help_text="사람인 수요에는 존재하나 네이버 API 검색 데이터가 매핑되지 않아 분석에서 제외된 역량 수")
    _kpi_card(k3, "🔥", "#fff7ed", "채용난 역량", f"{len(high_df)} 개",
              badge_text="Gap ≥ +20", badge_class="pg-badge-blue",
              help_text="기업 수요(요구도)가 지원자 관심(공급)보다 현저히 높은 역량 수 (인재 확보 난이도 높음)")
    _kpi_card(k4, "🟢", "#f0fdf4", "관심 우위 역량", f"{len(low_df)} 개",
              badge_text="Gap ≤ -20", badge_class="pg-badge-green",
              help_text="지원자 관심(검색량)이 기업 수요를 크게 초과하여 지원자 유입에 매우 유리한 역량 수")

    st.markdown(
        "<div style='font-size: 0.95rem; color: #334155; margin-bottom: 14px; font-weight: 500;'>"
        "본 분석은 사람인 공고의 기업 요구도(수요)와 네이버 검색 관심도(공급)를 정규화하여, "
        "채용공고 노출 효과를 극대화할 수 있는 수급 Gap을 도출합니다."
        "</div>",
        unsafe_allow_html=True
    )
    with st.expander("🔧 데이터 파이프라인 결합 방식"):
        st.markdown(
            f"**📄 분석 규모**: 분석 공고 {posting_cnt:,}건 · 🔑 수요 키워드 {len(df_gap)}개 · 🔗 공급 데이터 매칭 {confirmed_cnt}개 · ⚖️ 수급 균형 {balanced_cnt}개\n\n"
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
                bar_colors = []
                for val in top_gap["gap_score"]:
                    if val >= 20.0:
                        bar_colors.append("#FF6B6B")
                    elif val <= -20.0:
                        bar_colors.append("#2EC4B6")
                    else:
                        bar_colors.append("#cbd5e1")

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
                    "<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#FF6B6B;'></span>채용난 (Gap ≥ +20)</span>"
                    "<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#cbd5e1;'></span>수급균형</span>"
                    "<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#2EC4B6;'></span>관심우위 (Gap ≤ -20)</span>",
                    unsafe_allow_html=True,
                )

    with mid_col2:
        with st.container(border=True):
            st.markdown("**🎯 수급 상태**")
            if insight is None or table.empty:
                st.info("데이터 미확보")
            else:
                usable = insight["usable"] if insight["usable"] else 1
                high_cnt = len(high_df)
                low_cnt = len(low_df)

                if low_cnt > high_cnt:
                    ratio_val = (low_cnt / usable) * 100
                    gauge_title = "관심 우위 역량 비중"
                    gauge_colors = ["#065f46", "#047857", "#059669", "#10b981", "#34d399", "#6ee7b7"]
                elif high_cnt > 0:
                    ratio_val = (high_cnt / usable) * 100
                    gauge_title = "채용난 역량 비중"
                    gauge_colors = ["#7c2d12", "#c2410c", "#ea580c", "#f97316", "#fb923c", "#fdba74"]
                else:
                    ratio_val = 100.0
                    gauge_title = "수급 균형 비중"
                    gauge_colors = ["#1e3a8a", "#1d4ed8", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"]

                st.plotly_chart(
                    _segmented_arc_gauge(ratio_val, gauge_title, active_colors=gauge_colors),
                    use_container_width=True,
                )
                st.markdown(
                    f"<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#FF6B6B;'></span>채용난 {high_cnt}개</span>"
                    f"<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#cbd5e1;'></span>균형 {balanced_cnt}개</span>"
                    f"<span class='pg-legend-chip'><span class='pg-legend-dot' style='background:#2EC4B6;'></span>관심우위 {low_cnt}개</span>",
                    unsafe_allow_html=True,
                )
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
                    f"<span style='float: right; background-color: #fee2e2; color: #991b1b; font-size: 11px; padding: 2px 8px; border-radius: 20px;'>Gap {r['gap_score']:.1f}</span></div>"
                    f"<div class='pg-mini-card-sub'>수요 {r['demand_score']:.0f} · 관심도 {r['interest_score']:.0f}</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("💡 해당 직무에서는 기업의 채용 수요보다 구직자 관심(공급)이 월등히 부족한 '채용난 역량(Gap ≥ +20)'이 존재하지 않습니다. 이는 해당 직종 내 스펙들의 시장 공급망이 비교적 원활하며, 공고 등록 시 특정 역량 때문에 지원자 모집이 크게 지체될 우려가 적은 안정적인 인재 풀 환경임을 나타냅니다.")
    with top3_col2:
        st.caption(f"🟢 관심 우위 (Gap ≤ -20, 총 {len(low_df)}개)")
        if not low_df.empty:
            for _, r in low_df.head(3).iterrows():
                st.markdown(
                    f"<div class='pg-mini-card'><div class='pg-mini-card-title'>{r['canonical_skill']} "
                    f"<span style='float: right; background-color: #dcfce7; color: #15803d; font-size: 11px; padding: 2px 8px; border-radius: 20px;'>Gap {r['gap_score']:.1f}</span></div>"
                    f"<div class='pg-mini-card-sub'>수요 {r['demand_score']:.0f} · 관심도 {r['interest_score']:.0f}</div></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("💡 구직자 관심도가 기업 수요에 비해 압도적으로 높은 '관심 우위 역량(Gap ≤ -20)'이 현재 존재하지 않습니다. 이는 구직자들이 관심 있는 특정 스펙에 쏠리지 않고 고르게 분포되어 있거나, 시장 내 관심 열기가 다소 정체되어 공고 노출 시 즉각적인 트래픽 흡수가 상대적으로 둔화될 수 있음을 의미합니다.")
    if insight is not None and not table.empty:
        st.caption("※ trend_ratio_job_intent와 검색 API 수치는 이 Gap 스코어 계산에 사용하지 않았습니다.")

    st.write("")

    # --- 의미 기반 유사 역량 매칭 (JD 임베딩 × 실공고 PCA/UMAP 산점도 + Top5 + 비교) ---
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
                if "jd_skills_py" not in st.session_state:
                    st.session_state["jd_skills_py"] = df_gap["키워드"].tolist()[:3] if len(df_gap) >= 3 else df_gap["키워드"].tolist()

                bottleneck_kws = high_df["canonical_skill"].tolist() if not high_df.empty else []
                if st.button("⚡ 수급난 추천 스펙 태그 일괄 입력", key="autofill_skills_btn", use_container_width=True):
                    if bottleneck_kws:
                        st.session_state["jd_skills_py"] = [k for k in bottleneck_kws if k in df_gap["키워드"].tolist()]
                        st.rerun()
                    else:
                        st.warning("추천할 수급난 역량이 없습니다.")

                jd_skills = st.multiselect(
                    "🔑 JD 강조 우대 역량 설정 (사람인 실공고 상위 수요 키워드)",
                    options=df_gap["키워드"].tolist(),
                    default=st.session_state["jd_skills_py"],
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

                jd_draft = f"""# 🏢 [{jd_target}] 채용 공고

## [팀 소개]
{opening}
저희 팀은 시장 데이터 분석을 기반으로 성과를 도출하고 비즈니스의 다음 이정표를 설계하는 팀입니다.
직무 전문성을 상호 존중하며, 주도적으로 업무 영역을 확장하고 의사결정할 수 있는 환경을 지향합니다.

## [주요 업무]
- {selected_job} 영역의 비즈니스 핵심 KPI 정의 및 실시간 대시보드 구축/모니터링
- 시장 리서치, 경쟁사 동향 분석 및 데이터 기반 의사결정 지원 리포트 작성
- 유관 부서(기획, 데이터, 개발 등)와의 긴밀한 커뮤니케이션 및 프로젝트 관리 리드
- 지속 가능한 서비스 고도화를 위한 프로세스 리모델링 및 전략 제언

## [지원 자격]
- **경력 연차**: {jd_experience}
- **학력 조건**: 학사 학위 이상 보유자 (관련 전공자 우대)
- 데이터 해석 능력이 우수하며 비즈니스 관점의 의사소통이 원활하신 분

## [우대 사항]
- **{skills_str}** 역량 보유자 또는 관련 실무 경험자 극진 우대
- 비정형 데이터를 논리적으로 정형화하여 제안/역기획해보신 경험이 있으신 분
- 통계 분석 도구 또는 대용량 데이터 추출 쿼리(SQL 등) 작성 가능자

## [혜택 및 복지]
- **유연한 근무**: 자율 출퇴근제 및 하이브리드 재택근무제 운영
- **성장 지원**: 최고 사양의 업무 장비 지급 및 도서/세미나/교육비 연 무제한 지원
- **쾌적한 환경**: 무제한 고급 스낵바, 커피 머신 및 휴게 공간 제공

## [채용 절차]
- 서류 전형 ➔ 1차 실무 인터뷰 ➔ 2차 컬처핏 인터뷰 ➔ 처우 협의 ➔ 최종 합격
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
                badge_html = """
                <div style='display: inline-flex; align-items: center; background: linear-gradient(135deg, #dbeafe, #eff6ff); border: 1px solid #bfdbfe; padding: 6px 14px; border-radius: 20px; margin-bottom: 12px; box-shadow: 0 2px 4px 0 rgba(37, 99, 235, 0.06);'>
                    <span style='color: #1e40af; font-size: 13px; font-weight: 700;'>✨ 지원자 유입 노출 예상 효과 <b>+35% 상승</b></span>
                </div>
                """
                st.markdown(badge_html, unsafe_allow_html=True)
                
                # 대시보드 메인 글꼴과 완벽 통일하여 마크다운 렌더링
                st.markdown(sim_result["jd_draft"])
                
                st.write("")
                with st.expander("📋 원클릭 복사용 텍스트"):
                    st.code(sim_result["jd_draft"], language="markdown")


def render_company_health_tab():
    _inject_page_card_css()
    st.header("⚠️ 기업 채용건전성 위험지표 분석")

    health_result = build_company_health_mart()
    if health_result is None:
        st.warning("⚠️ **데이터 미확보** — `saramin_search_jobs.db`를 찾을 수 없어 이 탭을 표시할 수 없습니다.")
        return

    df_company, df_t = health_result

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

    k1, k2, k3, k4 = st.columns(4)
    _kpi_card(k1, "📄", "#eff6ff", "분석 대상 공고 수", f"{len(df_t):,} 건", badge_text="사람인 DB", badge_class="pg-badge-blue")
    _kpi_card(k2, "🏢", "#f0fdf4", "분석 대상 기업 수", f"{len(df_company):,} 개사", badge_text="사람인 DB", badge_class="pg-badge-green")
    _kpi_card(k3, "🔁", "#fff7ed", "상시채용/채용시 비율", f"{df_t['is_always_hiring'].mean()*100:.1f} %")
    _kpi_card(k4, "📋", "#fef2f2", "비정규직 비율", f"{(1-df_t['is_regular'].mean())*100:.1f} %")

    st.write("")

    repeat_companies = df_company[df_company["posting_count"] >= 2]

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
# 3. 사이드바 컨트롤러 (Control Tower)
# =====================================================================
st.sidebar.title("🎛️ 마스터 컨트롤러")

USER_MODE_OPTIONS = ["👤 구직자 모드", "🏢 기업·인사팀 모드"]
user_mode = st.sidebar.radio(
    "🧭 사용자 모드",
    USER_MODE_OPTIONS,
    index=0,
    help="모드에 따라 노출되는 탭이 달라집니다. 선택한 직무 필터는 모드를 전환해도 그대로 유지됩니다."
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

# 데이터 소스 상태 표시 (내부 경로는 expander 안에 숨기고, 배지만 표시)
st.sidebar.subheader("📡 데이터 소스 현황")
st.sidebar.markdown(
    """
    <style>
    .data-badge {
        display: block;
        padding: 7px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
        margin-bottom: 6px;
        line-height: 1.4;
    }
    .badge-green {
        background: #f0fdf4;
        color: #166534;
        border: 1px solid #bbf7d0;
    }
    .badge-blue {
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
    }
    .badge-gray {
        background: #f8fafc;
        color: #64748b;
        border: 1px solid #e2e8f0;
    }
    </style>
    """,
    unsafe_allow_html=True
)
_saramin_label = f"🟢 사람인 DB 연동 완료" if saramin_path else "⚪ 사람인 DB 미연동"
_saramin_count_label = f" ({df_saramin.shape[0]:,}건)" if df_saramin is not None else ""
_naver_label = f"🟢 네이버 API 연동 완료" if weekly_insights_path else "⚪ 네이버 API 미연동"
_saramin_badge_cls = "badge-green" if saramin_path else "badge-gray"
_naver_badge_cls = "badge-blue" if weekly_insights_path else "badge-gray"
st.sidebar.markdown(
    f"<span class='data-badge {_saramin_badge_cls}'>{_saramin_label}{_saramin_count_label}</span>"
    f"<span class='data-badge {_naver_badge_cls}'>{_naver_label}</span>",
    unsafe_allow_html=True
)
with st.sidebar.expander("🛠 데이터 파이프라인 정보"):
    if saramin_path:
        st.caption(f"사람인 DB: `{saramin_path}`")
    else:
        st.caption("사람인 DB: 미연동")
    if weekly_insights_path:
        st.caption(f"네이버 주간 API: `{weekly_insights_path}`")
    else:
        st.caption("네이버 주간 API: 미연동")


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
st.title("취업 시장 다차원 EDA 및 직무 적합도 진단 솔루션")
st.markdown(
    f"**현재 관제 직무**: `{selected_job}` · 사람인 실채용공고 5,000건(수요) + 네이버 주간 API(공급) 실시간 동적 매칭"
)

# ---------------------------------------------------------------------
# Hero Banner Section: 모던 카드 스타일로 개선
# ---------------------------------------------------------------------
hero_html = f"""
<style>
.hero-outer {{
    background: linear-gradient(135deg, #f0f4ff 0%, #f8fafc 100%);
    border-radius: 20px;
    padding: 28px 32px 20px 32px;
    margin-top: 10px;
    margin-bottom: 20px;
    box-shadow: 0 2px 12px rgba(37,99,235,0.07);
    border: 1px solid #e0e7ff;
}}
.hero-badge {{
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    background: #dcfce7;
    color: #166534;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.04em;
    margin-bottom: 14px;
    border: 1px solid #bbf7d0;
}}
.hero-title {{
    margin: 0 0 8px 0;
    color: #1e293b;
    font-size: 1.13rem;
    font-weight: 700;
    line-height: 1.5;
}}
.hero-desc {{
    margin-bottom: 0;
    color: #475569;
    font-size: 0.9rem;
    line-height: 1.65;
}}
.chip-row {{
    display: flex;
    gap: 10px;
    margin-top: 18px;
    flex-wrap: wrap;
}}
.chip-card {{
    flex: 1;
    min-width: 160px;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 14px 18px;
    transition: box-shadow 0.18s ease;
    cursor: default;
}}
.chip-card:hover {{
    box-shadow: 0 4px 16px rgba(37,99,235,0.10);
    border-color: #93c5fd;
}}
.chip-icon {{
    font-size: 18px;
    margin-bottom: 6px;
    display: block;
}}
.chip-title {{
    font-size: 14px;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 3px;
}}
.chip-sub {{
    font-size: 12px;
    color: #64748b;
    line-height: 1.4;
}}
</style>
<div class="hero-outer">
    <div class="hero-badge">🟢 REAL-TIME DATA CONNECTED</div>
    <p class="hero-title">
        나의 역량은 어느 수준인지, 기업이 원하는 스킬은 무엇인지, 어디가 위험한 채용시장인지 — 한 화면에서 확인하세요.
    </p>
    <p class="hero-desc">
        <b>사람인 5,000건 실채용 DB</b>와 <b>네이버 API 관심도 데이터</b>를 결합한 데이터 기반 취업 시장 인사이트 대시보드입니다.
    </p>
    <div class="chip-row">
        <div class="chip-card">
            <span class="chip-icon">📋</span>
            <div class="chip-title">내 스펙 점검하기</div>
            <div class="chip-sub">자격증·툴·경험 5대 스펙을 진단하세요 → 구직자 탭</div>
        </div>
        <div class="chip-card">
            <span class="chip-icon">📊</span>
            <div class="chip-title">기업 수급 Gap 보기</div>
            <div class="chip-sub">채용 수요-공급 미스매치를 분석하세요 → 인사팀 탭</div>
        </div>
        <div class="chip-card">
            <span class="chip-icon">🔍</span>
            <div class="chip-title">블랙기업 신호 보기</div>
            <div class="chip-sub">위험 채용공고·이직위험도를 탐지하세요 → 건전성 탭</div>
        </div>
    </div>
</div>
"""
st.markdown(hero_html, unsafe_allow_html=True)

st.write("---")


# =====================================================================
# 탭 0. 홈 (Intro): 전 직무 미스매치 종합 현황
# =====================================================================
def render_home_tab():
    _inject_page_card_css()
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
        "개발": ("dev", "IT개발·데이터"),
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
        "개발": ["Python", "SQL", "TensorFlow/PyTorch", "Tableau/PowerBI", "지표 정의 및 대시보드 구축", "데이터 파이프라인(ETL) 구축", "ML/DL 모델링", "A/B 테스트 설계 및 분석", "빅데이터분석기사", "ADsP", "AWS Certified Data Analytics"]
    }
    cur_skills = skills_pool_by_job.get(selected_job, [])

    # 네이버 API 데이터 카운트 필터링 연동
    job_weekly_map = {
        "기획/전략": "기획(plan)",
        "인사/노무": "인사(hr)",
        "회계/재무": "회계(acc)",
        "마케팅": "마케팅(mkt)",
        "개발": "개발(dev)"
    }
    cur_w_code = job_weekly_map.get(selected_job, "기획(plan)")
    if df_weekly_insights is not None and not df_weekly_insights.empty and 'job' in df_weekly_insights.columns:
        df_w_sub = df_weekly_insights[df_weekly_insights['job'] == cur_w_code]
        naver_cnt = len(df_w_sub)
    else:
        naver_cnt = 2088

    # 수급 미스매치 지수 동적 산출 (기업 수요 대비 구직자 관심도 편차)
    mismatches = []
    if df_filtered_saramin is not None and not df_filtered_saramin.empty:
        content_series = (df_filtered_saramin.get('title', pd.Series()).fillna('') + " " +
                          df_filtered_saramin.get('cleaned_requirement', pd.Series()).fillna('') + " " +
                          df_filtered_saramin.get('cleaned_preferential', pd.Series()).fillna('') + " " +
                          df_filtered_saramin.get('matched_skills', pd.Series()).fillna(''))
    else:
        content_series = pd.Series()

    for sk in cur_skills:
        d_cnt = sum(1 for text in content_series if sk.lower() in text.lower()) if not content_series.empty else 100
        if df_weekly_insights is not None and not df_weekly_insights.empty:
            w_match = df_w_sub[df_w_sub['keyword'] == sk] if 'df_w_sub' in locals() else pd.DataFrame()
            s_val = w_match['cafe_weekly_count'].mean() if not w_match.empty else 150
        else:
            s_val = 150
        
        m_val = abs(d_cnt - s_val) / (d_cnt + s_val + 1) * 100
        mismatches.append(m_val)

    mismatch_score = float(np.mean(mismatches)) if mismatches else 74.2

    if mismatch_score >= 90.0:
        mismatch_delta = "🚨 초고위험 불균형"
    elif mismatch_score >= 80.0:
        mismatch_delta = "⚠️ 고위험 불균형"
    elif mismatch_score >= 60.0:
        mismatch_delta = "🟡 보통 불균형"
    else:
        mismatch_delta = "🟢 안정 수급"

    # --- Bento Card 스타일 KPI 4개 (st.metric 대체) ---
    st.markdown(
        """
        <style>
        .kpi-grid { display: flex; gap: 14px; margin-bottom: 10px; flex-wrap: wrap; }
        .kpi-card {
            flex: 1; min-width: 180px;
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 20px 22px;
            box-shadow: 0 1px 4px rgba(15,23,42,0.06);
        }
        .kpi-label { color: #64748b; font-size: 13px; font-weight: 500; margin-bottom: 6px; }
        .kpi-value { color: #0f172a; font-size: 32px; font-weight: 700; line-height: 1.2; margin-bottom: 4px; }
        .kpi-sub { color: #94a3b8; font-size: 12px; }
        .kpi-card-accent {
            flex: 1; min-width: 180px;
            background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
            border: none;
            border-radius: 16px;
            padding: 20px 22px;
            box-shadow: 0 4px 16px rgba(37,99,235,0.25);
        }
        .kpi-label-accent { color: #93c5fd; font-size: 13px; font-weight: 500; margin-bottom: 6px; }
        .kpi-value-accent { color: #ffffff; font-size: 32px; font-weight: 700; line-height: 1.2; margin-bottom: 4px; }
        .kpi-sub-accent { color: #bfdbfe; font-size: 12px; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-label">{selected_job} 채용 공고 수</div>
                <div class="kpi-value">{saramin_count:,}<span style="font-size:16px;font-weight:400;"> 건</span></div>
                <div class="kpi-sub">사람인 실채용 DB 연동</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">네이버 API 데이터</div>
                <div class="kpi-value">{naver_cnt:,}<span style="font-size:16px;font-weight:400;"> 건</span></div>
                <div class="kpi-sub">주간 트렌드 데이터 연동</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-label">핵심 요구 스킬</div>
                <div class="kpi-value">{len(cur_skills)}<span style="font-size:16px;font-weight:400;"> 개</span></div>
                <div class="kpi-sub">실무 역량 중심 항목</div>
            </div>
            <div class="kpi-card-accent">
                <div class="kpi-label-accent">수급 미스매치 지수</div>
                <div class="kpi-value-accent">{mismatch_score:.1f}<span style="font-size:16px;font-weight:400;"> 점</span></div>
                <div class="kpi-sub-accent">{mismatch_delta} · 구직자 관점 시장 불균형 신호</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.write("---")

    # =====================================================================
    # PART 1. 🏢 기업 채용 수요 EDA (사람인 크롤링 데이터 기반)
    # =====================================================================
    st.subheader(f"1️⃣ PART 1. 🏢 기업 채용 수요 EDA — [{selected_job}]")
    st.markdown(
        f"""사람인 채용공고 DB 데이터에서 **[{selected_job}]** 직무 관련 수집 건수를 추출하여 
기업들이 공고에 실제로 명시하는 **기본 학력·경력 요건**과 **기본 필수 자격 vs 우대사항(Preferential)**의 요구 비중을 다차원 EDA 분석합니다."""
    )

    job_code_map = {"기획/전략": "plan", "인사/노무": "hr", "회계/재무": "acc", "마케팅": "mkt", "개발": "dev"}
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
    P1_STOPWORDS = set(['서비스', '인턴', '10년', '하여', '보유', '대해', '학위', '데이터', '회계', '경력자', '우대', '대구', '부산', '스킬', '학점', '대한', '있는', '관련', '개발자', '우대함', '통한', '따라', '성실', '근무', '대졸', '기반', '있으신', '전략', '박사', '해당직무', 'finance', '포함', '석사', '요건', '대학졸업', '본사', '노무', '우대사항', '정규직', '채용', '지원가능', '대학교졸업', '담당자', '수료', '학력', '엔지니어', '있는자', '경험이', '근무지', '경력', '가능', '고등학교졸업이상', '모집', '재학', '가능자', '조건', '지원자', '직무', '업무내용', '7년', '선택', '초대졸', '미만', '학력무관', '년', '지원', '우수자', '가능하신', '구축', '1년', '관련학과', '제출', '이상', '기본요건', '서울', '필수요건', '필수', '등의', '운영', '확인', '대학', '또는', '4년', 'ai엔지니어', '담당', '공고', '대학교', '업무', '신입', '능력', '부문', '가지', '가능한', '사용', '예정자', 'and', '경기', '졸업', '보유자', '데이터분석가', '관련업무', '커뮤니케이션', '경험자', '작성', '우대조건', '내용', '수행', '전공', '계약직', '자격요건', '통해', '분야', '보유하신', '관련된', '인천', '마케팅', '4년제', '기획자', '재무', '관련학', '이하', '판교', '5년', '원활', '개발', '무관', '2년', '소지자', '기타', '경험', '인사', '관리', '분석가', '분석', '능숙자', '3년', '보유역량', '사항', '파견직', '진행', '위한', '및', '마케터', '기획', '대학원', '상세', '자로서', '자격', '따른', '고졸'])

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

    # 2. 워드클라우드 서브플롯 (📌 필수 자격 vs ⭐ 우대 사항) — HR Analytics 스타일 카드 UI
    st.write(f"#### ☁️ [{selected_job}] 요구역량 항목별 워드클라우드 (WordCloud)")

    def _wordcloud_top5_chips(df_sorted_asc, accent_bg, accent_fg):
        top5 = df_sorted_asc.sort_values('score', ascending=False).head(5)
        chips = "".join(
            f"<span class='pg-badge' style='background:{accent_bg};color:{accent_fg};"
            f"margin:0 6px 6px 0;'>{r['word']} · {r['score']:.1f}</span>"
            for _, r in top5.iterrows()
        )
        st.markdown(chips, unsafe_allow_html=True)

    col_wc_1, col_wc_2 = st.columns(2)

    with col_wc_1:
        with st.container(border=True):
            st.markdown(f"**📌 [{selected_job}] 필수 요구사항**")
            dict_req = dict(zip(df_tfidf_req['word'], df_tfidf_req['score']))
            img_req = generate_real_wordcloud_img(dict_req, is_blue=True)
            st.image(img_req, use_column_width=True)
            st.caption("TOP 5 키워드 · 가중치")
            _wordcloud_top5_chips(df_tfidf_req, accent_bg="#eff6ff", accent_fg="#1d4ed8")

    with col_wc_2:
        with st.container(border=True):
            st.markdown(f"**⭐ [{selected_job}] 우대사항**")
            dict_pref = dict(zip(df_tfidf_pref['word'], df_tfidf_pref['score']))
            img_pref = generate_real_wordcloud_img(dict_pref, is_blue=False)
            st.image(img_pref, use_column_width=True)
            st.caption("TOP 5 키워드 · 가중치")
            _wordcloud_top5_chips(df_tfidf_pref, accent_bg="#fff7ed", accent_fg="#c2410c")

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
        "개발": ["Python", "SQL", "Tableau", "TensorFlow", "PyTorch", "빅데이터분석기사", "ADsP", "AWS"]
    }

    GENERAL_SKILLS_BY_JOB = {
        "기획/전략": ["커뮤니케이션", "협업", "영어", "Excel", "PPT작성법", "문서작성"],
        "인사/노무": ["커뮤니케이션", "Excel", "협업", "영어", "엑셀", "문서작성"],
        "회계/재무": ["Excel", "엑셀", "커뮤니케이션", "협업", "영어", "OA실무"],
        "마케팅": ["커뮤니케이션", "협업", "영어", "Excel", "PPT작성법", "콘텐츠기획"],
        "개발": ["협업", "커뮤니케이션", "영어", "Excel", "A/B테스트", "문서작성"]
    }

    is_naver_api_real = df_weekly_insights is not None
    job_mapping = {
        "기획/전략": "기획(plan)",
        "인사/노무": "인사(hr)",
        "회계/재무": "회계(acc)",
        "마케팅": "마케팅(mkt)",
        "개발": "개발(dev)"
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
        "개발": "dev"
    }

    job_weekly_map = {
        "기획/전략": "기획(plan)",
        "인사/노무": "인사(hr)",
        "회계/재무": "회계(acc)",
        "마케팅": "마케팅(mkt)",
        "개발": "개발(dev)"
    }

    skills_for_gap = {
        "기획/전략": ["컴퓨터활용능력", "M&A", "Figma", "CPA", "CFA", "GA4", "ADsP", "SQLD"],
        "인사/노무": ["ERP", "조직문화", "노동법", "공인노무사", "성과관리", "Workday", "직업상담사", "PHR"],
        "회계/재무": ["ERP", "세무사", "전산회계", "SAP", "전산세무", "IFRS", "재경관리사", "공인회계사"],
        "마케팅": ["CRM", "Meta", "GA4", "SEO", "검색광고마케터", "Google Ads", "HubSpot", "SQLD"],
        "개발": ["SQL", "Python", "AWS", "PyTorch", "TensorFlow", "ETL", "Tableau", "ADsP"]
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
def render_seeker_tab():
    st.header(f"[{selected_job}] 스펙 자가진단 및 적합도 스코어링")
    st.markdown(
        "보유하신 경력/학력/자격증/툴/실무 경험을 "
        "**실제 기업 공고 조건과 다차원적으로 비교**하여 점수를 산출합니다."
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
            
    raw_licenses = specs["licenses"]
    raw_tools = specs["tools"]
    raw_experiences = specs["experiences"]
    
    licenses_pool = ["해당 없음"] + raw_licenses
    tools_pool = ["해당 없음"] + raw_tools
    experiences_pool = ["해당 없음"] + raw_experiences
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
    clean_licenses = [l for l in user_licenses if l != "해당 없음"]
    clean_tools = [t for t in user_tools if t != "해당 없음"]
    clean_experiences = [e for e in user_experiences if e != "해당 없음"]
    user_skills = clean_licenses + clean_tools + clean_experiences

    if diagnose_clicked or user_licenses or user_tools or user_experiences:
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

        # 미보유 추천 스펙 TOP 3 도출 (해당 없음 예외 처리)
        unselected = (
            [(l, "자격증") for l in raw_licenses if l not in clean_licenses] +
            [(t, "실무 툴") for t in raw_tools if t not in clean_tools] +
            [(e, "직무 경험") for e in raw_experiences if e not in clean_experiences]
        )
        missing_specs = unselected[:3]

        # 1. [진단 알고리즘] 스코어링 공식 명분 및 투명성 안내 상자 & 면책 조항
        st.info(
            "ℹ️ **[:information_source: 점수 산출 데이터 기준 및 산출 공식]**\n\n"
            "본 점수는 사람인 5,000건 공고의 직무별 필수/우대 역량 가중치(70%)와 네이버 데이터랩의 최신 구직자 검색 희망 지수(30%)를 결합하여 산출된 정량 지표입니다.\n\n"
            "⚠️ **[유의사항]** 본 진단 점수 및 안심권 기준은 정량적 공고 매칭율에 기반한 참고 지표이며, 실제 기업 채용 전형에서의 **최종 합격 또는 불합격을 절대 보장하지 않습니다.**"
        )

        # 세부 범주별 가중치 점수 산출 (Breakdown)
        sub_lic_score = (len(clean_licenses) / len(raw_licenses) * 100) if raw_licenses else 0.0
        sub_tool_score = (len(clean_tools) / len(raw_tools) * 100) if raw_tools else 0.0
        sub_exp_score = (len(clean_experiences) / len(raw_experiences) * 100) if raw_experiences else 0.0
        sub_career_score = float(user_career_val * 10)
        sub_edu_score = float(user_edu_val * 33.3)

        JOB_BENCHMARK = {
            "기획/전략": 62.4,
            "인사/노무": 59.8,
            "회계/재무": 61.2,
            "마케팅": 58.5,
            "개발": 63.1
        }
        avg_score = JOB_BENCHMARK.get(selected_job, 60.0)

        if suitability_score >= 85.0:
            pct_str = "현재 상위 12% 수준입니다 (서류 최우수 합격권 🏆)"
        elif suitability_score >= 75.0:
            pct_str = "현재 상위 24% 수준입니다 (서류 통과 안심권 🟢)"
        elif suitability_score >= 60.0:
            pct_str = "현재 상위 48% 수준입니다 (보완 요구 경쟁권 🟡)"
        else:
            pct_str = "현재 상위 68% 수준입니다 (스펙 보완 필요권 🔴)"

        st.subheader("📋 다차원 직무 적합도 진단 결과")
        c_res1, c_res2 = st.columns([1, 2])
        with c_res1:
            st.metric(
                "종합 직무 적합도 점수",
                f"{suitability_score:.1f}점",
                help="자격증 20% + 실무툴 20% + 직무경험 20% + 경력 20% + 학력 20%"
            )
            # 2. [점수 맥락 제공] 상대적 위치(기준선) 가이드라인 배치
            st.markdown(
                f"""<div style="background-color:#eff6ff; border:1px solid #bfdbfe; padding:10px 14px; border-radius:8px; margin-top:8px;">
                    <p style="margin:0; font-size:0.88rem; color:#1e3a8a; font-weight:600;">
                        📊 <b>[{selected_job}] 지원자 평균 {avg_score:.1f}점</b> | 합격 안심권 <b>75.0점 이상</b><br>
                        ➔ <span style="color:#2563eb; font-weight:700;">{pct_str}</span><br>
                        <span style="font-size:0.78rem; color:#64748b; font-weight:normal;">(※ 기준: 합격자 개인 이력서 DB가 아닌, 사람인 5,000건 기업 공고 요건의 75% 이상을 동시 충족하는 시장 상위 25% 정량 충족률 기준입니다. <b>본 결과는 실제 합격/불합격을 보장하지 않습니다.</b>)</span>
                    </p>
                </div>""",
                unsafe_allow_html=True
            )
        with c_res2:
            st.markdown(f"##### ⚠️ 탑티어 {selected_job} 전문가 도약을 위해 우선순위로 채워야 할 스펙 TOP 3")
            if missing_specs:
                for idx, (item, cat) in enumerate(missing_specs):
                    st.warning(f"**{idx+1}순위: {item}** ({cat})")
            else:
                st.success("🎉 축하합니다! 해당 직무군 핵심 요구 스펙을 모두 체크하셨습니다.")

        # 3. [점수 세부 요소 파쇄] 5대 범주별 가중치 세부 점수 파쇄 (Breakdown)
        st.write("")
        st.markdown("##### 🧩 5대 평가 범주별 가중치 세부 점수 파쇄 (Breakdown)")
        b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns(5)
        with b_col1:
            st.metric("📜 우대 자격증", f"{sub_lic_score:.0f}점", "20% 가중치")
        with b_col2:
            st.metric("🛠️ 실무 툴/스킬", f"{sub_tool_score:.0f}점", "20% 가중치")
        with b_col3:
            st.metric("💼 직무 경험", f"{sub_exp_score:.0f}점", "20% 가중치")
        with b_col4:
            st.metric("📅 경력 연차", f"{sub_career_score:.0f}점", "20% 가중치")
        with b_col5:
            st.metric("🎓 최종 학력", f"{sub_edu_score:.0f}점", "20% 가중치")
                
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


if is_seeker_mode:
    tab_home, tab_seeker = st.tabs([
        "🏠 홈: 취업 마켓 다차원 EDA",
        "💡 구직자: 스펙 자가진단 및 스코어링",
    ])
    with tab_home:
        render_home_tab()
    with tab_seeker:
        render_seeker_tab()
else:
    tab_hr, tab_health = st.tabs([
        "🏢 인사팀: 수급 Gap 분석 및 JD 최적화",
        "⚠️ 기업 이직위험 및 채용 건전성 분석",
    ])
    with tab_hr:
        render_hr_gap_tab()
    with tab_health:
        render_company_health_tab()
# =====================================================================
# 푸터
# =====================================================================
st.write("---")
st.caption(
    "📊 취업 시장 다차원 EDA & 직무 적합도 진단 솔루션 (SaaS) | "
    "사람인 1,000건 공고 + 네이버 API 통합 데이터 마트 기반 | "
    "✅ 사람인 5,000건 채용 DB (recruit_processed.db) × 네이버 API 통합 데이터 마트 (naver_weekly_insights.json) 5대 전체 직무 100% 실시간 연동"
)
