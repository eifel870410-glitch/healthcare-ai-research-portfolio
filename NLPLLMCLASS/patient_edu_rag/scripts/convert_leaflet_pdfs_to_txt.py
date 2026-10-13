from pathlib import Path
import os
import fitz  # PyMuPDF


PROJECT_ROOT = Path(__file__).resolve().parents[1]

# 私人 PDF 來源不放進 Git。可用環境變數指定本機授權資料夾。
PDF_DIR = Path(
    os.environ.get(
        "PATIENT_EDU_PDF_DIR",
        PROJECT_ROOT / "private_source" / "health_education",
    )
)

# 轉出 TXT 的目標資料夾，也就是 RAG 會讀取的地方
TXT_DIR = PROJECT_ROOT / "data" / "leaflets"
TXT_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(text: str) -> str:
    text = text.replace("\x00", "")
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def pdf_to_text(pdf_path: Path) -> str:
    parts = []

    with fitz.open(pdf_path) as doc:
        for page_num, page in enumerate(doc, start=1):
            text = page.get_text("text")
            text = clean_text(text)

            if text:
                parts.append(f"\n--- Page {page_num} ---\n{text}")

    return "\n".join(parts).strip()


def main():
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"找不到 PDF：{PDF_DIR}")
        return

    success = 0
    empty = 0
    failed = 0

    print(f"找到 {len(pdf_files)} 份 PDF，開始轉成 TXT...")

    for pdf_path in pdf_files:
        try:
            text = pdf_to_text(pdf_path)

            if not text:
                empty += 1
                print(f"[空白或可能是掃描檔] {pdf_path.name}")
                continue

            txt_name = pdf_path.stem + ".txt"
            out_path = TXT_DIR / txt_name

            header = (
                f"Title: {pdf_path.stem}\n"
                f"Source: {pdf_path.name}\n"
                f"Type: Hospital Approved Leaflet\n\n"
            )

            out_path.write_text(header + text, encoding="utf-8")
            success += 1
            print(f"[完成] {pdf_path.name} -> {out_path.name}")

        except Exception as e:
            failed += 1
            print(f"[失敗] {pdf_path.name}: {e}")

    print()
    print("轉換完成")
    print(f"成功：{success}")
    print(f"空白或掃描檔：{empty}")
    print(f"失敗：{failed}")
    print(f"TXT 輸出資料夾：{TXT_DIR}")


if __name__ == "__main__":
    main()

