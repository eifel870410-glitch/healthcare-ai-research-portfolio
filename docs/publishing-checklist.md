# Publishing Checklist

Use this checklist before every GitHub push or release.

## Privacy and governance

- [ ] No patient names, IDs, dates of birth, accession numbers, recognizable faces, or source-folder names that could identify a person.
- [ ] No clinical images, labels, reports, or manifests without an explicit release decision and de-identification audit.
- [ ] No IRB forms, approval letters, signatures, emails, staff records, student numbers, or institutional application forms.
- [ ] No case-level generated reports, traces, review sheets, or raw evaluation records.
- [ ] Office properties, comments, notes, hidden slides, and embedded metadata have been reviewed.
- [ ] Master's-research content is limited to a broad research area and ongoing status; unpublished details require explicit release approval.

## Secrets

- [ ] No `.env` file, API key, account password, token, credential, private key, or private endpoint.
- [ ] Example configuration contains placeholders only.
- [ ] `python scripts/check_public_safety.py` passes on staged files.

## Rights and attribution

- [ ] Every artifact is authored by me or has clear permission and a compatible license.
- [ ] Third-party papers, figures, hospital leaflets, and course slides are cited or linked rather than copied.
- [ ] Group work is labeled, and `Your role` is specific and accurate.
- [ ] Starter code, external code, pretrained models, and material AI assistance are disclosed.
- [ ] Dataset and model licenses are documented.

## Scientific claims

- [ ] Prototype, ongoing study, course experiment, literature review, and publication are clearly distinguished.
- [ ] Metrics include sample size, evaluation setting, and limitations.
- [ ] Internal holdout and public leaderboard metrics are not treated as interchangeable.
- [ ] Clinical effectiveness is not inferred from demo or internal validation.
- [ ] Missing information is marked `TODO`.
- [ ] Negative results and important failure modes are retained.

## Reproducibility and presentation

- [ ] Setup steps, versions, seeds, split logic, and hardware assumptions are documented.
- [ ] Paths are portable and reveal no local username or private directory.
- [ ] Links work from the repository root.
- [ ] Preferred romanized name and English wording have been reviewed.
- [ ] `git diff --cached` contains only intended public material.

## Suggested sequence

```text
git status --short
git add <reviewed files only>
python scripts/check_public_safety.py
git diff --cached
git commit -m "Curate research portfolio"
git push
```

