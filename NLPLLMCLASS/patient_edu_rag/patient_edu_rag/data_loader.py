from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import re
import pandas as pd

@dataclass
class Leaflet:
    doc_id: str
    title: str
    source: str
    text: str
    path: str


def clean_text(text: str) -> str:
    text = text.replace("\ufeff", "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_leaflet(path: Path) -> Leaflet:
    raw = clean_text(path.read_text(encoding="utf-8"))
    title_match = re.search(r"^TITLE:\s*(.+)$", raw, flags=re.MULTILINE)
    source_match = re.search(r"^SOURCE:\s*(.+)$", raw, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else path.stem
    source = source_match.group(1).strip() if source_match else path.name
    body = re.sub(r"^(TITLE|SOURCE):.*$", "", raw, flags=re.MULTILINE).strip()
    return Leaflet(doc_id=path.stem, title=title, source=source, text=body, path=str(path))


def load_leaflets(leaflets_dir: str | Path) -> list[Leaflet]:
    base = Path(leaflets_dir)
    files = sorted(base.glob("*.txt"))
    if not files:
        raise FileNotFoundError(f"找不到衛教單文字檔：{base.resolve()}")
    return [parse_leaflet(p) for p in files]


def load_patients(csv_path: str | Path) -> pd.DataFrame:
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到 EHR CSV：{path.resolve()}")
    df = pd.read_csv(path)
    required = {"subject_id", "icd10_codes", "diagnoses", "prescriptions"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"EHR CSV 缺少欄位：{', '.join(sorted(missing))}")
    return df


def patient_profile(row: pd.Series) -> str:
    return (
        f"病人編號：{row.get('subject_id')}\n"
        f"年齡：{row.get('age', 'unknown')}\n"
        f"性別：{row.get('sex', 'unknown')}\n"
        f"ICD-10：{row.get('icd10_codes')}\n"
        f"診斷：{row.get('diagnoses')}\n"
        f"用藥：{row.get('prescriptions')}"
    )


def clinical_query(row: pd.Series) -> str:
    return " ".join([
        str(row.get("icd10_codes", "")),
        str(row.get("diagnoses", "")),
        str(row.get("prescriptions", "")),
    ])

