"""
인사팀 JD 최적화용 유사 공고 임베딩 생성 파이프라인.

data/recruit_processed.db 의 recruit_cleaned 테이블(사람인 실채용공고 5,000건)에서
제목/직무/요구역량/우대역량/경력/학력/고용형태를 결합한 임베딩 입력문을 만들고,
다국어(한국어+영문) sentence-transformers 모델로 문장 임베딩을 생성해
data/embedding/ 아래 4개 파일로 저장한다.

절대 규칙:
- 직무(job_group)가 다른 공고끼리는 비교하지 않는다 (직무별로만 유사도 계산 가능하도록 인덱스 구성).
- 결측/중복 공고를 정제하되, 실제로 존재하지 않는 역량·기업명·공고를 새로 만들지 않는다.
- 대시보드 코드는 이 스크립트에서 건드리지 않는다.
"""
import os
import sqlite3
import sys

import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "recruit_processed.db")
OUT_DIR = os.path.join(PROJECT_ROOT, "data", "embedding")

VECTORS_PATH = os.path.join(OUT_DIR, "job_vectors.tsv")
METADATA_PATH = os.path.join(OUT_DIR, "job_metadata.tsv")
EMBEDDINGS_NPY_PATH = os.path.join(OUT_DIR, "job_embeddings.npy")
INDEX_PATH = os.path.join(OUT_DIR, "job_embedding_index.csv")

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"  # 한국어+영문 혼합 문장에 적합한 다국어 모델

# 대시보드 인사팀 탭이 다루는 5개 직무와 사람인 job_group 매핑 (기존 SARAMIN_JOB_MAP과 동일)
SARAMIN_JOB_MAP = {
    "기획/전략": "영업·사업개발",
    "인사/노무": "인사·HR·총무",
    "회계/재무": "회계·재무·경영관리",
    "마케팅": "마케팅·CRM",
    "데이터분석가/AI엔지니어": "IT개발·데이터",
}
JOB_GROUP_TO_ROLE = {v: k for k, v in SARAMIN_JOB_MAP.items()}


def load_and_clean():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT * FROM recruit_cleaned", conn)
    conn.close()
    before = len(df)

    # 대시보드가 다루는 5개 직무(job_group)만 대상으로 한다.
    df = df[df["job_group"].isin(JOB_GROUP_TO_ROLE.keys())].copy()

    # 결측: 사용 컬럼(title/job_group/experience_level/education_level/employment_type)은
    # 원본에 결측이 없으나(사전 확인 완료), 방어적으로 title 공백 행만 제외한다.
    df = df[df["title"].fillna("").str.strip() != ""]

    # 중복 공고 제거: 동일 기업명+제목은 같은 공고의 재게시/중복 수집으로 간주해 첫 건만 남긴다.
    df = df.drop_duplicates(subset=["company_name", "title"], keep="first")

    # matched_skills가 완전히 비어 있으면(스킬 신호 전무) 임베딩 비교 의미가 없어 제외한다.
    df = df[df["matched_skills"].fillna("").str.strip() != ""]

    after = len(df)
    return df, before, after


def build_embedding_text(row):
    parts = [f"제목: {row['title']}", f"직무: {row['job_group']}"]
    if str(row["required_keywords"]).strip():
        parts.append(f"요구역량: {row['required_keywords']}")
    preferred = ", ".join(
        v for v in [str(row["preferred_keywords"]).strip(), str(row["preferred_certificates"]).strip()] if v
    )
    if preferred:
        parts.append(f"우대역량: {preferred}")
    if str(row["experience_level"]).strip():
        parts.append(f"경력: {row['experience_level']}")
    if str(row["education_level"]).strip():
        parts.append(f"학력: {row['education_level']}")
    if str(row["employment_type"]).strip():
        parts.append(f"고용형태: {row['employment_type']}")
    return ". ".join(parts) + "."


def main():
    print("[1단계] recruit_cleaned 로드 및 정제...")
    df, before, after = load_and_clean()
    print(f"  정제 전 {before}건 -> 정제 후 {after}건 (5개 직무 외 제외 + 중복/공백 제거)")
    print("  직무별 공고 수:")
    role_counts = df["job_group"].map(JOB_GROUP_TO_ROLE).value_counts()
    for role, cnt in role_counts.items():
        print(f"    - {role}: {cnt}건")

    print("\n[2단계] 임베딩 입력문 생성...")
    df["job_role"] = df["job_group"].map(JOB_GROUP_TO_ROLE)
    df["embedding_text"] = df.apply(build_embedding_text, axis=1)
    print("  샘플:", df["embedding_text"].iloc[0][:150])

    print(f"\n[3단계] 문장 임베딩 모델 로드 ({MODEL_NAME})...")
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_NAME)

    print(f"\n[4단계] {len(df)}건 임베딩 생성 중 (배치 처리)...")
    embeddings = model.encode(
        df["embedding_text"].tolist(),
        batch_size=64,
        show_progress_bar=True,
        convert_to_numpy=True,
    ).astype(np.float32)
    print(f"  임베딩 shape: {embeddings.shape}")

    print("\n[5단계] 결과 저장...")
    os.makedirs(OUT_DIR, exist_ok=True)

    # job_embeddings.npy: 원본 float32 행렬 (행 순서 = df 순서 = metadata/vectors/index와 동일)
    np.save(EMBEDDINGS_NPY_PATH, embeddings)
    print(f"  -> {EMBEDDINGS_NPY_PATH} {embeddings.shape}")

    # job_vectors.tsv: TensorFlow Projector 관례 (헤더 없음, 탭 구분 float)
    np.savetxt(VECTORS_PATH, embeddings, delimiter="\t")
    print(f"  -> {VECTORS_PATH} ({len(df)}행)")

    # job_metadata.tsv: 헤더 있음, vectors.tsv와 행 순서 1:1
    meta = pd.DataFrame({
        "job_id": df["rec_idx"],
        "job_role": df["job_role"],
        "company": df["company_name"],
        "title": df["title"],
        "experience": df["experience_level"],
        "education": df["education_level"],
        "employment_type": df["employment_type"],
        "skills": df["matched_skills"],
        "embedding_text": df["embedding_text"],
    })
    meta.to_csv(METADATA_PATH, sep="\t", index=False, encoding="utf-8-sig")
    print(f"  -> {METADATA_PATH} ({len(meta)}행)")

    # job_embedding_index.csv: row_index <-> job_id/job_role 경량 조회 인덱스
    index_df = pd.DataFrame({
        "row_index": range(len(df)),
        "job_id": df["rec_idx"].values,
        "job_role": df["job_role"].values,
    })
    index_df.to_csv(INDEX_PATH, index=False, encoding="utf-8-sig")
    print(f"  -> {INDEX_PATH} ({len(index_df)}행)")

    print("\n=== 완료 ===")


if __name__ == "__main__":
    main()
