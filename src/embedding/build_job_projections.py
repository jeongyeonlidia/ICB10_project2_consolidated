"""
job_embeddings.npy(384차원)를 직무별로 PCA 3D / UMAP 2D로 사전 축소해 저장한다.
대시보드의 "의미 기반 유사 역량 매칭" 산점도가 이 파일을 그대로 로드해서 쓰고,
사용자가 입력한 JD 벡터는 여기서 저장한 fitted PCA/UMAP 모델로 같은 좌표계에 투영한다
(재학습 없이 transform()만 수행 → 대시보드에서 매번 새로 학습하지 않음).

직무별로 따로 적합(fit)한다 — 화면에서 항상 선택 직무 공고만 보여주므로,
다른 직무 데이터가 섞여 투영 구조를 왜곡하지 않게 하기 위함이다.
"""
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EMBED_DIR = os.path.join(PROJECT_ROOT, "data", "embedding")
EMBEDDINGS_NPY_PATH = os.path.join(EMBED_DIR, "job_embeddings.npy")
METADATA_PATH = os.path.join(EMBED_DIR, "job_metadata.tsv")
COORDS_PATH = os.path.join(EMBED_DIR, "job_projection_coords.csv")
MODELS_DIR = os.path.join(EMBED_DIR, "projection_models")

if os.path.exists(COORDS_PATH):
    raise SystemExit(f"[중단] 기존 파일을 덮어쓸 수 없습니다: {COORDS_PATH}")


def safe_name(job_role):
    return job_role.replace("/", "_")


def main():
    from umap import UMAP  # 임포트 시점 지연 (umap-learn 로드 비용)

    embeddings = np.load(EMBEDDINGS_NPY_PATH)
    metadata = pd.read_csv(METADATA_PATH, sep="\t", encoding="utf-8-sig")
    assert len(embeddings) == len(metadata), "embeddings와 metadata 행수 불일치"

    os.makedirs(MODELS_DIR, exist_ok=True)
    rows = []

    for job_role in metadata["job_role"].unique():
        mask = (metadata["job_role"] == job_role).values
        job_ids = metadata.loc[mask, "job_id"].values
        job_emb = embeddings[mask]
        print(f"[{job_role}] {len(job_emb)}건 - PCA/UMAP 적합 중...")

        pca = PCA(n_components=3, random_state=42)
        pca_coords = pca.fit_transform(job_emb)

        umap_model = UMAP(n_components=2, random_state=42, n_neighbors=15, min_dist=0.1)
        umap_coords = umap_model.fit_transform(job_emb)

        joblib.dump(pca, os.path.join(MODELS_DIR, f"{safe_name(job_role)}_pca.joblib"))
        joblib.dump(umap_model, os.path.join(MODELS_DIR, f"{safe_name(job_role)}_umap.joblib"))

        for i, jid in enumerate(job_ids):
            rows.append({
                "job_id": jid,
                "job_role": job_role,
                "pca_x": pca_coords[i, 0], "pca_y": pca_coords[i, 1], "pca_z": pca_coords[i, 2],
                "umap_x": umap_coords[i, 0], "umap_y": umap_coords[i, 1],
            })
        print(f"  -> PCA 분산설명비율(3D 합): {pca.explained_variance_ratio_.sum():.3f}")

    coords_df = pd.DataFrame(rows)
    coords_df.to_csv(COORDS_PATH, index=False, encoding="utf-8-sig")
    print(f"\n저장 완료: {COORDS_PATH} ({len(coords_df)}행)")
    print(f"모델 저장 위치: {MODELS_DIR}")


if __name__ == "__main__":
    main()
