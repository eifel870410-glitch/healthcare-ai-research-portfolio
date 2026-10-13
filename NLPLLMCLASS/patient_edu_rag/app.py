from __future__ import annotations
import argparse
from rich.console import Console
from rich.table import Table
from patient_edu_rag.pipeline import run_patient
from patient_edu_rag.config import settings
from patient_edu_rag.retriever import build_index

console = Console()


def cmd_index(args):
    n = build_index(settings.leaflets_dir, settings.chroma_dir, settings.collection_name, reset=args.reset)
    console.print(f"完成 向量索引完成，共 {n} 份衛教單。")


def cmd_generate(args):
    trace = run_patient(args.subject_id, use_ollama=not args.no_ollama)
    table = Table(title="檢索結果")
    table.add_column("Rank")
    table.add_column("Score")
    table.add_column("Title")
    table.add_column("Source")
    for h in trace["retrieved"]:
        table.add_row(str(h["rank"]), str(h["score"]), h["title"], h["source"])
    console.print(table)
    console.print("\n報告完成")
    console.print(f"Markdown：{trace['markdown_report']}")
    console.print(f"Word：{trace['word_report']}")
    console.print(f"引用檢查：{trace['validation']}")


def main():
    parser = argparse.ArgumentParser(description="Personalized Patient Education RAG System")
    sub = parser.add_subparsers(required=True)

    p_index = sub.add_parser("index", help="建立或更新衛教單向量索引")
    p_index.add_argument("--reset", action="store_true", help="重建索引")
    p_index.set_defaults(func=cmd_index)

    p_gen = sub.add_parser("generate", help="產生單一病人的個人化衛教報告")
    p_gen.add_argument("--subject-id", required=True, help="病人 subject_id")
    p_gen.add_argument("--no-ollama", action="store_true", help="不呼叫 LLaMA，使用檢索摘要 fallback")
    p_gen.set_defaults(func=cmd_generate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

