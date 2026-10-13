# Biomedical Text Classification under Label Shift

**Evidence level:** course/Kaggle experiment; code and dataset documentation incomplete

## Project overview

This experiment investigated why stronger biomedical language models and model stacking did not reliably improve a public leaderboard score. The work shifted from model-centric tuning toward diagnosis of label quality, grouped validation, domain shift, and class-balanced data selection.

## Problem

Internal validation appeared stronger than public leaderboard performance. Duplicate text, inconsistent labels, class imbalance, and train/test distribution differences could make ordinary cross-validation misleading.

## Research question

When internal validation and public evaluation disagree, can grouped validation and class-balanced sample-quality filtering improve robustness more effectively than additional model stacking?

## Your role

The course slides document my progression through PubMedBERT, BioLinkBERT, TF-IDF, focal loss, class weighting, grouped validation, duplicate-text checks, and data-quality ablation.

**TODO:** add the exact code I wrote, identify any starter notebooks or collaborators, and disclose material AI assistance or external code.

## Dataset

**TODO:** add the competition name and URL, dataset source, license, task definition, total train/test counts, five class definitions, label distribution, and permitted use.

The current slides mention approximately 9,000 training rows and approximately 500 identical texts across train and test, but the source files needed to independently verify those counts are not present in the curated code. Treat both values as provisional until verified.

## Methodology

- PubMedBERT as the primary biomedical transformer.
- BioLinkBERT and TF-IDF in ensemble experiments.
- Class weighting and focal loss for imbalance.
- Duplicate-text and formatting diagnostics.
- `StratifiedGroupKFold` to reduce leakage from related samples.
- Out-of-fold probabilities as a sample-quality signal.
- Class-balanced extraction to prevent minority classes from disappearing during pruning.
- Fixed pseudo-public holdout for ablation after cross-validation/leaderboard mismatch.

## Experimental setup

**TODO:** document model checkpoints, tokenizer settings, maximum length, optimizer, learning rate, epochs, batch size, fold count, group definition, seeds, hardware, software versions, ensemble weights, and leaderboard submission dates.

## Results

The following numbers are transcribed from the existing course presentation:

| Experiment | Recorded metric |
|---|---:|
| Initial public leaderboard plateau | approximately 0.63 |
| Grouped-validation submission | 0.621 public leaderboard |
| Full-data baseline | 0.8318 internal holdout macro F1 |
| High-precision subset, approximately 3,587 rows | 0.7929 internal holdout macro F1 |
| Medium-precision balanced subset, approximately 6,001 rows | 0.8365 internal holdout macro F1 |
| Medium-precision balanced submission | 0.66273 public leaderboard |

Internal holdout macro F1 and public leaderboard score are different evaluation contexts and must not be compared as if they were the same metric.

## Error analysis

- Direct label transfer for duplicate train/test text reportedly reduced the public score from about 0.63 to 0.59, suggesting label inconsistency or a mistaken leakage assumption.
- A larger DeBERTa experiment collapsed to a single-class prediction in the recorded environment.
- Global top-quality filtering removed coverage and caused minority classes to disappear.
- Strict grouping did not by itself remove the validation/leaderboard gap.

**TODO:** verify every value from executable logs, add per-class confusion matrices, inspect mislabeled examples under the dataset license, and separate environment failure from modeling failure.

## Limitations

- The public task, dataset, and license are not yet documented.
- Training code and logs are not packaged in the curated repository.
- The pseudo-public holdout may have influenced iterative decisions.
- Leaderboard feedback can encourage overfitting.
- Approximate sample counts are currently supported only by slides.

## Lessons learned

- A higher cross-validation score is not useful if the validation design does not represent deployment or test conditions.
- Data quality, class coverage, and distribution shift can dominate architecture changes.
- Negative results are valuable when they lead to a clearer diagnostic strategy.
- Evaluation context must be communicated so users do not over-trust a single number.

## Reproducibility

**TODO:** add a clean training entry point, configuration file, pinned environment, dataset download instructions, preprocessing hash, fixed seeds, and a command that reproduces each ablation table row.

No raw competition data or model artifacts should be committed until the license and file contents are reviewed.

## Ethics and privacy

- Confirm that the dataset contains no personal or protected health information.
- Follow the competition and source-dataset licenses.
- Do not redistribute restricted text or labels.
- Report label noise and distribution shift without exposing sensitive examples.
- Do not present leaderboard performance as clinical utility.

