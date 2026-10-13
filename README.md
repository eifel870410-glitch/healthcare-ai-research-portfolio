<p align="center">
  <img src="docs/assets/portfolio-overview.svg" alt="Healthcare AI and human factors research portfolio" width="100%">
</p>

<p align="center">
  <strong>English</strong> · <a href="README.zh-TW.md">繁體中文</a> · <a href="README.ja.md">日本語</a>
</p>

# Research Portfolio — Healthcare AI and Human Factors

I am a master's student in medical informatics. This repository records my learning and research work in healthcare AI, medical imaging, and human factors. I am interested not only in model performance, but also in whether people can use these systems safely, understand their evidence, recover from errors, and avoid inappropriate trust.

> **Record status:** an evolving record of coursework and research. Every system shown here is a research or course prototype, not a clinical product. Missing facts are marked `TODO`; no result is invented.

## At a glance

| | |
|---|---|
| **Current stage** | Master's student in medical informatics |
| **Current focus** | Healthcare AI, medical imaging, and human factors |
| **Research interests** | Medical imaging, patient communication, clinical NLP, decision support, workflow safety |
| **Core lens** | Evidence, workload, usability, trust calibration, privacy, and failure recovery |
| **Identity** | **TODO:** add preferred romanized name, confirmed affiliation, expected graduation date, academic email, and ORCID |

## Featured work

| Project | Evidence selected for this portfolio | My role | Human-factors connection |
|---|---|---|---|
| [Personalized patient education with EHR + RAG](projects/patient-education-rag/README.md) | Local LLaMA 3.2 pipeline, retrieval and citation controls, Streamlit interface, automatic and human review | Implementation evidence available; exact independent/team attribution is `TODO` | Health literacy, evidence display, trust calibration, privacy |
| [Chest X-ray quality control and pneumothorax detection](projects/chest-xray-quality-control/README.md) | Two-stage CNN prototype, confusion matrices, failure analysis, Gradio interface | Group project; personal report documents baseline testing, CNN troubleshooting, two-stage redesign, and UI work; teammate attribution is `TODO` | Shortcut learning, false negatives, image-quality workflow, human review |
| [ASA physical-status classification](projects/asa-physical-status-classification/README.md) | Individual course competition report, clinical feature engineering, weighted ensemble, leaderboard evidence | Individual project; dataset/competition provenance remains `TODO` | Explainability, leakage control, clinical risk communication |
| [Biomedical text classification under label shift](projects/biomedical-text-classification/README.md) | PubMedBERT/BioLinkBERT experiments, grouped validation, data-quality ablation | Experiment documentation available; code provenance is `TODO` | Reliability under distribution shift and appropriate trust in metrics |
| [MRI radiomics and the tumor microenvironment](projects/mri-radiomics-review/README.md) | Group literature synthesis on imaging biomarkers and clinical translation | Group work; exact individual responsibility is `TODO` | Explainability, segmentation variability, clinical integration |
| [AI applications in MRI](projects/masters-thesis/README.md) | Broad research area only | Ongoing master's research | Unpublished details withheld |

## Research question

How can healthcare AI be designed and evaluated as part of a human system so that it supports accurate decisions, reduces avoidable workload, communicates evidence and uncertainty clearly, and does not encourage inappropriate reliance?

## Evidence snapshot

These values are reported only because they are visible in source files in this workspace. Follow the project links for sample sizes, assumptions, and limitations.

| Project | Recorded evidence | Boundary on the claim |
|---|---|---|
| Patient-education RAG | 20 demo cases: 100% generation success and citation-marker presence; 10 cases reviewed by one reviewer: Hit@3 90%, citation correctness 70%, hallucination rate 30% | Prototype evaluation; citation presence did not guarantee correctness |
| Chest X-ray prototype | Orientation CNN macro F1 0.96 on 800 images; pneumothorax CNN macro F1 0.79 on 600 images | Possible paired-image leakage and cross-dataset confounding; not clinical validation |
| ASA classification | Public score 0.56536; private score 0.55817 | Course competition evidence; metric definition, URL, and data provenance are `TODO` |
| Biomedical text classification | Recorded public score 0.66273 after class-balanced data selection | Course/competition experiment; internal validation is not treated as leaderboard equivalence |

## My contributions

- Built or documented local AI prototypes spanning retrieval-augmented generation, clinical-table classification, biomedical NLP, and medical imaging.
- Retained negative results, including hallucinations, citation errors, dataset shift, shortcut learning, and false negatives, as research evidence rather than hiding them.
- Connected technical performance to questions of workload, usability, privacy, and human oversight.
- **TODO:** finalize authorship and collaborator attribution for every group project before sharing its claims externally.

## Dataset and methodology

- **Patient education:** 100 MIMIC-IV demo-derived rows and 225 hospital-approved education documents were used locally; neither source nor case-level derivatives are published.
- **Chest X-ray:** NIH-derived normal images, SIIM-ACR pneumothorax examples, and generated horizontal flips were used locally; no image or DICOM is published.
- **ASA classification:** local files contain 14,734 training and 6,315 test rows with patient-level clinical attributes; all rows are excluded pending provenance and license review.
- **Biomedical text classification:** dataset name, license, class definitions, and complete counts remain `TODO`.
- **MRI radiomics:** literature review only; no original experimental dataset.
- **Master's thesis:** all dataset and method details are intentionally withheld.

Methods include local RAG, biomedical transformers, structured/text feature engineering, gradient-boosting ensembles, convolutional neural networks, interface prototyping, and critical literature synthesis. No method is described as clinically validated.

## Error analysis and lessons learned

- Citation syntax is not the same as citation correctness; the RAG review recorded both hallucinations and incorrect citations.
- A chest X-ray CNN initially collapsed to one class. The redesigned orientation result may still be inflated if an original image and its flipped copy crossed the split.
- The pneumothorax model used normal and positive images from different source datasets, so acquisition-source confounding remains possible; 82 of 300 displayed positives were predicted as normal.
- The ASA final script used transductive preprocessing and pseudo-labeled test rows. Its recorded cross-validation is therefore not a clean independent ground-truth estimate.
- Biomedical classification showed a mismatch between internal validation and public leaderboard behavior, motivating explicit distribution-shift analysis.

These failures directly motivate my interest in human factors: systems must make uncertainty and limitations visible and must support safe recovery when the model is wrong.

## Limitations

- Most work is retrospective coursework or prototype development.
- Several evaluations are small, single-reviewer, competition-based, or vulnerable to leakage and dataset shift.
- External, prospective, multi-site, calibration, subgroup, and reader-study evidence is generally absent.
- Dataset licensing and exact individual contribution details remain incomplete for some projects.
- The public repository intentionally excludes data required for full end-to-end reproduction.

## Reproduction instructions

The data-free patient-education code is the only currently selected executable project:

```text
git clone https://github.com/eifel870410-glitch/healthcare-ai-research-portfolio.git
cd healthcare-ai-research-portfolio/NLPLLMCLASS/patient_edu_rag
python -m venv .venv
<activate the virtual environment>
pip install -r requirements.txt
```

Then follow its [setup guide](NLPLLMCLASS/patient_edu_rag/README.md). Authorized users must provide their own permitted data. Reproduction for the chest X-ray, ASA, text-classification, and thesis projects remains `TODO` until code provenance, licensing, and configuration are documented.

## Ethics and privacy

- No patient DICOM, clinical image, patient-level CSV, IRB document, institutional form, credential, API key, model weight, or case-level model output is published.
- A deny-by-default `.gitignore` and a local [public-safety scanner](scripts/check_public_safety.py) protect the repository.
- Public examples should be synthetic or explicitly licensed and must be labeled accurately.
- Competition scores and prototype metrics must not be presented as evidence of clinical effectiveness.

## Repository guide

- [`projects/`](projects/) — evidence-based project pages using a common research template.
- [`NLPLLMCLASS/patient_edu_rag/`](NLPLLMCLASS/patient_edu_rag/) — reviewed, data-free code for the patient-education prototype.
- [`docs/research-direction.md`](docs/research-direction.md) — research interests and learning notes.
- [`docs/publishing-checklist.md`](docs/publishing-checklist.md) — privacy, authorship, licensing, and claims review.

## Ongoing documentation TODO

- Confirm preferred English/romanized name, affiliation, expected graduation date, contact details, and ORCID.
- Confirm **Your role** and teammate attribution for every group project.
- Add authoritative dataset, competition, and license links.
- Translate individual project pages when useful, after factual review.
- Re-run privacy and claims review before changing the repository from private to public.

