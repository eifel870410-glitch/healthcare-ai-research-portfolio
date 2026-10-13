from __future__ import annotations
from pathlib import Path
import json
from .config import settings
from .data_loader import load_patients, patient_profile, clinical_query
from .retriever import build_index, retrieve
from .generator import build_prompt, call_ollama, validate_citations, fallback_generation
from .report import markdown_to_docx


def run_patient(subject_id: str, use_ollama: bool = True) -> dict:
    Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
    build_index(settings.leaflets_dir, settings.chroma_dir, settings.collection_name)

    df = load_patients(settings.ehr_csv)
    row_df = df[df["subject_id"].astype(str) == str(subject_id)]
    if row_df.empty:
        raise ValueError(f"找不到 subject_id={subject_id}")
    row = row_df.iloc[0]

    query = clinical_query(row)
    profile = patient_profile(row)
    hits = retrieve(query, settings.chroma_dir, settings.collection_name, settings.top_k)
    prompt = build_prompt(profile, hits)

    if use_ollama:
        answer = call_ollama(prompt, settings.ollama_model, settings.ollama_base_url)
    else:
        answer = fallback_generation(profile, hits)

    validation = validate_citations(answer, len(hits))
    md_path = Path(settings.output_dir) / f"patient_{subject_id}_education_report.md"
    md_path.write_text(answer, encoding="utf-8")
    docx_path = markdown_to_docx(answer, str(subject_id), hits, settings.report_dir)

    trace = {
        "subject_id": str(subject_id),
        "query": query,
        "retrieved": hits,
        "validation": validation,
        "markdown_report": str(md_path),
        "word_report": str(docx_path),
    }
    trace_path = Path(settings.output_dir) / f"patient_{subject_id}_trace.json"
    trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return trace

