"""
5개 직무(기획/전략, 인사/노무, 회계/재무, 마케팅, 데이터분석가/AI엔지니어) 수급 Gap 분석용
네이버 데이터 테스트 수집 스크립트.

범위: 직무당 사람인 실채용공고 수요 상위 역량 5개 (총 25개)만 테스트 수집한다. 전체 수집 아님.

절대 규칙:
- 기존 파일을 덮어쓰지 않는다 (신규 파일만 생성).
- API 호출이 실패하거나 키가 없어도 mock/임의 값으로 대체하지 않고 실패로 기록한다.
- API 키를 로그/출력에 남기지 않는다.
- 대시보드/임베딩 코드는 건드리지 않는다 (이 스크립트는 순수 데이터 수집 전용).
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
OUT_DIR = os.path.join(PROJECT_ROOT, "data", "naver_api")
QUERY_MAP_PATH = os.path.join(OUT_DIR, "expanded_skill_query_map_test.csv")
RESULTS_PATH = os.path.join(OUT_DIR, "naver_skill_test_results.csv")

for target_path in (QUERY_MAP_PATH, RESULTS_PATH):
    if os.path.exists(target_path):
        print(f"[중단] 기존 파일을 덮어쓸 수 없습니다: {target_path}", file=sys.stderr)
        sys.exit(1)

# ---------------------------------------------------------------------------
# 1. 사람인 수요 역량 선정 설정
# ---------------------------------------------------------------------------
SARAMIN_JOB_MAP = {
    "기획/전략": "영업·사업개발",
    "인사/노무": "인사·HR·총무",
    "회계/재무": "회계·재무·경영관리",
    "마케팅": "마케팅·CRM",
    "데이터분석가/AI엔지니어": "IT개발·데이터",
}

# 대소문자/한영 표기 차이만 있는 동의어를 표준 표기로 정규화
CANONICAL_ALIASES = {
    "excel": "Excel", "엑셀": "Excel",
    "ppt": "PPT",
    "sql": "SQL",
    "python": "Python",
    "tableau": "Tableau",
    "hr": "인사(HR)",
}

# 직무 전반에 공통으로 등장하는 범용 단어 + Next/Boot/API/Code처럼 맥락 없이는 의미가 불분명한
# 단독 토큰(기술 파편어)을 대표 역량 후보에서 제외한다.
VAGUE_TOKENS = {
    "채용", "계약", "협업", "커뮤니케이션", "문서화", "보고서작성", "설계", "개발", "영업", "사무",
    "office", "데이터", "ai", "기획", "전략", "재무", "회계", "인사", "노무", "마케팅",
    "고객관리", "법률/법무", "리스크관리", "예산", "급여", "총무", "영어", "일본어", "중국어",
    "api", "next", "boot", "code", "md",
}

TOP_N_PER_JOB = 5


def select_top_skills():
    """recruit_processed.db에서 직무별 수요 상위 5개 역량을 선정한다."""
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
        top5 = counter.most_common(TOP_N_PER_JOB)
        selection[job] = [{"canonical_skill": k, "demand_count": v} for k, v in top5]
    return selection


# ---------------------------------------------------------------------------
# 2. 검색어 사전 생성
# ---------------------------------------------------------------------------
QUERY_TEMPLATES = [
    ("취업", "{skill} 취업"),
    ("채용", "{skill} 채용"),
    ("신입", "{skill} 신입"),
    ("학습", "{skill} 공부"),
]

JOB_INTENT_WORDS = ["취업", "채용", "신입", "이직", "면접", "스펙", "자격증", "공부", "준비", "포트폴리오"]


def build_query_map(selection):
    rows = []
    for job, skills in selection.items():
        for item in skills:
            skill = item["canonical_skill"]
            demand_count = item["demand_count"]
            for query_type, template in QUERY_TEMPLATES:
                rows.append({
                    "job_role": job,
                    "canonical_skill": skill,
                    "query": template.format(skill=skill),
                    "query_type": query_type,
                    "demand_count": demand_count,
                })
    return rows


def save_query_map(rows):
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(QUERY_MAP_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["job_role", "canonical_skill", "query", "query_type", "demand_count"])
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# 3. 네이버 데이터랩 수집 (직무별 대표 역량 단위로 keywordGroup 1개)
# ---------------------------------------------------------------------------
TODAY = datetime.now()
YESTERDAY = TODAY - timedelta(days=1)
START_DATE = "2026-01-01"
END_DATE = YESTERDAY.strftime("%Y-%m-%d")

DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"


def fetch_datalab_trend(client_id, client_secret, group_name, keywords):
    """반환: (mean_ratio 또는 None, latest_ratio 또는 None, 상태 문자열)"""
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
        if not data:
            return None, None, "EMPTY_RESULT"
        ratios = [row["ratio"] for row in data]
        data_sorted = sorted(data, key=lambda r: r["period"])
        mean_ratio = sum(ratios) / len(ratios)
        latest_ratio = data_sorted[-1]["ratio"]
        return mean_ratio, latest_ratio, "OK"
    except urllib.error.HTTPError as e:
        return None, None, f"HTTP_{e.code}"
    except Exception as e:
        return None, None, f"ERROR_{type(e).__name__}"


# ---------------------------------------------------------------------------
# 4. 검색 API 보조 수집 (블로그/카페/지식iN, 쿼리 단위)
# ---------------------------------------------------------------------------
SEARCH_APIS = [
    ("blog", "https://openapi.naver.com/v1/search/blog.json"),
    ("cafe", "https://openapi.naver.com/v1/search/cafearticle.json"),
    ("kin", "https://openapi.naver.com/v1/search/kin.json"),
]
SEARCH_DISPLAY = 20


def fetch_search_api(client_id, client_secret, endpoint, query):
    params = {"query": query, "display": SEARCH_DISPLAY, "start": 1, "sort": "sim"}
    url = f"{endpoint}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url)
    req.add_header("X-Naver-Client-Id", client_id)
    req.add_header("X-Naver-Client-Secret", client_secret)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("total"), result.get("items", []), "OK"
    except urllib.error.HTTPError as e:
        return None, [], f"HTTP_{e.code}"
    except Exception as e:
        return None, [], f"ERROR_{type(e).__name__}"


def has_job_intent(title, description):
    text = (title or "") + (description or "")
    return any(w in text for w in JOB_INTENT_WORDS)


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

    print("[1단계] 사람인 수요 역량 선정 중...")
    selection = select_top_skills()
    for job, skills in selection.items():
        print(f"  - {job}: " + ", ".join(f"{s['canonical_skill']}({s['demand_count']})" for s in skills))

    print("\n[2단계] 검색어 사전 생성 및 저장...")
    query_rows = build_query_map(selection)
    save_query_map(query_rows)
    print(f"  -> {QUERY_MAP_PATH} ({len(query_rows)}행)")

    print("\n[3단계] 네이버 데이터랩 주간 트렌드 수집 (대표 역량 25개, 1콜/역량)...")
    datalab_results = {}  # (job, skill) -> (mean, latest, status)
    idx = 0
    total_skills = sum(len(v) for v in selection.values())
    for job, skills in selection.items():
        for item in skills:
            idx += 1
            skill = item["canonical_skill"]
            queries = [row["query"] for row in query_rows if row["job_role"] == job and row["canonical_skill"] == skill]
            print(f"  [{idx}/{total_skills}] {job} / {skill} keywordGroup={queries}", end=" ", flush=True)
            mean_r, latest_r, status = fetch_datalab_trend(client_id, client_secret, skill, queries)
            datalab_results[(job, skill)] = (mean_r, latest_r, status)
            print(f"-> {status} (mean={mean_r}, latest={latest_r})")
            time.sleep(0.5)

    print("\n[4단계] 검색 API(블로그/카페/지식iN) 보조 수집 (쿼리 단위)...")
    # (job, skill) -> {"blog":n, "cafe":n, "kin":n, "raw_total":sum, "links":set(), "call_status":[...]}
    search_agg = {}
    for job, skills in selection.items():
        for item in skills:
            search_agg[(job, item["canonical_skill"])] = {
                "blog": 0, "cafe": 0, "kin": 0, "raw_total": 0, "links": set(), "statuses": []
            }

    total_calls = len(query_rows) * len(SEARCH_APIS)
    call_i = 0
    for row in query_rows:
        key = (row["job_role"], row["canonical_skill"])
        for source, endpoint in SEARCH_APIS:
            call_i += 1
            total, items, status = fetch_search_api(client_id, client_secret, endpoint, row["query"])
            print(f"  [{call_i}/{total_calls}] [{source}] '{row['query']}' -> {status}"
                  + (f", total={total}, items={len(items)}" if status == "OK" else ""))
            search_agg[key]["statuses"].append(status)
            if status == "OK":
                if total is not None:
                    search_agg[key]["raw_total"] += total
                intent_count = 0
                for it in items:
                    link = it.get("link", "")
                    if link:
                        search_agg[key]["links"].add(link)
                    if has_job_intent(it.get("title", ""), it.get("description", "")):
                        intent_count += 1
                search_agg[key][source] += intent_count
            time.sleep(0.3)

    print("\n[5단계] 결과 집계 및 저장...")
    result_rows = []
    for job, skills in selection.items():
        for item in skills:
            skill = item["canonical_skill"]
            key = (job, skill)
            mean_r, latest_r, dl_status = datalab_results[key]
            agg = search_agg[key]

            flags = []
            if dl_status != "OK":
                flags.append(f"TREND_{dl_status}")
            fail_statuses = [s for s in agg["statuses"] if s != "OK"]
            if fail_statuses:
                flags.append(f"SEARCH_PARTIAL_FAIL({len(fail_statuses)}/{len(agg['statuses'])})")
            job_intent_total = agg["blog"] + agg["cafe"] + agg["kin"]
            if job_intent_total == 0:
                flags.append("NO_JOB_INTENT_DOCS")
            if not flags:
                flags.append("OK")

            result_rows.append({
                "job_role": job,
                "canonical_skill": skill,
                "demand_count": item["demand_count"],
                "trend_ratio_mean": "" if mean_r is None else round(mean_r, 4),
                "trend_ratio_latest": "" if latest_r is None else latest_r,
                "blog_job_intent_count": agg["blog"],
                "cafe_job_intent_count": agg["cafe"],
                "kin_job_intent_count": agg["kin"],
                "unique_document_count": len(agg["links"]),
                "raw_total_search_results": agg["raw_total"],
                "data_quality_flag": ";".join(flags),
            })

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8-sig") as f:
        fieldnames = ["job_role", "canonical_skill", "demand_count", "trend_ratio_mean", "trend_ratio_latest",
                      "blog_job_intent_count", "cafe_job_intent_count", "kin_job_intent_count",
                      "unique_document_count", "raw_total_search_results", "data_quality_flag"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result_rows)
    print(f"  -> {RESULTS_PATH} ({len(result_rows)}행)")

    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
