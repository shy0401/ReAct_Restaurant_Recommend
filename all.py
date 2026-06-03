from __future__ import annotations

import os
from pathlib import Path


EXCLUDE_DIRS = {
    ".git",
    ".idea",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    "submission_outputs",
}

TARGET_EXTENSIONS = (
    ".py",
    ".js",
    ".jsx",
    ".mjs",
    ".ts",
    ".html",
    ".css",
    ".json",
    ".md",
    ".txt",
    ".example",
    ".env.example",
)

EXCLUDE_FILES = {".env", "project_combined.txt"}


def merge_code_efficient(root_dir: str, output_file: str, chunk_size: int = 1024 * 1024) -> None:
    root_path = Path(root_dir).resolve()
    output_path = Path(output_file).resolve()

    with output_path.open("w", encoding="utf-8") as outfile:
        outfile.write("# PROJECT DIRECTORY STRUCTURE\n```text\n")
        for root, dirs, files in os.walk(root_path):
            dirs[:] = [directory for directory in dirs if directory not in EXCLUDE_DIRS and not directory.startswith(".")]
            root_obj = Path(root)
            level = len(root_obj.relative_to(root_path).parts)
            indent = "    " * level
            if root_obj != root_path:
                outfile.write(f"{indent}- {root_obj.name}/\n")
            for file_name in files:
                if _should_include(file_name):
                    outfile.write(f"{indent}    - {file_name}\n")
        outfile.write("```\n\n" + "=" * 50 + "\n\n")

        for root, dirs, files in os.walk(root_path):
            dirs[:] = [directory for directory in dirs if directory not in EXCLUDE_DIRS and not directory.startswith(".")]
            for file_name in files:
                if not _should_include(file_name):
                    continue
                file_path = Path(root) / file_name
                if file_path.resolve() == output_path:
                    continue
                rel_path = file_path.relative_to(root_path)
                extension = file_path.suffix.lstrip(".") or "text"
                outfile.write(f"## File: {rel_path}\n```{extension}\n")
                try:
                    with file_path.open("r", encoding="utf-8", errors="ignore") as infile:
                        while chunk := infile.read(chunk_size):
                            outfile.write(chunk)
                except Exception as exc:
                    outfile.write(f"// [Error reading file: {exc}]\n")
                outfile.write("\n```\n\n")

    print(f"프로젝트 병합 완료: {output_file}")


def _should_include(file_name: str) -> bool:
    if file_name in EXCLUDE_FILES:
        return False
    if file_name == ".env":
        return False
    return file_name.endswith(TARGET_EXTENSIONS)


if __name__ == "__main__":
    merge_code_efficient("./", "project_combined.txt")
