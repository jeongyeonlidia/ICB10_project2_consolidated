"""
IT개발·데이터 직무 네이버 raw 데이터 후처리 파이프라인.

raw/blog_raw.csv, raw/cafe_raw.csv, raw/kin_raw.csv 를 입력으로 받아
1) 통합  2) 중복 제거  3) 취업 관련 콘텐츠 필터링(휴리스틱 스코어링)
4) 콘텐츠 유형 분류  5) 키워드별 집계
를 수행하고 결과를 processed/ 에 새 파일로만 저장한다. raw 파일은 읽기 전용으로만 사용한다.
"""
import html
import random
import re

import pandas as pd

RAW_DIR = "data/naver_api/it_data/raw"
PROCESSED_DIR = "data/naver_api/it_data/processed"

# ---------------------------------------------------------------------------
# 0. 유틸리티
# ---------------------------------------------------------------------------
TAG_RE = re.compile(r"</?b>")


def clean_text(text):
    if not isinstance(text, str):
        return ""
    text = TAG_RE.sub("", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_link(link):
    if not isinstance(link, str) or not link.startswith("http"):
        return None
    # 네이버 지식iN 등은 docId가 쿼리스트링에 있어 식별자 역할을 하므로
    # 쿼리스트링은 보존하고, fragment와 트레일링 슬래시만 제거한다.
    link = link.split("#")[0].rstrip("/")
    return link


# ---------------------------------------------------------------------------
# 1. 데이터 통합
# ---------------------------------------------------------------------------
def merge_raw():
    frames = []
    for name in ["blog_raw.csv", "cafe_raw.csv", "kin_raw.csv"]:
        df = pd.read_csv(f"{RAW_DIR}/{name}", encoding="utf-8-sig")
        frames.append(df)
    merged = pd.concat(frames, ignore_index=True)
    merged.to_csv(f"{PROCESSED_DIR}/it_content_merged.csv", index=False, encoding="utf-8-sig")
    return merged


# ---------------------------------------------------------------------------
# 2. 중복 제거
# ---------------------------------------------------------------------------
def deduplicate(merged):
    groups = {}   # key -> group dict
    order = []    # key insertion order

    for _, row in merged.iterrows():
        norm_link = normalize_link(row.get("link"))
        if norm_link:
            key = ("link", norm_link)
        else:
            key = ("text", clean_text(row.get("title")).lower() + "||" + clean_text(row.get("description")).lower())

        if key not in groups:
            groups[key] = {
                "source": row.get("source"),
                "title": row.get("title"),
                "description": row.get("description"),
                "link": row.get("link"),
                "date": row.get("date"),
                "total_search_results": row.get("total_search_results"),
                "matched_keywords": set(),
                "matched_queries": set(),
                "duplicate_count": 0,
            }
            order.append(key)

        g = groups[key]
        g["matched_keywords"].add(row.get("representative_keyword"))
        g["matched_queries"].add(row.get("search_query"))
        g["duplicate_count"] += 1

    rows = []
    for i, key in enumerate(order):
        g = groups[key]
        mk = sorted(g["matched_keywords"])
        mq = sorted(g["matched_queries"])
        rows.append({
            "dedup_id": f"doc_{i+1:06d}",
            "representative_keyword": mk[0],
            "search_query": mq[0],
            "matched_keywords": ";".join(mk),
            "matched_queries": ";".join(mq),
            "source": g["source"],
            "title": g["title"],
            "description": g["description"],
            "link": g["link"],
            "date": g["date"],
            "total_search_results": g["total_search_results"],
            "duplicate_count": g["duplicate_count"],
        })

    dedup_df = pd.DataFrame(rows)
    dedup_df.to_csv(f"{PROCESSED_DIR}/it_content_deduplicated.csv", index=False, encoding="utf-8-sig")
    return dedup_df


# ---------------------------------------------------------------------------
# 3. 취업 관련 콘텐츠 필터링 (휴리스틱 스코어링)
# ---------------------------------------------------------------------------
TIER_A = ["취업", "취준", "취업준비", "취업 준비", "신입", "지원", "채용", "면접",
          "서류", "자소서", "자기소개서", "이직", "합격", "불합격", "인턴", "비전공자",
          "국비", "부트캠프"]
TIER_B = ["자격증", "공부", "준비", "프로젝트", "실무"]

NARRATIVE_MARKERS = ["후기", "경험담", "다녀왔습니다", "준비하면서", "준비했습니다",
                      "공부하고 있습니다", "스터디", "제가", "저는", "도전"]
QUESTION_MARKERS = ["궁금", "고민", "조언", "어떻게", "될까요", "하나요", "추천해주세요",
                     "알려주세요", "부탁드립니다"]
AD_MARKERS = ["이벤트", "쿠폰", "할인", "프로모션", "무료체험", "바로가기", "신청하기",
              "오픈기념", "특가", "☎", "문의:", "010-"]

CORP_MARKERS = ["모집공고", "채용공고", "지원자격", "우대사항", "근무지", "근무형태",
                "연봉", "경력무관", "서류전형", "최종합격자", "(주)", "㈜"]
EDU_MARKERS = ["학원", "부트캠프", "국비", "커리큘럼", "수강", "교육생 모집",
               "무료설명회", "환급", "강의"]
INFO_MARKERS = ["정리", "총정리", "알아보겠습니다", "비교", "방법"]

JOB_RELATED_THRESHOLD = 0.35


def score_row(title, description, source):
    text = clean_text(title) + " " + clean_text(description)

    a_hits = [k for k in TIER_A if k in text]
    b_hits = [k for k in TIER_B if k in text]
    narrative_hits = [k for k in NARRATIVE_MARKERS if k in text]
    question_hits = [k for k in QUESTION_MARKERS if k in text]
    ad_hits = [k for k in AD_MARKERS if k in text]

    score = len(a_hits) * 0.3 + len(b_hits) * 0.15
    booster = 0.0
    if narrative_hits:
        booster += 0.15
    if question_hits:
        booster += 0.15
    if source == "kin":
        booster += 0.1
    booster = min(booster, 0.3)
    score += booster

    penalty = 0.0
    if ad_hits and not a_hits:
        # 취업 관련 신호 없이 광고성 어휘만 있는 경우에만 감점
        penalty += 0.25 * min(len(ad_hits), 2)

    score = max(0.0, min(1.0, score - penalty))
    is_related = score >= JOB_RELATED_THRESHOLD

    reason_parts = []
    if a_hits:
        reason_parts.append("핵심 취업 신호: " + ", ".join(a_hits[:4]))
    if b_hits:
        reason_parts.append("보조 준비 신호: " + ", ".join(b_hits[:4]))
    if narrative_hits:
        reason_parts.append("개인 경험 서술 문맥 포함")
    if question_hits:
        reason_parts.append("질문/고민 문맥 포함")
    if ad_hits and not a_hits:
        reason_parts.append("취업 신호 없이 광고성 어휘만 존재하여 감점")
    if not reason_parts:
        reason_parts.append("취업 준비 관련 키워드/문맥 미발견")
    reason = " / ".join(reason_parts)

    return score, is_related, reason


def classify_content_type(title, description, source):
    text = clean_text(title) + " " + clean_text(description)

    corp_hits = sum(1 for k in CORP_MARKERS if k in text)
    has_recruit_verb = any(k in text for k in ["채용", "모집", "지원"])
    if corp_hits >= 2 and has_recruit_verb:
        return "기업 채용 홍보"

    if any(k in text for k in EDU_MARKERS):
        return "교육/학원 홍보"

    if source == "kin" or ("?" in text and any(k in text for k in QUESTION_MARKERS)):
        return "취업 고민/질문"

    if any(k in text for k in NARRATIVE_MARKERS):
        return "개인 후기"

    if any(k in text for k in INFO_MARKERS):
        return "정보 공유"

    return "기타"


def filter_and_classify(dedup_df):
    scores, relateds, reasons, ctypes = [], [], [], []
    for _, row in dedup_df.iterrows():
        score, is_related, reason = score_row(row["title"], row["description"], row["source"])
        ctype = classify_content_type(row["title"], row["description"], row["source"])
        scores.append(round(score, 2))
        relateds.append(is_related)
        reasons.append(reason)
        ctypes.append(ctype)

    classified = dedup_df.copy()
    classified["job_related_score"] = scores
    classified["is_job_related"] = relateds
    classified["job_related_reason"] = reasons
    classified["content_type"] = ctypes

    classified.to_csv(f"{PROCESSED_DIR}/it_content_classified_full.csv", index=False, encoding="utf-8-sig")

    job_related = classified[classified["is_job_related"]].reset_index(drop=True)
    job_related.to_csv(f"{PROCESSED_DIR}/it_job_related_content.csv", index=False, encoding="utf-8-sig")
    return classified, job_related


# ---------------------------------------------------------------------------
# 5. 키워드별 집계
# ---------------------------------------------------------------------------
def aggregate_by_keyword(job_related, merged):
    # 키워드별 total_search_results = 원본(raw) 기준 source별 검색 총량 합
    ts_lookup = (
        merged.drop_duplicates(subset=["representative_keyword", "source"])
        .set_index(["representative_keyword", "source"])["total_search_results"]
    )

    keywords = sorted(merged["representative_keyword"].unique())
    rows = []
    for kw in keywords:
        exploded = job_related[job_related["matched_keywords"].apply(lambda s, k=kw: k in s.split(";"))]

        blog_cnt = (exploded["source"] == "blog").sum()
        cafe_cnt = (exploded["source"] == "cafe").sum()
        kin_cnt = (exploded["source"] == "kin").sum()
        unique_cnt = len(exploded)

        total_search_results = 0
        for src in ["blog", "cafe", "kin"]:
            total_search_results += int(ts_lookup.get((kw, src), 0) or 0)

        search_query_count = merged[merged["representative_keyword"] == kw]["search_query"].nunique()

        rows.append({
            "representative_keyword": kw,
            "total_document_count": unique_cnt,
            "blog_document_count": blog_cnt,
            "cafe_document_count": cafe_cnt,
            "kin_document_count": kin_cnt,
            "unique_document_count": unique_cnt,
            "total_search_results": total_search_results,
            "search_query_count": search_query_count,
        })

    summary = pd.DataFrame(rows).sort_values("unique_document_count", ascending=False).reset_index(drop=True)
    summary.to_csv(f"{PROCESSED_DIR}/keyword_content_summary.csv", index=False, encoding="utf-8-sig")
    return summary


# ---------------------------------------------------------------------------
# 실행
# ---------------------------------------------------------------------------
def main():
    merged = merge_raw()
    dedup_df = deduplicate(merged)
    classified, job_related = filter_and_classify(dedup_df)
    summary = aggregate_by_keyword(job_related, merged)

    print("\n=== 처리 요약 ===")
    print(f"1. raw 총 건수: {len(merged)}")
    print(f"2. 중복 제거 후 건수: {len(dedup_df)} (제거된 건수: {len(merged) - len(dedup_df)})")
    print(f"3. 취업 관련 필터링 후 건수: {len(job_related)} / 전체 dedup {len(dedup_df)} ({len(job_related)/len(dedup_df):.1%})")

    print("\n4. source별 최종(취업 관련) 건수")
    print(job_related["source"].value_counts().to_string())

    print("\n5. content_type 분포 (취업 관련 콘텐츠 기준)")
    print(job_related["content_type"].value_counts().to_string())

    print("\n6. 키워드별 상위 10개 (unique_document_count 기준)")
    print(summary.head(10).to_string(index=False))

    print("\n7. 생성 파일")
    for fname in ["it_content_merged.csv", "it_content_deduplicated.csv",
                  "it_content_classified_full.csv", "it_job_related_content.csv",
                  "keyword_content_summary.csv"]:
        print(f"  - {PROCESSED_DIR}/{fname}")

    # 재현 가능한 50건 샘플 (품질 확인용, 별도 파일로 저장 - 검토는 별도로 진행)
    random.seed(42)
    sample_n = min(50, len(job_related))
    sample_idx = random.sample(range(len(job_related)), sample_n)
    sample_df = job_related.iloc[sample_idx][
        ["dedup_id", "representative_keyword", "source", "title", "description",
         "content_type", "job_related_score", "job_related_reason", "link"]
    ]
    sample_df.to_csv(f"{PROCESSED_DIR}/_quality_check_sample_50.csv", index=False, encoding="utf-8-sig")
    print(f"\n8. 품질 확인용 샘플 50건 저장: {PROCESSED_DIR}/_quality_check_sample_50.csv")


if __name__ == "__main__":
    main()
