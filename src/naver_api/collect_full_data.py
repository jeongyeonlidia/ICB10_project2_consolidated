"""
IT개발·데이터 직무 네이버 API 전체 수집 스크립트.

data/naver_api/it_data/search_queries/dev_keywords_master.json 의
31개 representative_keyword × (블로그/카페글/지식iN) 을
키워드·source별 최대 100건, pagination(display<=100, start<=1000)을 적용해 수집하고
raw/ 에 원본 그대로(중복 제거·필터링 없이) 저장한다.
"""
import csv
import json
import os
import sys
import time

import requests
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(PROJECT_ROOT, "data", "naver_api", "it_data", ".env")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "naver_api", "it_data", "raw")
MASTER_PATH = os.path.join(PROJECT_ROOT, "data", "naver_api", "it_data", "search_queries", "dev_keywords_master.json")

APIS = [
    {"source": "blog", "endpoint": "https://openapi.naver.com/v1/search/blog.json", "date_field": "postdate", "out_file": "blog_raw.csv"},
    {"source": "cafe", "endpoint": "https://openapi.naver.com/v1/search/cafearticle.json", "date_field": None, "out_file": "cafe_raw.csv"},
    {"source": "kin", "endpoint": "https://openapi.naver.com/v1/search/kin.json", "date_field": None, "out_file": "kin_raw.csv"},
]

TARGET_PER_COMBO = 100
PAGE_SIZE = 100
MAX_START = 1000  # 네이버 검색 API 상한
REQUEST_INTERVAL_SEC = 0.15
MAX_RETRIES = 3
FIELDNAMES = [
    "representative_keyword", "search_query", "source",
    "title", "description", "link", "date", "total_search_results",
]


def load_keywords():
    with open(MASTER_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [g["representative_keyword"] for g in data["skills"] + data["certifications"]]


def call_with_retry(endpoint, params, headers):
    """429/5xx에 대해 지수 백오프 재시도. 그 외 오류는 즉시 반환."""
    delay = 1.0
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
        except requests.RequestException as e:
            if attempt == MAX_RETRIES - 1:
                return None, str(e)
            time.sleep(delay)
            delay *= 2
            continue

        if resp.status_code == 200:
            return resp, None
        if resp.status_code == 429 or resp.status_code >= 500:
            if attempt < MAX_RETRIES - 1:
                time.sleep(delay)
                delay *= 2
                continue
        return resp, None
    return None, "재시도 초과"


def collect_for_combo(endpoint, keyword, headers, call_log):
    """키워드 하나 × source 하나에 대해 최대 TARGET_PER_COMBO건을 pagination으로 수집."""
    collected = []
    total_search_results = None
    start = 1

    while len(collected) < TARGET_PER_COMBO and start <= MAX_START:
        display = min(PAGE_SIZE, TARGET_PER_COMBO - len(collected))
        params = {"query": keyword, "display": display, "start": start, "sort": "sim"}

        resp, err = call_with_retry(endpoint, params, headers)
        call_log["calls"] += 1

        if resp is None:
            call_log["errors"].append({"keyword": keyword, "start": start, "error": err})
            break

        if resp.status_code != 200:
            try:
                msg = resp.json().get("errorMessage", resp.text[:200])
            except Exception:
                msg = resp.text[:200]
            call_log["errors"].append({"keyword": keyword, "start": start, "error": f"HTTP {resp.status_code}: {msg}"})
            break

        body = resp.json()
        if total_search_results is None:
            total_search_results = body.get("total", 0)

        items = body.get("items", [])
        if not items:
            break

        collected.extend(items)

        if len(items) < display:
            break
        start += display
        time.sleep(REQUEST_INTERVAL_SEC)

    return collected, total_search_results


def main():
    load_dotenv(ENV_PATH)
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    headers = {"X-Naver-Client-Id": client_id, "X-Naver-Client-Secret": client_secret}
    os.makedirs(RAW_DIR, exist_ok=True)
    keywords = load_keywords()

    overall_summary = {
        "total_calls": 0,
        "by_source": {},
        "by_keyword": {},
        "low_result_keywords": [],  # (keyword, source, total, collected)
        "error_keywords": [],       # (keyword, source, error)
    }

    for api in APIS:
        call_log = {"calls": 0, "errors": []}
        rows = []
        source_total = 0

        for keyword in keywords:
            items, total_results = collect_for_combo(api["endpoint"], keyword, headers, call_log)
            n = len(items)
            source_total += n
            overall_summary["by_keyword"].setdefault(keyword, {})[api["source"]] = n

            if total_results is None:
                overall_summary["error_keywords"].append(
                    (keyword, api["source"], call_log["errors"][-1]["error"] if call_log["errors"] else "unknown")
                )
            elif n < TARGET_PER_COMBO:
                overall_summary["low_result_keywords"].append((keyword, api["source"], total_results, n))

            for item in items:
                date_val = item.get(api["date_field"], "") if api["date_field"] else ""
                rows.append({
                    "representative_keyword": keyword,
                    "search_query": keyword,
                    "source": api["source"],
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "link": item.get("link", ""),
                    "date": date_val,
                    "total_search_results": total_results if total_results is not None else "",
                })

            time.sleep(REQUEST_INTERVAL_SEC)

        out_path = os.path.join(RAW_DIR, api["out_file"])
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        overall_summary["by_source"][api["source"]] = {
            "collected": source_total,
            "out_path": out_path,
            "calls": call_log["calls"],
            "errors": call_log["errors"],
        }
        overall_summary["total_calls"] += call_log["calls"]

    # ---- 요약 출력 ----
    print("\n=== 전체 수집 요약 ===")
    print(f"\n1. 전체 API 호출 횟수: {overall_summary['total_calls']}")

    print("\n2. source별 수집 건수")
    for src, info in overall_summary["by_source"].items():
        print(f"  - {src}: {info['collected']}건 (호출 {info['calls']}회) -> {info['out_path']}")

    print("\n3. 키워드별 수집 건수 (blog/cafe/kin)")
    for kw in keywords:
        counts = overall_summary["by_keyword"].get(kw, {})
        print(f"  - {kw}: blog={counts.get('blog', 0)}, cafe={counts.get('cafe', 0)}, kin={counts.get('kin', 0)}")

    print("\n4. 검색 결과가 100건 미만이었던 키워드 (keyword, source, total_search_results, collected)")
    if overall_summary["low_result_keywords"]:
        for kw, src, total, n in overall_summary["low_result_keywords"]:
            print(f"  - {kw} / {src}: total={total}, collected={n}")
    else:
        print("  없음")

    print("\n5. API 오류가 발생한 키워드 (keyword, source, error)")
    if overall_summary["error_keywords"]:
        for kw, src, err in overall_summary["error_keywords"]:
            print(f"  - {kw} / {src}: {err}")
    else:
        print("  없음")

    print("\n6. 생성된 파일 경로")
    for src, info in overall_summary["by_source"].items():
        print(f"  - {info['out_path']}")


if __name__ == "__main__":
    main()
