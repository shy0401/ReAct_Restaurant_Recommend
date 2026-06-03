from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path
from typing import Iterable


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_FILENAME = "신하윤_202112026_실습4.zip"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "submission_outputs"

REQUIRED_INCLUDE_ENTRIES = [
    "app",
    "mcp_servers",
    "frontend/src",
    "frontend/public",
    "frontend/index.html",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/scripts",
    "frontend/.env.example",
    "ui",
    "scripts/run_submission_scenario.py",
    "scripts/package_submission.py",
    "tests",
    "README.md",
    "requirements.txt",
    ".env.example",
    "docs",
]

OPTIONAL_INCLUDE_ENTRIES = [
    "frontend/postcss.config.js",
    "frontend/tailwind.config.js",
    "frontend/vite.config.js",
    "frontend/vite.config.mjs",
    "submission_outputs/실행로그_trace.txt",
    "submission_outputs/실행로그_trace.json",
    "submission_outputs/과제_실행_요약.md",
]

EXCLUDED_DIR_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
}

EXCLUDED_FILE_NAMES = {
    ".env",
    "place_cache.json",
    "meal_history.json",
}

EXCLUDED_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".zip",
}

TEXT_SUFFIXES = {
    ".py",
    ".js",
    ".jsx",
    ".mjs",
    ".json",
    ".md",
    ".txt",
    ".html",
    ".css",
    ".env",
    ".example",
    ".toml",
    ".yaml",
    ".yml",
}


class SensitiveInfoError(RuntimeError):
    pass


def collect_submission_files(root_dir: Path = ROOT_DIR, *, include_optional: bool = True) -> list[Path]:
    entries = list(REQUIRED_INCLUDE_ENTRIES)
    if include_optional:
        entries.extend(OPTIONAL_INCLUDE_ENTRIES)

    files: dict[str, Path] = {}
    for entry in entries:
        path = root_dir / entry
        if not path.exists():
            continue
        if path.is_dir():
            for child in path.rglob("*"):
                if child.is_file() and _is_allowed_file(child, root_dir):
                    files[child.relative_to(root_dir).as_posix()] = child
        elif _is_allowed_file(path, root_dir):
            files[path.relative_to(root_dir).as_posix()] = path
    return [files[key] for key in sorted(files)]


def scan_sensitive_info(files: Iterable[Path], root_dir: Path = ROOT_DIR) -> None:
    findings: list[str] = []
    openai_pattern = re.compile(r"OPENAI_API_KEY[ \t]*=[ \t]*sk-[A-Za-z0-9_\-]+")
    key_assignment_pattern = re.compile(
        r"^(KAKAO_REST_API_KEY|NAVER_CLIENT_SECRET|GOOGLE_PLACES_API_KEY)[ \t]*=[ \t]*(.*)$",
        re.MULTILINE,
    )

    for path in files:
        if not _looks_text(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = path.read_text(encoding="utf-8", errors="ignore")

        if openai_pattern.search(text):
            findings.append(f"{_rel(path, root_dir)}: OPENAI_API_KEY가 sk- 형태로 설정되어 있습니다.")

        for match in key_assignment_pattern.finditer(text):
            key_name = match.group(1)
            value = match.group(2).strip().strip('"').strip("'")
            if value and not _is_safe_placeholder(value):
                findings.append(f"{_rel(path, root_dir)}: {key_name} 값이 비어 있지 않습니다.")

    if findings:
        message = "민감정보가 발견되어 zip 생성을 중단합니다.\n" + "\n".join(f"- {item}" for item in findings)
        raise SensitiveInfoError(message)


def create_submission_zip(
    *,
    root_dir: Path = ROOT_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    filename: str = DEFAULT_FILENAME,
    include_optional: bool = True,
) -> Path:
    files = collect_submission_files(root_dir, include_optional=include_optional)
    scan_sensitive_info(files, root_dir)

    output_dir.mkdir(parents=True, exist_ok=True)
    zip_path = output_dir / filename
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=path.relative_to(root_dir).as_posix())
    return zip_path


def list_zip_contents(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as archive:
        return archive.namelist()


def validate_zip_contents(names: Iterable[str]) -> None:
    forbidden_parts = {
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".pytest_cache",
        "node_modules",
        "dist",
        "build",
    }
    forbidden_names = {".env", "place_cache.json", "meal_history.json"}
    violations: list[str] = []
    for name in names:
        parts = set(Path(name).parts)
        if parts & forbidden_parts:
            violations.append(name)
        if Path(name).name in forbidden_names:
            violations.append(name)
        if name.endswith(".zip"):
            violations.append(name)
    if violations:
        joined = "\n".join(f"- {item}" for item in sorted(set(violations)))
        raise RuntimeError(f"금지 파일이 zip에 포함되었습니다.\n{joined}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="과제 제출용 zip 파일을 생성합니다.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="zip 파일을 생성할 디렉터리")
    parser.add_argument("--filename", default=DEFAULT_FILENAME, help="생성할 zip 파일명")
    parser.add_argument("--no-trace", action="store_true", help="submission_outputs의 실행 로그를 포함하지 않습니다.")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = ROOT_DIR / output_dir

    try:
        zip_path = create_submission_zip(
            root_dir=ROOT_DIR,
            output_dir=output_dir,
            filename=args.filename,
            include_optional=not args.no_trace,
        )
        contents = list_zip_contents(zip_path)
        validate_zip_contents(contents)
    except SensitiveInfoError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"zip 생성 실패: {exc}", file=sys.stderr)
        return 1

    print(f"제출 zip 생성 완료: {zip_path}")
    print(f"포함 파일 수: {len(contents)}")
    print("zip 내부 목록:")
    for name in contents:
        print(f"- {name}")
    return 0


def _is_allowed_file(path: Path, root_dir: Path) -> bool:
    relative = path.relative_to(root_dir)
    parts = set(relative.parts)
    if parts & EXCLUDED_DIR_NAMES:
        return False
    if path.name in EXCLUDED_FILE_NAMES:
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def _looks_text(path: Path) -> bool:
    if path.name.endswith(".env.example"):
        return True
    return path.suffix.lower() in TEXT_SUFFIXES


def _is_safe_placeholder(value: str) -> bool:
    lowered = value.lower()
    placeholder_tokens = ["your_", "example", "placeholder", "발급", "입력", "<", ">"]
    return any(token in lowered or token in value for token in placeholder_tokens)


def _rel(path: Path, root_dir: Path) -> str:
    try:
        return path.relative_to(root_dir).as_posix()
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
