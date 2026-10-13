# Personalized Patient Education with EHR + RAG

**Evidence level:** working course prototype; not clinically validated
**Public code:** [`NLPLLMCLASS/patient_edu_rag/`](../../NLPLLMCLASS/patient_edu_rag/)

## Project overview

This project explores a local system that retrieves approved patient-education content and uses a local LLaMA 3.2 model to draft a Traditional Chinese report tailored to structured diagnoses and medications.

## Problem

Static patient-education materials are not tailored to an individual's clinical profile, while clinical staff have limited time to assemble personalized explanations. General-purpose language models can also produce unsupported medical statements or expose sensitive information when external services are used.

## Research question

Can a locally executed retrieval-augmented generation pipeline produce traceable, readable, personalized patient-education drafts from structured demo EHR data and an approved knowledge base?

## Your role

The current repository contains the pipeline, retrieval and generation modules, Streamlit interface, report export, automatic evaluation, and human-review tools associated with my course project.

**TODO:** confirm which components I personally designed, coded, evaluated, or revised; identify any classmates, supervisors, or AI-assisted development that require attribution.

## Dataset

- **Structured records:** 100 rows derived from the MIMIC-IV demo data in the current local workspace.
- **Knowledge base:** 225 hospital-approved patient-education text documents.
- **Automatic evaluation sample:** the first 20 demo records.
- **Human-review sample:** 10 records reviewed by one reviewer.

The 100 available records must not be confused with the 20 automatically evaluated or 10 human-reviewed cases. Source data, case identifiers, leaflets, generated reports, traces, vector indexes, and review rows are excluded from Git.

## Methodology

1. Load structured diagnoses, diagnosis codes, and medications.
2. Construct a clinical query from the selected demo record.
3. Retrieve the top three education documents with a multilingual sentence-transformer and ChromaDB.
4. Select relevant passages and build a constrained prompt.
5. Generate a Traditional Chinese report with local Ollama/LLaMA 3.2.
6. Require source markers and check for missing sections.
7. Export Markdown, Word, and a trace record.
8. Run automatic structure checks and a separate human-review workflow.

## Experimental setup

- Local Python application on Windows.
- Ollama model recorded in code: `llama3.2`.
- Embedding model recorded in code: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`.
- Retrieval depth: top 3 documents.
- Automatic batch: 20 demo cases.
- Human review: 10 cases, one reviewer.

**TODO:** add the exact hardware, operating-system version, dependency lockfile, random seeds where applicable, evaluation date, and model build/version.

## Results

### Automatic evaluation

| Metric | Result | Scope |
|---|---:|---|
| Generation success | 100% | 20 demo cases |
| Citation presence | 100% | Automatic string check |
| Section completeness | 100% | Automatic structural check |
| Mean inference time | 511.45 seconds | 20 successful local runs |
| Mean report length | 1,031.40 characters | 20 generated reports |

### Human review

| Metric | Result | Scope |
|---|---:|---|
| Retrieval Hit@3 | 90% | 10 cases, one reviewer |
| Hallucination rate | 30% | 10 cases, one reviewer |
| Personalization | 4.2 / 5 | 10 cases, one reviewer |
| Readability | 4.7 / 5 | 10 cases, one reviewer |
| Citation correctness | 70% | 10 cases, one reviewer |
| Overall usefulness | 4.3 / 5 | 10 cases, one reviewer |

These figures describe a small prototype evaluation. Citation presence is not equivalent to citation correctness, and the results do not establish clinical effectiveness.

## Error analysis

- Three of the ten reviewed reports were marked as containing hallucinated content.
- Citation correctness was 70%, despite citation markers being present in all automatically checked reports.
- Retrieval missed the expected relevant document in one of ten reviewed cases.
- Mean local inference time was substantially slower than the project's original target.

**TODO:** create a non-sensitive error taxonomy, obtain multiple reviewers, measure inter-rater reliability, and publish only synthetic or fully authorized examples.

## Limitations

- Small sample sizes and only one human reviewer.
- No blinded comparison, external validation, prospective study, or patient-outcome evaluation.
- Automatic checks measured formatting and marker presence rather than medical correctness.
- The knowledge base may not cover every diagnosis or medication.
- Dependency versions are not fully pinned.
- Data and institutional materials cannot be redistributed, limiting end-to-end reproduction.

## Lessons learned

- Grounding and citation formatting reduce neither hallucination nor citation error by themselves.
- Data provenance and human review must be designed into the workflow.
- Readability, usefulness, inference time, and error detectability are human-factors outcomes, not secondary implementation details.
- Honest reporting of failure rates is more informative than presenting only successful examples.

## Reproducibility

```text
cd NLPLLMCLASS/patient_edu_rag
python -m venv .venv
<activate the virtual environment>
pip install -r requirements.txt
```

Install Ollama and the recorded local model, then follow the detailed [source-code README](../../NLPLLMCLASS/patient_edu_rag/README.md).

To execute the full workflow, an authorized user must create the expected local files under `data/ehr/` and `data/leaflets/`. Those files are intentionally absent. Do not substitute real patient data for a portfolio demonstration.

**TODO:** add a small synthetic dataset, pinned environment, smoke test, and expected command output.

## Ethics and privacy

- Local inference avoids sending clinical text to an external generation API.
- MIMIC-IV data must be handled under its applicable PhysioNet access, license, and citation requirements.
- Hospital education materials require an explicit rights review before redistribution.
- No identifiers, case-level output, clinical report, vector index, or reviewer row is included in Git.
- This prototype is not a medical device and must not be used to provide unsupervised clinical advice.

