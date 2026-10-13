from pathlib import Path
import pandas as pd


# =========================
# 路徑設定
# =========================
PROJECT_ROOT = Path(__file__).resolve().parents[1]

MIMIC_DIR = PROJECT_ROOT / "data" / "mimic_demo"
OUT_DIR = PROJECT_ROOT / "data" / "ehr"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_PATH = OUT_DIR / "patients_demo.csv"


# =========================
# 讀取 MIMIC demo 資料
# =========================
print("讀取 MIMIC demo 資料中...")

diagnoses = pd.read_csv(MIMIC_DIR / "diagnoses_icd.csv.gz")
diag_dict = pd.read_csv(MIMIC_DIR / "d_icd_diagnoses.csv.gz")
prescriptions = pd.read_csv(MIMIC_DIR / "prescriptions.csv.gz")
patients = pd.read_csv(MIMIC_DIR / "patients.csv.gz")


# =========================
# 整理 ICD 診斷資料
# =========================
print("整理 ICD 診斷資料中...")

diagnoses["icd_code"] = diagnoses["icd_code"].astype(str)
diag_dict["icd_code"] = diag_dict["icd_code"].astype(str)

diagnoses = diagnoses.merge(
    diag_dict[["icd_code", "icd_version", "long_title"]],
    on=["icd_code", "icd_version"],
    how="left"
)

# 原始 ICD code：給系統欄位 icd10_codes 使用
icd_code_summary = (
    diagnoses
    .dropna(subset=["icd_code"])
    .groupby("subject_id")["icd_code"]
    .apply(lambda x: "; ".join(sorted(set(x.astype(str)))[:20]))
    .reset_index()
    .rename(columns={"icd_code": "icd10_codes"})
)

# 診斷名稱：給報告展示使用
diagnosis_summary = (
    diagnoses
    .dropna(subset=["long_title"])
    .groupby("subject_id")["long_title"]
    .apply(lambda x: "; ".join(sorted(set(x.astype(str)))[:10]))
    .reset_index()
    .rename(columns={"long_title": "diagnoses"})
)


# =========================
# 整理用藥資料
# =========================
print("整理用藥資料中...")

if "drug" in prescriptions.columns:
    drug_col = "drug"
elif "drug_type" in prescriptions.columns:
    drug_col = "drug_type"
else:
    raise ValueError("prescriptions.csv.gz 找不到 drug 或 drug_type 欄位")

med_summary = (
    prescriptions
    .dropna(subset=[drug_col])
    .groupby("subject_id")[drug_col]
    .apply(lambda x: "; ".join(sorted(set(x.astype(str)))[:20]))
    .reset_index()
    .rename(columns={drug_col: "prescriptions"})
)

# 另外保留 medications 欄位，方便展示
med_summary["medications"] = med_summary["prescriptions"]


# =========================
# 整理病人基本資料
# =========================
print("整理病人基本資料中...")

patient_cols = ["subject_id"]

if "gender" in patients.columns:
    patient_cols.append("gender")

if "anchor_age" in patients.columns:
    patient_cols.append("anchor_age")

ehr = patients[patient_cols].copy()


# =========================
# 合併病人、診斷、用藥
# =========================
ehr = ehr.merge(icd_code_summary, on="subject_id", how="left")
ehr = ehr.merge(diagnosis_summary, on="subject_id", how="left")
ehr = ehr.merge(med_summary, on="subject_id", how="left")

ehr["icd10_codes"] = ehr["icd10_codes"].fillna("")
ehr["diagnoses"] = ehr["diagnoses"].fillna("")
ehr["prescriptions"] = ehr["prescriptions"].fillna("")
ehr["medications"] = ehr["medications"].fillna("")

# 只保留有診斷或用藥的病人
ehr = ehr[(ehr["icd10_codes"] != "") | (ehr["prescriptions"] != "")]


# =========================
# 欄位順序
# =========================
keep_cols = [
    "subject_id",
    "gender",
    "anchor_age",
    "icd10_codes",
    "prescriptions",
    "diagnoses",
    "medications",
]

ehr = ehr[[col for col in keep_cols if col in ehr.columns]]


# =========================
# 輸出成專案需要的 patients_demo.csv
# =========================
ehr.to_csv(OUT_PATH, index=False, encoding="utf-8-sig")

print("完成！")
print(f"輸出檔案：{OUT_PATH}")
print()
print(f"總 demo 紀錄數：{len(ehr)}")
print("為避免在終端機或操作紀錄中暴露識別欄位，本程式不列印個別 subject_id。")

