"""
IT개발·데이터 직무 네이버 API 테스트 수집 스크립트.

data/naver_api/it_data/search_queries/ 의 키워드 중 3개(Python, SQL, ADsP)만
블로그/카페글/지식iN 검색 API로 소량(display=15) 수집해 raw/ 에 저장한다.
"""
import csv
import os
import sys
import time

import requests
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(PROJECT_ROOT, "data", "naver_api", "it_data", ".env")
RAW_DIR = os.path.join(PROJECT_ROOT, "data", "naver_api", "it_data", "raw")

TEST_KEYWORDS = [
    {"representative_keyword": "Python", "search_query": "Python"},
    {"representative_keyword": "SQL", "search_query": "SQL"},
    {"representative_keyword": "ADsP", "search_query": "ADsP"},
]

APIS = [
    {"source": "blog", "endpoint": "https://openapi.naver.com/v1/search/blog.json", "date_field": "postdate", "out_file": "blog_test_raw.csv"},
    {"source": "cafe", "endpoint": "https://openapi.naver.com/v1/search/cafearticle.json", "date_field": None, "out_file": "cafe_test_raw.csv"},
    {"source": "kin", "endpoint": "https://openapi.naver.com/v1/search/kin.json", "date_field": None, "out_file": "kin_test_raw.csv"},
]

DISPLAY = 15
FIELDNAMES = ["representative_keyword", "search_query", "source", "title", "description", "link", "date"]


def call_naver_api(endpoint, query, client_id, client_secret):
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    params = {"query": query, "display": DISPLAY, "start": 1, "sort": "sim"}
    resp = requests.get(endpoint, headers=headers, params=params, timeout=10)
    return resp


def main():
    load_dotenv(ENV_PATH)
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수를 찾을 수 없습니다.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(RAW_DIR, exist_ok=True)

    summary = []

    for api in APIS:
        rows = []
        api_summary = {"source": api["source"], "calls": []}

        for kw in TEST_KEYWORDS:
            resp = call_naver_api(api["endpoint"], kw["search_query"], client_id, client_secret)
            status = resp.status_code
            count = 0
            error_msg = ""

            if status == 200:
                items = resp.json().get("items", [])
                for item in items:
                    date_val = item.get(api["date_field"], "") if api["date_field"] else ""
                    rows.append({
                        "representative_keyword": kw["representative_keyword"],
                        "search_query": kw["search_query"],
                        "source": api["source"],
                        "title": item.get("title", ""),
                        "description": item.get("description", ""),
                        "link": item.get("link", ""),
                        "date": date_val,
                    })
                count = len(items)
            else:
                try:
                    error_msg = resp.json().get("errorMessage", resp.text[:200])
                except Exception:
                    error_msg = resp.text[:200]

            api_summary["calls"].append({
                "keyword": kw["representative_keyword"],
                "status": status,
                "count": count,
                "error": error_msg,
            })
            time.sleep(0.2)

        out_path = os.path.join(RAW_DIR, api["out_file"])
        with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)

        api_summary["out_path"] = out_path
        api_summary["total_rows"] = len(rows)
        summary.append(api_summary)

    print("\n=== 수집 결과 요약 ===")
    for api_summary in summary:
        print(f"\n[{api_summary['source']}] -> {api_summary['out_path']} (총 {api_summary['total_rows']}건)")
        for call in api_summary["calls"]:
            status_label = "OK" if call["status"] == 200 else f"FAIL({call['status']})"
            print(f"  - {call['keyword']}: {status_label}, {call['count']}건" + (f", error={call['error']}" if call["error"] else ""))


if __name__ == "__main__":
    main()
