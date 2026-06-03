from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from scripts import package_submission


def test_collect_submission_files_excludes_forbidden_paths() -> None:
    files = package_submission.collect_submission_files(package_submission.ROOT_DIR, include_optional=False)
    names = {path.relative_to(package_submission.ROOT_DIR).as_posix() for path in files}

    assert "app/data/restaurants.json" in names
    assert "README.md" in names
    assert "scripts/package_submission.py" in names
    assert ".env" not in names
    assert "app/data/place_cache.json" not in names
    assert not any("__pycache__" in name for name in names)
    assert not any("node_modules" in name for name in names)
    assert not any(name.endswith(".zip") for name in names)


def test_sensitive_scan_blocks_non_empty_api_keys(tmp_path: Path) -> None:
    key_name = "KAKAO_" + "REST_API_KEY"
    secret_file = tmp_path / "leaked.env.example"
    secret_file.write_text(f"{key_name}=real-secret-value\n", encoding="utf-8")

    with pytest.raises(package_submission.SensitiveInfoError):
        package_submission.scan_sensitive_info([secret_file], tmp_path)


def test_create_submission_zip_excludes_forbidden_files(tmp_path: Path) -> None:
    zip_path = package_submission.create_submission_zip(
        root_dir=package_submission.ROOT_DIR,
        output_dir=tmp_path,
        filename="test_submission.zip",
        include_optional=False,
    )

    with zipfile.ZipFile(zip_path) as archive:
        names = archive.namelist()

    package_submission.validate_zip_contents(names)
    assert "README.md" in names
    assert "docs/submission_checklist.md" in names
    assert "scripts/package_submission.py" in names
    assert "frontend/package.json" in names
    assert not any(name.startswith(".git/") for name in names)
    assert not any("node_modules" in name for name in names)
