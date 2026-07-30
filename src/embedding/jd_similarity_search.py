"""
인사팀 JD 최적화용 유사 공고 검색 (임베딩 기반, 직무 내부 검색 전용).

data/embedding/{job_embeddings.npy, job_metadata.tsv, job_embedding_index.csv} 를 로드해
사용자가 입력한 JD 텍스트와 같은 직무(job_role)의 실제 채용공고만을 대상으로
코사인 유사도 Top5를 찾고, 공통/누락 역량과 필수→우대 전환 후보를 계산한다.

절대 규칙:
- 선택한 job_role과 다른 직무의 공고는 절대 비교 대상에 포함하지 않는다.
- 유사도 수치만으로 "좋은 공고"라고 단정하는 문구를 출력하지 않는다.
- 실제 매칭된 공고에 없는 역량/기업명을 만들어내지 않는다 (전부 metadata.tsv / DB 원본 값 그대로 사용).
"""
import os
import sqlite3
from collections import Counter

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMBED_DIR = os.path.join(PROJECT_ROOT, "data", "embedding")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "recruit_processed.db")

EMBEDDINGS_NPY_PATH = os.path.join(EMBED_DIR, "job_embeddings.npy")
METADATA_PATH = os.path.join(EMBED_DIR, "job_metadata.tsv")
INDEX_PATH = os.path.join(EMBED_DIR, "job_embedding_index.csv")

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"

# 공고 대부분(테스트 기준 90%대 이상)에 거의 항상 붙는 boilerplate 태그 - 실제 역량 신호가 아니므로
# 공통역량/누락역량 비교에서 제외한다. (인사팀 Gap 탭의 build_gap_mart와 동일한 정의를 재사용)
NOISE_TOKENS = {"채용"}

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def get_model():
    """외부(대시보드)에서 동일 모델 인스턴스를 재사용하기 위한 공개 접근자."""
    return _get_model()


def embed_text(text):
    """JD 텍스트를 동일 모델로 임베딩한다 (PCA/UMAP 좌표 투영 등 외부 재사용을 위해 공개)."""
    model = _get_model()
    return model.encode([text], convert_to_numpy=True)[0].astype(np.float32)


def load_artifacts():
    embeddings = np.load(EMBEDDINGS_NPY_PATH)
    metadata = pd.read_csv(METADATA_PATH, sep="\t", encoding="utf-8-sig")
    return embeddings, metadata


def _tokenize(cell):
    return {t.strip() for t in str(cell).split(",") if t.strip() and t.strip() not in NOISE_TOKENS}


def _extract_jd_skills(jd_text, vocab):
    text_lower = jd_text.lower()
    return {v for v in vocab if v.lower() in text_lower}


def _fetch_required_preferred(job_ids):
    """Top5 매칭 공고의 required_keywords/preferred_keywords/preferred_certificates를
    원본 DB에서 다시 조회한다 (metadata.tsv엔 matched_skills만 있어 필수/우대 구분이 없음)."""
    conn = sqlite3.connect(DB_PATH)
    placeholders = ",".join("?" * len(job_ids))
    query = (
        f"SELECT rec_idx, required_keywords, preferred_keywords, preferred_certificates "
        f"FROM recruit_cleaned WHERE rec_idx IN ({placeholders})"
    )
    df = pd.read_sql(query, conn, params=[str(j) for j in job_ids])
    conn.close()
    return df.set_index("rec_idx")


def search_similar_jobs(jd_text, job_role, top_k=5):
    embeddings, metadata = load_artifacts()

    # --- 직무 내부로만 제한 (다른 직무 공고와 비교 금지) ---
    mask = (metadata["job_role"] == job_role).values
    if mask.sum() == 0:
        return {"error": f"'{job_role}' 직무의 임베딩 공고가 없습니다."}

    sub_meta = metadata[mask].reset_index(drop=True)
    sub_emb = embeddings[mask]

    model = _get_model()
    query_vec = model.encode([jd_text], convert_to_numpy=True)[0].astype(np.float32)

    query_norm = query_vec / (np.linalg.norm(query_vec) + 1e-12)
    matrix_norm = sub_emb / (np.linalg.norm(sub_emb, axis=1, keepdims=True) + 1e-12)
    sims = matrix_norm @ query_norm

    sub_meta = sub_meta.copy()
    sub_meta["similarity"] = sims
    top = sub_meta.sort_values("similarity", ascending=False).head(top_k).reset_index(drop=True)

    # --- JD 텍스트에서 언급된 역량 추출 (같은 직무 공고들의 실제 스킬 어휘 안에서만) ---
    vocab = set()
    for s in sub_meta["skills"].dropna():
        vocab |= _tokenize(s)
    jd_skills = _extract_jd_skills(jd_text, vocab)

    top_skill_sets = [_tokenize(row["skills"]) for _, row in top.iterrows()]
    skill_counter = Counter()
    for s in top_skill_sets:
        skill_counter.update(s)

    results = []
    for (_, row), posting_skills in zip(top.iterrows(), top_skill_sets):
        common = sorted(jd_skills & posting_skills)
        missing = sorted(posting_skills - jd_skills)
        results.append({
            "job_id": row["job_id"],
            "company": row["company"],
            "title": row["title"],
            "similarity": round(float(row["similarity"]), 4),
            "common_skills": common,
            "missing_in_jd": missing,
            "experience": row["experience"],
            "education": row["education"],
            "employment_type": row["employment_type"],
        })

    repeated_skills = {k for k, v in skill_counter.items() if v >= 2}  # Top5 중 2건 이상 반복된 역량
    missing_from_jd = sorted(repeated_skills - jd_skills)  # 현재 JD 누락 역량
    jd_only_rare = sorted({s for s in jd_skills if skill_counter.get(s, 0) <= 1})  # JD에만 있고 유사공고엔 거의 없음

    # --- 필수조건 완화/우대조건 전환 후보 ---
    # Top5 매칭 공고 원본에서 required/preferred 재조회 (실측치만 사용, 임의 판단 없음)
    job_ids = top["job_id"].tolist()
    rp = _fetch_required_preferred(job_ids)
    downgrade_candidates = []
    for skill in sorted(jd_skills):
        required_hits = 0
        preferred_hits = 0
        for jid in job_ids:
            if jid not in rp.index:
                continue
            row = rp.loc[jid]
            if skill.lower() in str(row["required_keywords"]).lower():
                required_hits += 1
            if skill.lower() in str(row["preferred_keywords"]).lower() or skill.lower() in str(row["preferred_certificates"]).lower():
                preferred_hits += 1
        if preferred_hits >= 2 and preferred_hits > required_hits:
            downgrade_candidates.append({
                "skill": skill, "required_hits": required_hits, "preferred_hits": preferred_hits
            })

    return {
        "job_role": job_role,
        "jd_skills": sorted(jd_skills),
        "top5": results,
        "repeated_skills_top5": sorted(repeated_skills),
        "missing_from_jd": missing_from_jd,
        "jd_only_rare": jd_only_rare,
        "downgrade_candidates": downgrade_candidates,
        "note": "유사도는 참고 지표이며, 유사도만으로 공고 품질을 판단할 수 없습니다.",
    }


if __name__ == "__main__":
    # 테스트 JD 1건 (실제 데이터셋에 존재하는 어휘로 작성한 예시 입력문 — 가짜 공고 데이터 아님)
    test_jd = (
        "개발 채용. "
        "요구역량: Python, SQL, 데이터 분석, AI. "
        "우대역량: AWS, 클라우드, 백엔드 개발 경험. "
        "경력: 신입/경력 무관. 학력: 학력무관. 고용형태: 정규직."
    )
    test_job_role = "개발"

    print(f"[테스트 JD]\n{test_jd}\n")
    print(f"[대상 직무] {test_job_role}\n")

    result = search_similar_jobs(test_jd, test_job_role, top_k=5)

    print("추출된 JD 역량:", result["jd_skills"])
    print()
    print("=== Top5 유사 공고 ===")
    for i, r in enumerate(result["top5"], 1):
        print(f"{i}. [{r['similarity']}] {r['company']} - {r['title']}")
        print(f"   경력:{r['experience']} / 학력:{r['education']} / 고용형태:{r['employment_type']}")
        print(f"   공통역량: {r['common_skills']}")
        print(f"   JD에 없는 역량: {r['missing_in_jd']}")
    print()
    print("Top5 중 2건 이상 반복 역량:", result["repeated_skills_top5"])
    print("현재 JD 누락 역량:", result["missing_from_jd"])
    print("JD에만 있고 유사공고엔 거의 없는 역량:", result["jd_only_rare"])
    print("필수→우대 전환 후보:", result["downgrade_candidates"])
    print()
    print("※", result["note"])
