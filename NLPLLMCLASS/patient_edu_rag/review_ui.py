from pathlib import Path
import re
import shutil
import base64

import pandas as pd
import streamlit as st
from docx import Document
import fitz  # PyMuPDF，用來讀取 PDF 文字

from patient_edu_rag.config import settings


# =========================================================
# 路徑設定
# =========================================================
PROJECT_ROOT = Path(__file__).resolve().parent

REPORTS_DIR = PROJECT_ROOT / "reports"
UPLOAD_REPORTS_DIR = PROJECT_ROOT / "eval_results" / "uploaded_reports"
OUTPUTS_DIR = PROJECT_ROOT / "outputs"

EVAL_DIR = PROJECT_ROOT / "eval_results"
REVIEWS_DIR = EVAL_DIR / "reviews"

GENERATION_CSV = EVAL_DIR / "generation_eval.csv"
HUMAN_SUMMARY_TXT = EVAL_DIR / "human_summary.txt"

EVAL_DIR.mkdir(exist_ok=True)
REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)
UPLOAD_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


# =========================================================
# 評估欄位
# =========================================================
REQUIRED_REVIEW_COLS = [
    "retrieval_hit_0_1",
    "hallucination_found_0_1",
    "personalization_score_1_to_5",
    "readability_score_1_to_5",
    "citation_correct_0_1",
]

ALL_REVIEW_COLS = REQUIRED_REVIEW_COLS + [
    "overall_usefulness_1_to_5",
    "reviewer_comments",
    "reviewer_id",
]

TEXT_COLS = [
    "retrieval_hit_0_1",
    "hallucination_found_0_1",
    "personalization_score_1_to_5",
    "readability_score_1_to_5",
    "citation_correct_0_1",
    "overall_usefulness_1_to_5",
    "reviewer_comments",
    "reviewer_id",
]

EXPECTED_SECTIONS = [
    "病人狀況摘要",
    "主要衛教重點",
    "用藥與日常照護提醒",
    "需要回診或立即尋求協助的情況",
    "給病人的簡短提醒",
    "引用來源",
]


# =========================================================
# Streamlit 設定
# =========================================================
st.set_page_config(
    page_title="衛教報告人工評估系統",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# =========================================================
# CSS
# =========================================================
st.markdown(
    """
    <style>
    .block-container {
        max-width: 1450px;
        padding-top: 2rem;
        padding-bottom: 3rem;
    }

    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1f2937;
        margin-bottom: 0.25rem;
    }

    .sub-title {
        color: #6b7280;
        margin-bottom: 1.5rem;
    }

    .top-box {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 1rem 1.2rem;
        margin-bottom: 1.2rem;
    }

    .case-card {
        border-radius: 12px;
        padding: 0.75rem 0.9rem;
        margin-bottom: 0.5rem;
        border: 1px solid #e5e7eb;
        font-size: 0.95rem;
    }

    .case-done {
        background-color: #ecfdf5;
        border-color: #a7f3d0;
        color: #065f46;
    }

    .case-pending {
        background-color: #fef2f2;
        border-color: #fecaca;
        color: #991b1b;
    }

    .patient-box {
        background: #f8fafc;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1rem 1.25rem;
        margin-bottom: 1rem;
    }

    .report-box {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1.25rem;
        max-height: 650px;
        overflow-y: auto;
        white-space: normal;
    }

    .pdf-box {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 0.75rem;
    }

    .review-box {
        background: #ffffff;
        border: 1px solid #e5e7eb;
        border-radius: 14px;
        padding: 1rem 1.25rem;
    }

    .metric-pill {
        display: inline-block;
        padding: 0.3rem 0.7rem;
        border-radius: 999px;
        font-size: 0.9rem;
        margin-right: 0.4rem;
        margin-bottom: 0.4rem;
        background-color: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 型別修復工具
# =========================================================
def force_text_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    防止 pandas 把空白評分欄位讀成 float64。
    所有評分欄位都強制轉成文字欄位。
    """
    for col in TEXT_COLS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    return df


# =========================================================
# 報告讀取與 PDF 顯示
# =========================================================
def extract_subject_id(filename: str) -> str:
    """
    從檔名抓 subject_id。

    支援以數字型 demo subject_id 命名的報告檔案，例如：
    patient_<subject_id>_education_report.docx
    patient_<subject_id>_education_report_<timestamp>.pdf
    <subject_id>_report.pdf
    """
    match = re.search(r"patient_(\d+)_education_report", filename)
    if match:
        return match.group(1)

    match = re.search(r"(\d{6,})", filename)
    if match:
        return match.group(1)

    return ""


def safe_filename(filename: str) -> str:
    filename = filename.replace(" ", "_")
    filename = "".join(
        ch for ch in filename
        if ch.isalnum() or ch in ["_", "-", ".", "(", ")"]
    )
    return filename


def read_docx_text(docx_path: Path) -> str:
    try:
        doc = Document(docx_path)
        paragraphs = []

        for p in doc.paragraphs:
            text = p.text.strip()
            if text:
                paragraphs.append(text)

        return "\n\n".join(paragraphs)

    except Exception as e:
        print(f"讀取 Word 失敗：{docx_path}，錯誤：{e}")
        return ""


def read_pdf_text(pdf_path: Path) -> str:
    """
    讀取 PDF 文字，主要給系統分析與備用。
    UI 預覽 PDF 時會直接顯示 PDF 原始版面。
    """
    try:
        doc = fitz.open(pdf_path)
        pages = []

        for page_index, page in enumerate(doc, start=1):
            text = page.get_text("text").strip()

            if text:
                pages.append(f"--- Page {page_index} ---\n{text}")

        doc.close()

        return "\n\n".join(pages)

    except Exception as e:
        print(f"讀取 PDF 失敗：{pdf_path}，錯誤：{e}")
        return ""


def display_pdf_viewer(pdf_path: Path, height: int = 780):
    """
    直接在 Streamlit 裡顯示 PDF 原始版面。
    """
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")

        pdf_display = f"""
        <iframe
            src="data:application/pdf;base64,{base64_pdf}"
            width="100%"
            height="{height}"
            type="application/pdf"
            style="border: 1px solid #e5e7eb; border-radius: 12px;">
        </iframe>
        """

        st.markdown('<div class="pdf-box">', unsafe_allow_html=True)
        st.markdown(pdf_display, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    except Exception as e:
        st.error(f"PDF 預覽失敗：{e}")


def read_txt_or_md(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        try:
            return path.read_text(encoding="utf-8-sig", errors="ignore")
        except Exception:
            return ""


def read_report_text(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix == ".docx":
        return read_docx_text(path)

    if suffix == ".pdf":
        return read_pdf_text(path)

    if suffix in [".txt", ".md"]:
        return read_txt_or_md(path)

    return ""


def analyze_existing_report(text: str) -> dict:
    citation_count = text.count("[來源")

    section_count = sum(
        1 for sec in EXPECTED_SECTIONS
        if sec in text
    )

    missing_sections = [
        sec for sec in EXPECTED_SECTIONS
        if sec not in text
    ]

    suspicious_incomplete = False
    incomplete_markers = ["未完成", "待續", "以下內容省略", "產生失敗"]

    for marker in incomplete_markers:
        if marker in text:
            suspicious_incomplete = True

    return {
        "citation_count": citation_count,
        "has_citation": citation_count > 0,
        "section_count": section_count,
        "section_complete": len(missing_sections) == 0,
        "missing_sections": ";".join(missing_sections),
        "suspicious_incomplete": suspicious_incomplete,
        "char_count": len(text),
    }


def collect_report_files():
    patterns = [
        "patient_*_education_report*.docx",
        "patient_*_education_report*.pdf",
        "*.docx",
        "*.pdf",
        "*.txt",
        "*.md",
    ]

    files = []

    for folder in [REPORTS_DIR, UPLOAD_REPORTS_DIR]:
        if not folder.exists():
            continue

        for pattern in patterns:
            files.extend(folder.glob(pattern))

    unique = {}

    for p in files:
        unique[str(p.resolve())] = p

    return list(unique.values())


def auto_build_generation_csv_from_reports(
    limit: int = 100,
    latest_per_patient: bool = True,
) -> bool:
    report_files = sorted(
        collect_report_files(),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not report_files:
        return False

    selected_files = []

    if latest_per_patient:
        seen_subjects = set()

        for path in report_files:
            subject_id = extract_subject_id(path.name)

            if not subject_id:
                continue

            if subject_id in seen_subjects:
                continue

            selected_files.append(path)
            seen_subjects.add(subject_id)

            if len(selected_files) >= limit:
                break
    else:
        selected_files = report_files[:limit]

    rows = []

    for i, report_path in enumerate(selected_files, start=1):
        subject_id = extract_subject_id(report_path.name)
        text = read_report_text(report_path)

        md_path = OUTPUTS_DIR / f"{report_path.stem}.md"
        md_path.write_text(text, encoding="utf-8")

        analysis = analyze_existing_report(text)

        rows.append({
            "case_no": str(i),
            "subject_id": str(subject_id),
            "success": "True",
            "elapsed_seconds": "",
            "markdown_path": str(md_path),
            "docx_path": str(report_path),
            "citation_count": str(analysis["citation_count"]),
            "has_citation": str(analysis["has_citation"]),
            "section_count": str(analysis["section_count"]),
            "section_complete": str(analysis["section_complete"]),
            "missing_sections": analysis["missing_sections"],
            "suspicious_incomplete": str(analysis["suspicious_incomplete"]),
            "char_count": str(analysis["char_count"]),
            "error": "",
        })

    generation_df = pd.DataFrame(rows)
    generation_df.to_csv(GENERATION_CSV, index=False, encoding="utf-8-sig")

    return True


def ensure_generation_file():
    if GENERATION_CSV.exists():
        return

    ok = auto_build_generation_csv_from_reports(
        limit=100,
        latest_per_patient=True,
    )

    if not ok:
        st.error(
            "找不到評估報告。請先上傳報告，或確認 reports 資料夾中有 Word / PDF / TXT / Markdown 報告。"
        )
        st.stop()


def save_uploaded_reports(uploaded_files):
    saved_paths = []

    for uploaded_file in uploaded_files:
        filename = safe_filename(uploaded_file.name)
        out_path = UPLOAD_REPORTS_DIR / filename

        if out_path.exists():
            stem = out_path.stem
            suffix = out_path.suffix
            counter = 1

            while True:
                candidate = UPLOAD_REPORTS_DIR / f"{stem}_{counter}{suffix}"
                if not candidate.exists():
                    out_path = candidate
                    break
                counter += 1

        with open(out_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        reports_copy = REPORTS_DIR / out_path.name

        if not reports_copy.exists():
            shutil.copy2(out_path, reports_copy)

        saved_paths.append(out_path)

    auto_build_generation_csv_from_reports(
        limit=100,
        latest_per_patient=True,
    )

    return saved_paths


# =========================================================
# Reviewer 管理
# =========================================================
def list_reviewers():
    return [p.stem for p in sorted(REVIEWS_DIR.glob("*.csv"))]


def safe_reviewer_id(text: str) -> str:
    text = text.strip()
    text = text.replace(" ", "_")
    text = "".join(ch for ch in text if ch.isalnum() or ch in ["_", "-"])
    return text


def reviewer_path(reviewer_id: str) -> Path:
    return REVIEWS_DIR / f"{reviewer_id}.csv"


def load_generation_df():
    ensure_generation_file()

    df = pd.read_csv(GENERATION_CSV, encoding="utf-8-sig", dtype=str)
    df = df.fillna("")
    df["subject_id"] = df["subject_id"].astype(str)

    return df


def create_reviewer_file(reviewer_id: str):
    gen_df = load_generation_df()

    review_df = gen_df[[
        "case_no",
        "subject_id",
        "markdown_path",
        "docx_path",
        "success",
        "elapsed_seconds",
        "citation_count",
        "section_complete",
    ]].copy()

    review_df["retrieval_hit_0_1"] = ""
    review_df["hallucination_found_0_1"] = ""
    review_df["personalization_score_1_to_5"] = ""
    review_df["readability_score_1_to_5"] = ""
    review_df["citation_correct_0_1"] = ""
    review_df["overall_usefulness_1_to_5"] = ""
    review_df["reviewer_comments"] = ""
    review_df["reviewer_id"] = reviewer_id

    review_df = force_text_columns(review_df)

    out_path = reviewer_path(reviewer_id)
    review_df.to_csv(out_path, index=False, encoding="utf-8-sig")

    return out_path


def save_review_df(df, reviewer_id: str):
    """
    儲存 reviewer 評分結果。
    重要：強制評分欄位為文字，避免 pandas float64 型別錯誤。
    """
    df = df.copy()
    df = force_text_columns(df)
    df.to_csv(reviewer_path(reviewer_id), index=False, encoding="utf-8-sig")


def sync_reviewer_with_generation(
    review_df: pd.DataFrame,
    reviewer_id: str,
) -> pd.DataFrame:
    gen_df = load_generation_df()

    base_cols = [
        "case_no",
        "subject_id",
        "markdown_path",
        "docx_path",
        "success",
        "elapsed_seconds",
        "citation_count",
        "section_complete",
    ]

    review_df = force_text_columns(review_df)

    review_df["docx_path"] = review_df["docx_path"].astype(str)
    gen_df["docx_path"] = gen_df["docx_path"].astype(str)

    merged_rows = []

    for _, gen_row in gen_df.iterrows():
        docx_path = str(gen_row["docx_path"])
        old_match = review_df[review_df["docx_path"].astype(str) == docx_path]

        if not old_match.empty:
            old_row = old_match.iloc[0].to_dict()

            for col in base_cols:
                old_row[col] = gen_row.get(col, old_row.get(col, ""))

            old_row["reviewer_id"] = reviewer_id
            merged_rows.append(old_row)

        else:
            new_row = {col: gen_row.get(col, "") for col in base_cols}
            new_row["retrieval_hit_0_1"] = ""
            new_row["hallucination_found_0_1"] = ""
            new_row["personalization_score_1_to_5"] = ""
            new_row["readability_score_1_to_5"] = ""
            new_row["citation_correct_0_1"] = ""
            new_row["overall_usefulness_1_to_5"] = ""
            new_row["reviewer_comments"] = ""
            new_row["reviewer_id"] = reviewer_id
            merged_rows.append(new_row)

    synced_df = pd.DataFrame(merged_rows)

    for col in base_cols + ALL_REVIEW_COLS:
        if col not in synced_df.columns:
            synced_df[col] = ""

    synced_df = force_text_columns(synced_df)

    return synced_df


def load_review_df(reviewer_id: str):
    path = reviewer_path(reviewer_id)

    if not path.exists():
        create_reviewer_file(reviewer_id)

    df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    df = df.fillna("")
    df["subject_id"] = df["subject_id"].astype(str)

    df = force_text_columns(df)
    df = sync_reviewer_with_generation(df, reviewer_id)
    df = force_text_columns(df)

    save_review_df(df, reviewer_id)

    return df


# =========================================================
# 病人資料
# =========================================================
@st.cache_data
def load_patients():
    df = pd.read_csv(settings.ehr_csv, encoding="utf-8-sig", dtype=str)
    df = df.fillna("")
    df["subject_id"] = df["subject_id"].astype(str)
    return df


def get_patient_row(patients_df, subject_id):
    matched = patients_df[patients_df["subject_id"] == str(subject_id)]

    if matched.empty:
        return None

    return matched.iloc[0]


# =========================================================
# 評分與顯示工具
# =========================================================
def is_filled(value):
    if pd.isna(value):
        return False

    value = str(value).strip()

    if value == "":
        return False

    if value.lower() == "nan":
        return False

    return True


def is_reviewed(row):
    return all(is_filled(row.get(col, "")) for col in REQUIRED_REVIEW_COLS)


def read_markdown(path):
    if not is_filled(path):
        return ""

    p = Path(str(path))

    if not p.exists():
        return ""

    return p.read_text(encoding="utf-8", errors="ignore")


def option_from_value(value, yes_text="是", no_text="否"):
    if not is_filled(value):
        return "未評"

    value = str(value).strip()

    if value in ["1", "1.0", "True", "true", "YES", "yes", "相關", "有幻覺", "合理"]:
        return yes_text

    if value in ["0", "0.0", "False", "false", "NO", "no", "不相關", "無幻覺", "不合理"]:
        return no_text

    return "未評"


def value_from_option(option, yes_text="是", no_text="否"):
    if option == yes_text:
        return "1"

    if option == no_text:
        return "0"

    return ""


def score_from_value(value):
    if not is_filled(value):
        return "未評"

    value = str(value).strip()

    if value.endswith(".0"):
        value = value.replace(".0", "")

    if value in ["1", "2", "3", "4", "5"]:
        return value

    return "未評"


def value_from_score(score):
    if score == "未評":
        return ""

    return str(score)


# =========================================================
# 統計摘要
# =========================================================
def summarize_one_reviewer(df):
    work = df.copy()

    cols = REQUIRED_REVIEW_COLS + ["overall_usefulness_1_to_5"]

    for col in cols:
        work[col] = pd.to_numeric(work[col], errors="coerce")

    reviewed = work.dropna(subset=REQUIRED_REVIEW_COLS)

    if reviewed.empty:
        return None

    summary = {
        "reviewed_cases": len(reviewed),
        "total_cases": len(df),
        "retrieval_hit_rate": reviewed["retrieval_hit_0_1"].mean() * 100,
        "hallucination_rate": reviewed["hallucination_found_0_1"].mean() * 100,
        "personalization_score": reviewed["personalization_score_1_to_5"].mean(),
        "readability_score": reviewed["readability_score_1_to_5"].mean(),
        "citation_correct_rate": reviewed["citation_correct_0_1"].mean() * 100,
    }

    if reviewed["overall_usefulness_1_to_5"].notna().any():
        summary["overall_usefulness"] = reviewed["overall_usefulness_1_to_5"].mean()
    else:
        summary["overall_usefulness"] = None

    return summary


def aggregate_all_reviewers():
    files = sorted(REVIEWS_DIR.glob("*.csv"))

    if not files:
        return None

    dfs = []

    for path in files:
        df = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
        df = df.fillna("")
        df["reviewer_id"] = path.stem
        dfs.append(df)

    if not dfs:
        return None

    all_df = pd.concat(dfs, ignore_index=True)

    cols = REQUIRED_REVIEW_COLS + ["overall_usefulness_1_to_5"]

    for col in cols:
        if col not in all_df.columns:
            all_df[col] = ""
        all_df[col] = pd.to_numeric(all_df[col], errors="coerce")

    reviewed = all_df.dropna(subset=REQUIRED_REVIEW_COLS)

    if reviewed.empty:
        return None

    summary = {
        "reviewer_count": reviewed["reviewer_id"].nunique(),
        "reviewed_records": len(reviewed),
        "unique_cases_reviewed": reviewed["subject_id"].nunique(),
        "retrieval_hit_rate": reviewed["retrieval_hit_0_1"].mean() * 100,
        "hallucination_rate": reviewed["hallucination_found_0_1"].mean() * 100,
        "personalization_score": reviewed["personalization_score_1_to_5"].mean(),
        "readability_score": reviewed["readability_score_1_to_5"].mean(),
        "citation_correct_rate": reviewed["citation_correct_0_1"].mean() * 100,
    }

    if reviewed["overall_usefulness_1_to_5"].notna().any():
        summary["overall_usefulness"] = reviewed["overall_usefulness_1_to_5"].mean()
    else:
        summary["overall_usefulness"] = None

    lines = []
    lines.append("========== Multi-Reviewer Evaluation Summary ==========")
    lines.append(f"Reviewer count: {summary['reviewer_count']}")
    lines.append(f"Reviewed records: {summary['reviewed_records']}")
    lines.append(f"Unique cases reviewed: {summary['unique_cases_reviewed']}")
    lines.append(f"Retrieval Hit Rate@3: {summary['retrieval_hit_rate']:.2f}%")
    lines.append(f"Hallucination Rate: {summary['hallucination_rate']:.2f}%")
    lines.append(f"Personalization Score: {summary['personalization_score']:.2f} / 5")
    lines.append(f"Readability Score: {summary['readability_score']:.2f} / 5")
    lines.append(f"Citation Correctness: {summary['citation_correct_rate']:.2f}%")

    if summary["overall_usefulness"] is not None:
        lines.append(f"Overall Usefulness: {summary['overall_usefulness']:.2f} / 5")

    lines.append("=======================================================")

    HUMAN_SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")

    return summary


def set_current_index(index):
    st.session_state.current_index = int(index)


# =========================================================
# 初始化
# =========================================================
if "current_index" not in st.session_state:
    st.session_state.current_index = 0

if "reviewer_id" not in st.session_state:
    st.session_state.reviewer_id = ""


# =========================================================
# 標題
# =========================================================
st.markdown(
    """
    <div class="main-title">衛教報告人工評估系統</div>
    <div class="sub-title">
    可手動上傳報告，系統會自動儲存到本機，並依照 Subject ID 抓取 MIMIC 原始病人資料供評估對照。
    </div>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 上方控制區：上傳 + 掃描 + Reviewer
# =========================================================
st.markdown('<div class="top-box">', unsafe_allow_html=True)

upload_col, scan_col = st.columns([3, 1])

with upload_col:
    uploaded_files = st.file_uploader(
        "上傳要評估的報告，可一次上傳多份。支援 .docx / .pdf / .txt / .md",
        type=["docx", "pdf", "txt", "md"],
        accept_multiple_files=True,
    )

with scan_col:
    st.write("")
    st.write("")
    if st.button("儲存上傳並更新清單", use_container_width=True):
        if uploaded_files:
            saved = save_uploaded_reports(uploaded_files)
            st.success(f"已儲存 {len(saved)} 份報告到本機。")
            st.session_state.current_index = 0
            st.rerun()
        else:
            st.warning("請先選擇要上傳的報告。")

control_col1, control_col2, control_col3, control_col4 = st.columns([1.4, 2, 2, 1.2])

with control_col1:
    if st.button("重新掃描 reports", use_container_width=True):
        ok = auto_build_generation_csv_from_reports(
            limit=100,
            latest_per_patient=True,
        )

        if ok:
            st.success("已重新掃描 reports / uploaded_reports 並更新評估清單。")
            st.session_state.current_index = 0
            st.rerun()
        else:
            st.error("找不到可用報告。")

reviewers = list_reviewers()

with control_col2:
    if reviewers:
        selected_reviewer = st.selectbox(
            "選擇 Reviewer",
            reviewers,
            index=0 if st.session_state.reviewer_id not in reviewers else reviewers.index(st.session_state.reviewer_id),
        )
    else:
        selected_reviewer = ""

with control_col3:
    new_reviewer = st.text_input(
        "新增 Reviewer ID",
        placeholder="例如：R01、R02、nurse01",
    )

with control_col4:
    st.write("")
    st.write("")
    add_clicked = st.button("新增 / 使用", use_container_width=True)

if add_clicked:
    ensure_generation_file()

    new_id = safe_reviewer_id(new_reviewer)

    if not new_id:
        st.error("請輸入有效的 Reviewer ID。")
        st.stop()

    create_reviewer_file(new_id)
    st.session_state.reviewer_id = new_id
    st.session_state.current_index = 0
    st.success(f"已建立 / 切換至 Reviewer：{new_id}")
    st.rerun()

if reviewers and not st.session_state.reviewer_id:
    st.session_state.reviewer_id = selected_reviewer

if reviewers and selected_reviewer and selected_reviewer != st.session_state.reviewer_id:
    st.session_state.reviewer_id = selected_reviewer
    st.session_state.current_index = 0
    st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# 沒有 Reviewer 時停止
# =========================================================
ensure_generation_file()

if not st.session_state.reviewer_id:
    st.info("請先新增或選擇 Reviewer ID，例如 R01。")
    st.stop()


reviewer_id = st.session_state.reviewer_id

st.success(f"目前評分者：{reviewer_id}")


# =========================================================
# 載入資料
# =========================================================
review_df = load_review_df(reviewer_id)
patients_df = load_patients()

total_cases = len(review_df)

if total_cases == 0:
    st.error("目前沒有可評估的案例。")
    st.stop()

if st.session_state.current_index >= total_cases:
    st.session_state.current_index = total_cases - 1

if st.session_state.current_index < 0:
    st.session_state.current_index = 0


reviewed_count = sum(is_reviewed(row) for _, row in review_df.iterrows())
pending_count = total_cases - reviewed_count

st.markdown(
    f"""
    <span class="metric-pill">Reviewer：{reviewer_id}</span>
    <span class="metric-pill">總案例：{total_cases}</span>
    <span class="metric-pill">已評估：{reviewed_count}</span>
    <span class="metric-pill">未評估：{pending_count}</span>
    <span class="metric-pill">支援：DOCX / PDF / TXT / MD</span>
    <span class="metric-pill">上傳儲存位置：eval_results/uploaded_reports</span>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 主版面
# =========================================================
left_col, middle_col, right_col = st.columns([1.15, 2.7, 1.7])


# =========================================================
# 左側：案例清單
# =========================================================
with left_col:
    st.markdown("### 報告清單")

    for idx, row in review_df.iterrows():
        done = is_reviewed(row)
        status_class = "case-done" if done else "case-pending"
        status_text = "已評估" if done else "未評估"

        case_no = row.get("case_no", idx + 1)
        subject_id = row.get("subject_id", "")

        st.markdown(
            f"""
            <div class="case-card {status_class}">
                <b>Case {case_no}</b><br>
                Subject ID：{subject_id}<br>
                狀態：{status_text}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if st.button(
            f"查看 Case {case_no}",
            key=f"select_case_{reviewer_id}_{idx}",
            use_container_width=True,
        ):
            set_current_index(idx)
            st.rerun()


# =========================================================
# 目前案例
# =========================================================
current_index = st.session_state.current_index
current_row = review_df.iloc[current_index]
subject_id = str(current_row["subject_id"])

patient_row = get_patient_row(patients_df, subject_id)
markdown_text = read_markdown(current_row.get("markdown_path", ""))
report_path = current_row.get("docx_path", "")


# =========================================================
# 中間：病人資料與報告
# =========================================================
with middle_col:
    st.markdown(f"### Case {current_row.get('case_no', current_index + 1)}｜Subject ID：{subject_id}")

    if patient_row is not None:
        st.markdown('<div class="patient-box">', unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)

        with c1:
            st.metric("Subject ID", subject_id)

        with c2:
            st.metric("性別", patient_row.get("gender", ""))

        with c3:
            st.metric("年齡", patient_row.get("anchor_age", ""))

        st.markdown("**診斷名稱：**")
        st.write(patient_row.get("diagnoses", ""))

        st.markdown("**用藥紀錄：**")
        st.write(patient_row.get("prescriptions", ""))

        with st.expander("查看 ICD / 完整病人資料"):
            st.markdown("**ICD / 診斷碼：**")
            st.write(patient_row.get("icd10_codes", ""))

            st.markdown("**Medications：**")
            st.write(patient_row.get("medications", ""))

        st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning(
            "找不到此 Subject ID 的 MIMIC 病人資料。請確認報告檔名是否包含正確 subject_id。"
        )

    st.markdown("### 生成報告預覽")

    if is_filled(report_path) and Path(str(report_path)).exists():
        report_file = Path(str(report_path))
        suffix = report_file.suffix.lower()

        if suffix == ".pdf":
            display_pdf_viewer(report_file, height=780)

            with st.expander("查看 PDF 文字擷取內容"):
                if markdown_text.strip():
                    st.text(markdown_text)
                else:
                    st.warning("這份 PDF 可能是掃描圖片，無法直接擷取文字。")

        else:
            st.markdown('<div class="report-box">', unsafe_allow_html=True)

            if markdown_text.strip():
                st.markdown(markdown_text)
            else:
                st.warning("找不到報告預覽內容。")

            st.markdown("</div>", unsafe_allow_html=True)

    else:
        st.warning("找不到原始報告檔案，請重新上傳或重新掃描 reports。")

    if is_filled(report_path) and Path(str(report_path)).exists():
        suffix = Path(str(report_path)).suffix.lower()

        if suffix == ".pdf":
            mime_type = "application/pdf"
        elif suffix == ".docx":
            mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        elif suffix == ".txt":
            mime_type = "text/plain"
        else:
            mime_type = "text/markdown"

        with open(report_path, "rb") as f:
            st.download_button(
                label="下載這份報告",
                data=f,
                file_name=Path(str(report_path)).name,
                mime=mime_type,
                use_container_width=True,
            )


# =========================================================
# 右側：評估表單
# =========================================================
with right_col:
    st.markdown("### 人工評估")
    st.markdown('<div class="review-box">', unsafe_allow_html=True)

    st.caption("請對照中間的原始病人資料與生成報告進行評分。")

    retrieval_current = option_from_value(
        current_row.get("retrieval_hit_0_1", ""),
        yes_text="相關",
        no_text="不相關",
    )

    hallucination_current = option_from_value(
        current_row.get("hallucination_found_0_1", ""),
        yes_text="有幻覺",
        no_text="無幻覺",
    )

    citation_current = option_from_value(
        current_row.get("citation_correct_0_1", ""),
        yes_text="合理",
        no_text="不合理",
    )

    personalization_current = score_from_value(
        current_row.get("personalization_score_1_to_5", "")
    )

    readability_current = score_from_value(
        current_row.get("readability_score_1_to_5", "")
    )

    usefulness_current = score_from_value(
        current_row.get("overall_usefulness_1_to_5", "")
    )

    retrieval_hit = st.radio(
        "1. Retrieval Hit@3：檢索到的衛教單是否與病人診斷 / 用藥 / 照護需求相關？",
        ["未評", "相關", "不相關"],
        index=["未評", "相關", "不相關"].index(retrieval_current),
        key=f"retrieval_{reviewer_id}_{current_index}",
    )

    hallucination_found = st.radio(
        "2. Hallucination：報告是否出現原始資料或衛教單沒有支持的醫療內容？",
        ["未評", "有幻覺", "無幻覺"],
        index=["未評", "有幻覺", "無幻覺"].index(hallucination_current),
        key=f"hallucination_{reviewer_id}_{current_index}",
    )

    personalization_score = st.selectbox(
        "3. Personalization Score：是否有根據病人診斷與用藥個人化？",
        ["未評", "1", "2", "3", "4", "5"],
        index=["未評", "1", "2", "3", "4", "5"].index(personalization_current),
        key=f"personalization_{reviewer_id}_{current_index}",
    )

    readability_score = st.selectbox(
        "4. Readability Score：病人是否容易閱讀與理解？",
        ["未評", "1", "2", "3", "4", "5"],
        index=["未評", "1", "2", "3", "4", "5"].index(readability_current),
        key=f"readability_{reviewer_id}_{current_index}",
    )

    citation_correct = st.radio(
        "5. Citation Correctness：引用來源是否合理且可追溯？",
        ["未評", "合理", "不合理"],
        index=["未評", "合理", "不合理"].index(citation_current),
        key=f"citation_{reviewer_id}_{current_index}",
    )

    overall_usefulness = st.selectbox(
        "6. Overall Usefulness：整體臨床衛教實用性",
        ["未評", "1", "2", "3", "4", "5"],
        index=["未評", "1", "2", "3", "4", "5"].index(usefulness_current),
        key=f"usefulness_{reviewer_id}_{current_index}",
    )

    comments = st.text_area(
        "Reviewer Comments",
        value="" if not is_filled(current_row.get("reviewer_comments", "")) else str(current_row.get("reviewer_comments", "")),
        height=110,
        key=f"comments_{reviewer_id}_{current_index}",
    )

    st.markdown("</div>", unsafe_allow_html=True)

    save_col, next_col = st.columns(2)

    with save_col:
        save_clicked = st.button("儲存", type="secondary", use_container_width=True)

    with next_col:
        save_next_clicked = st.button("儲存並下一份", type="primary", use_container_width=True)

    prev_col, go_next_col = st.columns(2)

    with prev_col:
        if st.button("上一份", use_container_width=True):
            st.session_state.current_index = max(0, current_index - 1)
            st.rerun()

    with go_next_col:
        if st.button("下一份", use_container_width=True):
            st.session_state.current_index = min(total_cases - 1, current_index + 1)
            st.rerun()

    if save_clicked or save_next_clicked:
        missing_items = []

        if retrieval_hit == "未評":
            missing_items.append("Retrieval Hit@3")

        if hallucination_found == "未評":
            missing_items.append("Hallucination")

        if personalization_score == "未評":
            missing_items.append("Personalization Score")

        if readability_score == "未評":
            missing_items.append("Readability Score")

        if citation_correct == "未評":
            missing_items.append("Citation Correctness")

        if missing_items:
            st.warning(
                "還有必要評估項目尚未完成："
                + "、".join(missing_items)
                + "。請完成前 5 題後再儲存。"
            )

        else:
            review_df = force_text_columns(review_df)

            review_df.loc[current_index, "retrieval_hit_0_1"] = value_from_option(
                retrieval_hit,
                yes_text="相關",
                no_text="不相關",
            )

            review_df.loc[current_index, "hallucination_found_0_1"] = value_from_option(
                hallucination_found,
                yes_text="有幻覺",
                no_text="無幻覺",
            )

            review_df.loc[current_index, "personalization_score_1_to_5"] = value_from_score(
                personalization_score
            )

            review_df.loc[current_index, "readability_score_1_to_5"] = value_from_score(
                readability_score
            )

            review_df.loc[current_index, "citation_correct_0_1"] = value_from_option(
                citation_correct,
                yes_text="合理",
                no_text="不合理",
            )

            review_df.loc[current_index, "overall_usefulness_1_to_5"] = value_from_score(
                overall_usefulness
            )

            review_df.loc[current_index, "reviewer_comments"] = str(comments)
            review_df.loc[current_index, "reviewer_id"] = str(reviewer_id)

            review_df = force_text_columns(review_df)
            save_review_df(review_df, reviewer_id)

            if save_next_clicked:
                st.session_state.current_index = min(total_cases - 1, current_index + 1)
                st.success("已儲存，並切換到下一份。")
                st.rerun()
            else:
                st.success("評估結果已儲存。")
                st.rerun()


# =========================================================
# 底部摘要
# =========================================================
st.divider()

st.markdown("## 目前評估摘要")

summary = summarize_one_reviewer(review_df)

if summary is None:
    st.info("目前這位 reviewer 尚未完成任何一份完整評估。")
else:
    m1, m2, m3, m4, m5, m6 = st.columns(6)

    with m1:
        st.metric("Reviewed", f"{summary['reviewed_cases']} / {summary['total_cases']}")

    with m2:
        st.metric("Retrieval Hit@3", f"{summary['retrieval_hit_rate']:.1f}%")

    with m3:
        st.metric("Hallucination Rate", f"{summary['hallucination_rate']:.1f}%")

    with m4:
        st.metric("Personalization", f"{summary['personalization_score']:.2f} / 5")

    with m5:
        st.metric("Citation Correct", f"{summary['citation_correct_rate']:.1f}%")

    with m6:
        if summary["overall_usefulness"] is not None:
            st.metric("Usefulness", f"{summary['overall_usefulness']:.2f} / 5")
        else:
            st.metric("Usefulness", "N/A")


st.markdown("## 多位 Reviewer 彙整摘要")

aggregate_summary = aggregate_all_reviewers()

if aggregate_summary is None:
    st.info("尚未有可彙整的多人評分結果。")
else:
    a1, a2, a3, a4, a5, a6 = st.columns(6)

    with a1:
        st.metric("Reviewers", aggregate_summary["reviewer_count"])

    with a2:
        st.metric("Hit@3", f"{aggregate_summary['retrieval_hit_rate']:.1f}%")

    with a3:
        st.metric("Hallucination", f"{aggregate_summary['hallucination_rate']:.1f}%")

    with a4:
        st.metric("Personalization", f"{aggregate_summary['personalization_score']:.2f}/5")

    with a5:
        st.metric("Citation", f"{aggregate_summary['citation_correct_rate']:.1f}%")

    with a6:
        if aggregate_summary["overall_usefulness"] is not None:
            st.metric("Usefulness", f"{aggregate_summary['overall_usefulness']:.2f}/5")
        else:
            st.metric("Usefulness", "N/A")

    st.caption(f"多人評估摘要會同步輸出到：{HUMAN_SUMMARY_TXT}")

