from __future__ import annotations
import json
import time
from pathlib import Path
import pandas as pd
from patient_edu_rag.config import settings
from patient_edu_rag.data_loader import load_patients, clinical_query
from patient_edu_rag.retriever import build_index, retrieve

# Demo ground truth：正式專案可改成人工標註的 subject_id -> relevant leaflet doc_id 清單
ground_truth = {
    "10001": ["diabetes_metformin", "hypertension_lisinopril"],
    "10002": ["copd_inhaler", "heart_failure_furosemide"],
    "10003": ["ckd_medication", "hyperlipidemia_statin"],
}


def main():
    build_index(settings.leaflets_dir, settings.chroma_dir, settings.collection_name)
    df = load_patients(settings.ehr_csv)
    rows = []
    start_all = time.time()
    for _, row in df.iterrows():
        sid = str(row["subject_id"])
        start = time.time()
        hits = retrieve(clinical_query(row), settings.chroma_dir, settings.collection_name, settings.top_k)
        elapsed = time.time() - start
        returned = [h["doc_id"] for h in hits]
        truth = ground_truth.get(sid, [])
        hit = any(x in returned for x in truth)
        rows.append({
            "subject_id": sid,
            "hit@k": int(hit),
            "returned": ";".join(returned),
            "truth": ";".join(truth),
            "retrieval_seconds": round(elapsed, 3),
        })
    out = pd.DataFrame(rows)
    hit_rate = out["hit@k"].mean() if len(out) else 0
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(settings.output_dir) / "retrieval_eval.csv"
    out.to_csv(out_path, index=False, encoding="utf-8-sig")
    summary = {
        "top_k": settings.top_k,
        "hit_rate": round(float(hit_rate), 4),
        "average_retrieval_seconds": round(float(out["retrieval_seconds"].mean()), 3),
        "total_seconds": round(time.time() - start_all, 3),
        "eval_csv": str(out_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

