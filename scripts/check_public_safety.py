"""Fail when staged or tracked files look unsafe for a public portfolio."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys


MAX_FILE_SIZE = 10 * 1024 * 1024

FORBIDDEN_PARTS = {
    ".venv",
    "venv",
    "__pycache__",
    "data",
    "datasets",
    "raw_dicom",
    "chroma_db",
    "runs",
    "outputs",
    "reports",
    "eval_results",
    "health_education",
    "pytest",
}

FORBIDDEN_SUFFIXES = {
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
    ".pdf",
    ".xls",
    ".xlsx",
    ".csv",
    ".tsv",
    ".db",
    ".duckdb",
    ".sqlite",
    ".sqlite3",
    ".dcm",
    ".dicom",
    ".nii",
    ".npy",
    ".npz",
    ".pt",
    ".pth",
    ".onnx",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".tif",
    ".tiff",
    ".bmp",
    ".mp4",
    ".mov",
    ".avi",
    ".zip",
    ".7z",
}

FORBIDDEN_NAME_FRAGMENTS = {
    "個人資料",
    "在學證明",
    "個案報告",
    "核准函",
    "身分證",
    "身份證",
}

SECRET_PATTERNS = {
    "private key": re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "GitHub token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "student number": re.compile(r"\bG\d{9}\b", re.IGNORECASE),
    "Taiwan national ID pattern": re.compile(r"\b[A-Z][12]\d{8}\b"),
    "password assignment": re.compile(
        r"(?im)^\s*(?:password|passwd|pwd)\s*[:=]\s*[^\s#]{4,}"
    ),
}


def git_paths(all_tracked: bool) -> list[Path]:
    command = (
        ["git", "ls-files", "-z"]
        if all_tracked
        else ["git", "diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR"]
    )
    result = subprocess.run(command, check=True, capture_output=True)
    return [Path(item.decode("utf-8")) for item in result.stdout.split(b"\0") if item]


def suffix_of(path: Path) -> str:
    if path.name.lower().endswith(".nii.gz"):
        return ".nii"
    return path.suffix.lower()


def inspect(path: Path) -> list[str]:
    issues: list[str] = []
    lowered_parts = {part.lower() for part in path.parts}

    blocked_parts = lowered_parts.intersection(FORBIDDEN_PARTS)
    if blocked_parts:
        issues.append("forbidden directory: " + ", ".join(sorted(blocked_parts)))

    if any("irb" in part for part in lowered_parts):
        issues.append("IRB-related path")

    if suffix_of(path) in FORBIDDEN_SUFFIXES:
        issues.append(f"forbidden file type: {path.suffix or path.name}")

    if any(fragment.lower() in path.name.lower() for fragment in FORBIDDEN_NAME_FRAGMENTS):
        issues.append("sensitive filename")

    if path.name == ".env" or (
        path.name.startswith(".env.") and path.name != ".env.example"
    ):
        issues.append("environment secret file")

    if not path.exists() or not path.is_file():
        return issues

    if path.stat().st_size > MAX_FILE_SIZE:
        issues.append(f"file exceeds {MAX_FILE_SIZE // (1024 * 1024)} MiB")

    if path.stat().st_size <= 2 * 1024 * 1024:
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            text = ""
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                issues.append(f"possible {label}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--all",
        action="store_true",
        help="scan every tracked file instead of only staged additions and changes",
    )
    args = parser.parse_args()

    try:
        paths = git_paths(args.all)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"Unable to read Git file list: {exc}", file=sys.stderr)
        return 2

    failures: list[tuple[Path, list[str]]] = []
    for path in paths:
        issues = inspect(path)
        if issues:
            failures.append((path, issues))

    if failures:
        print("Public-safety check failed:\n")
        for path, issues in failures:
            print(f"- {path}: {'; '.join(issues)}")
        print("\nRemove the file from the index and review it before publication.")
        return 1

    scope = "tracked" if args.all else "staged"
    print(f"Public-safety check passed for {len(paths)} {scope} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

