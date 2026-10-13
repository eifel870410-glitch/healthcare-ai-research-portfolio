import argparse
import csv
import json
import time
from pathlib import Path

import pandas as pd

from patient_edu_rag.config import settings
from patient_edu_rag.pipeline import run_patient


PROJECT_ROOT = Path(__file__).resolve().parent
EVAL_DIR = PROJECT_ROOT / "eval_results"
EVAL_DIR.mkdir(exist_ok=True)

GENERATION_CSV = EVAL_DIR / "generation_eval.csv"
HUMAN_REVIEW_CSV = EVAL_DIR / "human_review_template.csv"
SUMMARY_TXT = EVAL_DIR / "summary.txt"


EXPECTED_SECTIONS = [
    "病人狀況摘要",
    "主要衛教重點",
    "用藥與日常照護提醒",
    "需要回診或立即尋求協助的情況",
    "給病人的簡短提醒",
    "引用來源",
]


def latest_file(folder: Path, pattern: str):
    files = sorted(
        folder.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return files[0] if files else None


def read_text(path: Path):
    if not path or not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def analyze_report(markdown_text: str):
    """
    自動評估：
    1. 是否有引用
    2. 引用數量
    3. 是否有完整章節
    4. 是否有明顯未完成
    """

    citation_count = markdown_text.count("[來源")
    section_count = sum(1 for sec in EXPECTED_SECTIONS if sec in markdown_text)

    missing_sections = [
        sec for sec in EXPECTED_SECTIONS
        if sec not in markdown_text
    ]

    has_citation = citation_count > 0
    section_complete = len(missing_sections) == 0

    suspicious_incomplete = False
    incomplete_markers = [
        "未完成",
        "以下內容省略",
        "待續",
        "產生失敗",
    ]

    for marker in incomplete_markers:
        if marker in markdown_text:
            suspicious_incomplete = True

    word_count = len(markdown_text)

    return {
        "citation_count": citation_count,
        "has_citation": has_citation,
        "section_count": section_count,
        "section_complete": section_complete,
        "missing_sections": ";".join(missing_sections),
        "suspicious_incomplete": suspicious_incomplete,
        "char_count": word_count,
    }


def load_patients(limit: int):
    df = pd.read_csv(settings.ehr_csv)
    df["subject_id"] = df["subject_id"].astype(str)

    # 取前 limit 位有資料的病人
    df = df.head(limit)

    return df


def generate_reports(limit: int, use_ollama: bool = True):
    patients_df = load_patients(limit)

    rows = []

    print(f"準備產生 {len(patients_df)} 份報告")
    print(f"模型：{settings.ollama_model}")
    print(f"使用 Ollama：{use_ollama}")
    print()

    for idx, row in patients_df.iterrows():
        subject_id = str(row["subject_id"])

        print("=" * 60)
        print(f"[{idx + 1}/{len(patients_df)}] 產生 Subject ID：{subject_id}")
        print("=" * 60)

        start_time = time.time()

        success = False
        error = ""

        try:
            run_patient(subject_id, use_ollama=use_ollama)
            success = True

        except Exception as e:
            error = str(e)
            print(f"失敗：{error}")

        elapsed = time.time() - start_time

        md_path = latest_file(
            settings.output_dir,
            f"patient_{subject_id}_education_report*.md",
        )

        docx_path = latest_file(
            settings.report_dir,
            f"patient_{subject_id}_education_report*.docx",
        )

        markdown_text = read_text(md_path)
        analysis = analyze_report(markdown_text)

        rows.append({
            "case_no": idx + 1,
            "subject_id": subject_id,
            "success": success,
            "elapsed_seconds": round(elapsed, 2),
            "markdown_path": str(md_path) if md_path else "",
            "docx_path": str(docx_path) if docx_path else "",
            "citation_count": analysis["citation_count"],
            "has_citation": analysis["has_citation"],
            "section_count": analysis["section_count"],
            "section_complete": analysis["section_complete"],
            "missing_sections": analysis["missing_sections"],
            "suspicious_incomplete": analysis["suspicious_incomplete"],
            "char_count": analysis["char_count"],
            "error": error,
        })

        print(f"完成狀態：{success}")
        print(f"耗時：{elapsed:.2f} 秒")
        print(f"引用數量：{analysis['citation_count']}")
        print(f"章節完整：{analysis['section_complete']}")
        print()

    generation_df = pd.DataFrame(rows)
    generation_df.to_csv(GENERATION_CSV, index=False, encoding="utf-8-sig")

    create_human_review_template(generation_df)
    summarize_auto(generation_df)

    print()
    print("批次產生完成")
    print(f"自動評估結果：{GENERATION_CSV}")
    print(f"人工評估表：{HUMAN_REVIEW_CSV}")
    print(f"摘要：{SUMMARY_TXT}")


def create_human_review_template(generation_df: pd.DataFrame):
    """
    人工評估欄位：
    - retrieval_hit_0_1：前三個檢索來源是否至少一個相關
    - hallucination_found_0_1：是否有幻覺
    - personalization_score_1_to_5：個人化程度
    - readability_score_1_to_5：可讀性
    - citation_correct_0_1：引用是否合理
    """

    review_df = generation_df[[
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
    review_df["reviewer_comments"] = ""

    review_df.to_csv(HUMAN_REVIEW_CSV, index=False, encoding="utf-8-sig")


def summarize_auto(generation_df: pd.DataFrame):
    total = len(generation_df)

    if total == 0:
        return

    success_rate = generation_df["success"].mean() * 100
    successful = generation_df[generation_df["success"] == True]

    avg_time = successful["elapsed_seconds"].mean() if len(successful) else 0
    citation_coverage = successful["has_citation"].mean() * 100 if len(successful) else 0
    section_complete_rate = successful["section_complete"].mean() * 100 if len(successful) else 0
    avg_char_count = successful["char_count"].mean() if len(successful) else 0

    lines = []
    lines.append("========== Automatic Evaluation Summary ==========")
    lines.append(f"Total cases: {total}")
    lines.append(f"Generation success rate: {success_rate:.2f}%")
    lines.append(f"Average inference time: {avg_time:.2f} seconds")
    lines.append(f"Citation coverage: {citation_coverage:.2f}%")
    lines.append(f"Section completeness rate: {section_complete_rate:.2f}%")
    lines.append(f"Average report length: {avg_char_count:.2f} characters")
    lines.append("")
    lines.append("Manual review required for:")
    lines.append("- Retrieval Hit Rate")
    lines.append("- Hallucination Rate")
    lines.append("- Personalization Score")
    lines.append("- Readability Score")
    lines.append("- Citation Correctness")
    lines.append("==================================================")

    SUMMARY_TXT.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))


def summarize_human():
    if not HUMAN_REVIEW_CSV.exists():
        raise FileNotFoundError(f"找不到人工評估表：{HUMAN_REVIEW_CSV}")

    review_df = pd.read_csv(HUMAN_REVIEW_CSV)

    required_cols = [
        "retrieval_hit_0_1",
        "hallucination_found_0_1",
        "personalization_score_1_to_5",
        "readability_score_1_to_5",
        "citation_correct_0_1",
    ]

    for col in required_cols:
        if col not in review_df.columns:
            raise ValueError(f"人工評估表缺少欄位：{col}")

    valid_df = review_df.copy()

    for col in required_cols:
        valid_df[col] = pd.to_numeric(valid_df[col], errors="coerce")

    reviewed_df = valid_df.dropna(subset=required_cols)

    if reviewed_df.empty:
        print("目前人工評估欄位還沒填，無法計算人工評估指標。")
        return

    total_reviewed = len(reviewed_df)

    retrieval_hit_rate = reviewed_df["retrieval_hit_0_1"].mean() * 100
    hallucination_rate = reviewed_df["hallucination_found_0_1"].mean() * 100
    personalization_score = reviewed_df["personalization_score_1_to_5"].mean()
    readability_score = reviewed_df["readability_score_1_to_5"].mean()
    citation_correct_rate = reviewed_df["citation_correct_0_1"].mean() * 100

    lines = []
    lines.append("========== Human Evaluation Summary ==========")
    lines.append(f"Reviewed cases: {total_reviewed}")
    lines.append(f"Retrieval Hit Rate@3: {retrieval_hit_rate:.2f}%")
    lines.append(f"Hallucination Rate: {hallucination_rate:.2f}%")
    lines.append(f"Personalization Score: {personalization_score:.2f} / 5")
    lines.append(f"Readability Score: {readability_score:.2f} / 5")
    lines.append(f"Citation Correctness: {citation_correct_rate:.2f}%")
    lines.append("==============================================")

    human_summary_path = EVAL_DIR / "human_summary.txt"
    human_summary_path.write_text("\n".join(lines), encoding="utf-8")

    print("\n".join(lines))
    print(f"人工評估摘要已輸出：{human_summary_path}")


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "mode",
        choices=["generate", "summarize-human"],
        help="generate = 產生報告並做自動評估；summarize-human = 彙整人工評估結果",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="要產生幾份報告，預設 20",
    )

    parser.add_argument(
        "--no-ollama",
        action="store_true",
        help="不使用 LLaMA，只產生測試版報告",
    )

    args = parser.parse_args()

    if args.mode == "generate":
        generate_reports(
            limit=args.limit,
            use_ollama=not args.no_ollama,
        )

    elif args.mode == "summarize-human":
        summarize_human()


if __name__ == "__main__":
    main()
