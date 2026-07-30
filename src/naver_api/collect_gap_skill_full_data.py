"""
5개 직무(기획/전략, 인사/노무, 회계/재무, 마케팅, 개발) 수급 Gap 분석용
네이버 데이터 전체 수집 스크립트 (직무별 사람인 수요 상위 20개 역량, 총 최대 100개 (직무,역량) 쌍).

테스트 수집(collect_gap_skill_test_data.py) 결과를 반영한 수정 사항:
1. 데이터랩: canonical_skill 단독 검색을 기본(trend_ratio_base)으로 사용.
   역량명+취업/채용/신입 조합은 보조값(trend_ratio_job_intent)으로 별도 저장.
   null은 0으로 채우지 않는다. 모호한 단어(BI, ml, 리스크, 자금, 결산)만 직무 문맥을 붙여 검색한다.
2. 검색 API: blog/cafe/kin 수집 건수와 unique_document_count만 보조 지표로 저장한다.
   '구직 의도 비율'이나 API의 total(raw_total_search_results)은 더 이상 사용하지 않는다.
   쿼리 자체에 취업/채용 단어를 넣어 문서를 '구직 의도 문서'로 판정하지 않는다(테스트에서 근거 없음 확인).

절대 규칙:
- 기존 테스트 산출물(expanded_skill_query_map_test.csv, naver_skill_test_results.csv)은 건드리지 않는다.
- API 실패/키 없음을 mock/임의 값으로 채우지 않는다.
- API 키를 로그에 출력하지 않는다.
- 대시보드/임베딩 코드는 수정하지 않는다.
"""
import csv
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 경로 설정
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(PROJECT_ROOT, "data", "naver_api", "it_data", ".env")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "recruit_processed.db")
OUT_DIR = os.path.join(PROJECT_ROOT, "data", "integrated")
CSV_PATH = os.path.join(OUT_DIR, "naver_skill_weekly_insights.csv")
JSON_PATH = os.path.join(OUT_DIR, "naver_skill_weekly_insights.json")

# 기존 테스트 산출물 경로 (건드리지 않음 - 존재 여부만 확인용)
TEST_QUERY_MAP_PATH = os.path.join(PROJECT_ROOT, "data", "naver_api", "expanded_skill_query_map_test.csv")
TEST_RESULTS_PATH = os.path.join(PROJECT_ROOT, "data", "naver_api", "naver_skill_test_results.csv")

for target_path in (CSV_PATH, JSON_PATH):
    if os.path.exists(target_path):
        print(f"[중단] 기존 파일을 덮어쓸 수 없습니다: {target_path}", file=sys.stderr)
        sys.exit(1)

# ---------------------------------------------------------------------------
# 1. 사람인 수요 역량 선정 (직무별 상위 20개)
# ---------------------------------------------------------------------------
SARAMIN_JOB_MAP = {
    "기획/전략": "영업·사업개발",
    "인사/노무": "인사·HR·총무",
    "회계/재무": "회계·재무·경영관리",
    "마케팅": "마케팅·CRM",
    "개발": "IT개발·데이터",
}

CANONICAL_ALIASES = {
    "excel": "Excel", "엑셀": "Excel",
    "ppt": "PPT",
    "sql": "SQL",
    "python": "Python",
    "tableau": "Tableau",
    "hr": "인사(HR)",
}

VAGUE_TOKENS = {
    "채용", "계약", "협업", "커뮤니케이션", "문서화", "보고서작성", "설계", "개발", "영업", "사무",
    "office", "데이터", "ai", "기획", "전략", "재무", "회계", "인사", "노무", "마케팅",
    "고객관리", "법률/법무", "리스크관리", "예산", "급여", "총무", "영어", "일본어", "중국어",
    "api", "next", "boot", "code", "md",
}

TOP_N_PER_JOB = 20

# 단독으로는 뜻이 여러 갈래로 갈리는 토큰 (경쟁 의미가 뚜렷해 bare 검색 시 신호가 오염될 위험이 큰 경우만 선정).
# 예) BI: 비즈니스 인텔리전스 vs 브랜드 아이덴티티(CI/BI), ml: 머신러닝 vs 부피 단위 밀리리터,
#     리스크/자금/결산: 채용 맥락 밖에서도 매우 흔히 쓰이는 일반 시사/경제 단어라 직무 신호가 희석됨.
AMBIGUOUS_TOKENS = {"BI", "ml", "ML", "리스크", "자금", "결산"}

JOB_CONTEXT_WORD = {
    "기획/전략": "기획",
    "인사/노무": "인사",
    "회계/재무": "회계",
    "마케팅": "마케팅",
    "개발": "데이터",
}


def select_top_skills():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM recruit_skill_flags", conn)
    conn.close()

    selection = {}
    for job, job_group in SARAMIN_JOB_MAP.items():
        sub = df[df["job_group"] == job_group]
        counter = Counter()
        for col in ["preferred_certificates", "required_keywords", "preferred_keywords", "matched_skills"]:
            for val in sub[col].dropna():
                for tok in str(val).split(","):
                    tok = tok.strip()
                    if not tok:
                        continue
                    canon = CANONICAL_ALIASES.get(tok.lower(), tok)
                    if canon.lower() in VAGUE_TOKENS:
                        continue
                    counter[canon] += 1
        top_n = counter.most_common(TOP_N_PER_JOB)
        selection[job] = [{"canonical_skill": k, "demand_count": v} for k, v in top_n]
    return selection


def search_term_for(job, skill):
    """모호한 토큰만 직무 문맥을 붙인 검색어를 반환한다."""
    if skill in AMBIGUOUS_TOKENS:
        return f"{JOB_CONTEXT_WORD[job]} {skill}"
    return skill


# ---------------------------------------------------------------------------
# 3. 네이버 데이터랩 수집
# ---------------------------------------------------------------------------
TODAY = datetime.now()
YESTERDAY = TODAY - timedelta(days=1)
START_DATE = "2026-01-01"
END_DATE = YESTERDAY.strftime("%Y-%m-%d")
DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"

_datalab_cache = {}  # tuple(sorted(keywords)) -> {period: ratio} or None


def fetch_datalab_series(client_id, client_secret, group_name, keywords):
    cache_key = (group_name, tuple(keywords))
    if cache_key in _datalab_cache:
        return _datalab_cache[cache_key]

    payload = {
        "startDate": START_DATE,
        "endDate": END_DATE,
        "timeUnit": "week",
        "keywordGroups": [{"groupName": group_name, "keywords": keywords[:5]}],
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(DATALAB_URL, data=body)
    req.add_header("X-Naver-Client-Id", client_id)
    req.add_header("X-Naver-Client-Secret", client_secret)
    req.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        data = result.get("results", [{}])[0].get("data", [])
        series = {row["period"]: row["ratio"] for row in data}
        status = "OK" if series else "EMPTY_RESULT"
        _datalab_cache[cache_key] = (series, status)
    except urllib.error.HTTPError as e:
        _datalab_cache[cache_key] = ({}, f"HTTP_{e.code}")
    except Exception as e:
        _datalab_cache[cache_key] = ({}, f"ERROR_{type(e).__name__}")
    time.sleep(0.4)
    return _datalab_cache[cache_key]


# ---------------------------------------------------------------------------
# 4. 검색 API 보조 수집 (blog/cafe/kin, 스킬(문맥 보정) 단일 쿼리)
# ---------------------------------------------------------------------------
SEARCH_APIS = [
    ("blog", "https://openapi.naver.com/v1/search/blog.json"),
    ("cafe", "https://openapi.naver.com/v1/search/cafearticle.json"),
    ("kin", "https://openapi.naver.com/v1/search/kin.json"),
]
SEARCH_DISPLAY = 20

_search_cache = {}  # (source, query) -> (items, status)


def fetch_search_api(client_id, client_secret, source, endpoint, query):
    cache_key = (source, query)
    if cache_key in _search_cache:
        return _search_cache[cache_key]
    params = {"query": query, "display": SEARCH_DISPLAY, "start": 1, "sort": "sim"}
    url = f"{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", client_id)
    req.add_header("X-Naver-Client-Secret", client_secret)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        items = result.get("items", [])
        _search_cache[cache_key] = (items, "OK")
    except urllib.error.HTTPError as e:
        _search_cache[cache_key] = ([], f"HTTP_{e.code}")
    except Exception as e:
        _search_cache[cache_key] = ([], f"ERROR_{type(e).__name__}")
    time.sleep(0.3)
    return _search_cache[cache_key]


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------
def main():
    load_dotenv(ENV_PATH)
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("[중단] NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 을 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    print("[0단계] 기존 테스트 산출물 보존 확인...")
    for p in (TEST_QUERY_MAP_PATH, TEST_RESULTS_PATH):
        print(f"  - {'존재(유지)' if os.path.exists(p) else '없음'}: {p}")

    print("\n[1단계] 사람인 수요 역량 선정 (직무별 상위 20개)...")
    selection = select_top_skills()
    total_pairs = sum(len(v) for v in selection.values())
    unique_skills = {item["canonical_skill"] for skills in selection.values() for item in skills}
    print(f"  총 (직무,역량) 쌍: {total_pairs}, 고유 역량 수: {len(unique_skills)}")
    for job, skills in selection.items():
        amb = [s["canonical_skill"] for s in skills if s["canonical_skill"] in AMBIGUOUS_TOKENS]
        print(f"  - {job}: {len(skills)}개 선정" + (f" (모호 토큰: {amb})" if amb else ""))

    rows = []
    pair_idx = 0
    for job, skills in selection.items():
        for item in skills:
            pair_idx += 1
            skill = item["canonical_skill"]
            demand_count = item["demand_count"]
            term = search_term_for(job, skill)
            is_ambiguous = skill in AMBIGUOUS_TOKENS

            print(f"\n[{pair_idx}/{total_pairs}] {job} / {skill}"
                  + (f" (모호->문맥검색어 '{term}')" if is_ambiguous else ""))

            # --- 데이터랩: 기본(단독) ---
            base_series, base_status = fetch_datalab_series(client_id, client_secret, f"base:{term}", [term])
            print(f"  데이터랩(기본, '{term}') -> {base_status}, {len(base_series)}주")

            # --- 데이터랩: 보조(구직 의도 조합) ---
            intent_keywords = [f"{term} 취업", f"{term} 채용", f"{term} 신입"]
            intent_series, intent_status = fetch_datalab_series(client_id, client_secret, f"intent:{term}", intent_keywords)
            print(f"  데이터랩(의도조합) -> {intent_status}, {len(intent_series)}주")

            # --- 검색 API 보조 수집 (문맥 보정된 term 그대로, 취업/채용 단어 추가 없이) ---
            source_counts = {}
            source_links = set()
            search_statuses = []
            for source, endpoint in SEARCH_APIS:
                items, status = fetch_search_api(client_id, client_secret, source, endpoint, term)
                search_statuses.append(status)
                source_counts[source] = len(items) if status == "OK" else 0
                if status == "OK":
                    for it in items:
                        link = it.get("link", "")
                        if link:
                            source_links.add(link)
            print(f"  검색API -> blog={source_counts['blog']}, cafe={source_counts['cafe']}, "
                  f"kin={source_counts['kin']}, unique_doc={len(source_links)}")

            # --- 데이터 품질 플래그 ---
            flags = []
            if base_status != "OK":
                flags.append(f"BASE_{base_status}")
            if intent_status != "OK":
                flags.append(f"INTENT_{intent_status}")
            search_fail = [s for s in search_statuses if s != "OK"]
            if search_fail:
                flags.append(f"SEARCH_FAIL({len(search_fail)}/3)")
            if is_ambiguous:
                flags.append("AMBIGUOUS_CONTEXT_APPLIED")
            if not flags:
                flags.append("OK")
            flag_str = ";".join(flags)

            weeks_observed = len(base_series)

            # --- 주간 행 생성 (기본 시리즈의 날짜를 기준으로 outer 병합) ---
            all_dates = sorted(set(base_series.keys()) | set(intent_series.keys()))
            if not all_dates:
                # 데이터랩 결과가 전무한 경우에도 (직무,역량) 존재는 남긴다 (date 공란)
                rows.append({
                    "date": "",
                    "job_role": job,
                    "canonical_skill": skill,
                    "demand_count": demand_count,
                    "trend_ratio_base": "",
                    "trend_ratio_job_intent": "",
                    "blog_collected_count": source_counts["blog"],
                    "cafe_collected_count": source_counts["cafe"],
                    "kin_collected_count": source_counts["kin"],
                    "unique_document_count": len(source_links),
                    "weeks_observed": weeks_observed,
                    "data_quality_flag": flag_str,
                })
            else:
                for d in all_dates:
                    rows.append({
                        "date": d,
                        "job_role": job,
                        "canonical_skill": skill,
                        "demand_count": demand_count,
                        "trend_ratio_base": base_series.get(d, ""),
                        "trend_ratio_job_intent": intent_series.get(d, ""),
                        "blog_collected_count": source_counts["blog"],
                        "cafe_collected_count": source_counts["cafe"],
                        "kin_collected_count": source_counts["kin"],
                        "unique_document_count": len(source_links),
                        "weeks_observed": weeks_observed,
                        "data_quality_flag": flag_str,
                    })

    print("\n[5단계] 결과 저장...")
    os.makedirs(OUT_DIR, exist_ok=True)
    fieldnames = ["date", "job_role", "canonical_skill", "demand_count",
                  "trend_ratio_base", "trend_ratio_job_intent",
                  "blog_collected_count", "cafe_collected_count", "kin_collected_count",
                  "unique_document_count", "weeks_observed", "data_quality_flag"]

    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  -> {CSV_PATH} ({len(rows)}행)")

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f"  -> {JSON_PATH} ({len(rows)}행)")

    print("\n=== 완료 ===")
    print(f"데이터랩 API 고유 호출: {len(_datalab_cache)}건 (캐시로 중복 스킬 재사용)")
    print(f"검색 API 고유 호출: {len(_search_cache)}건 (캐시로 중복 스킬 재사용)")


if __name__ == "__main__":
    main()
