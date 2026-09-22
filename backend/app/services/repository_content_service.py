from __future__ import annotations

from pathlib import Path


IMPORTANT_FILE_NAMES = {
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "settings.gradle",
    "settings.gradle.kts",
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "pyproject.toml",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
}

IMPORTANT_SUFFIXES = {
    ".java",
    ".kt",
    ".kts",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".xml",
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".properties",
}

IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    ".venv",
    "venv",
    "node_modules",
    "target",
    "build",
    "dist",
    "__pycache__",
}

MAX_CONTENT_FILES = 40
MAX_CHARS_PER_FILE = 12_000
MAX_TOTAL_CHARS = 120_000

# A complete path inventory is useful for proving that a proposed
# create operation does not overwrite an existing repository file.
MAX_INVENTORY_PATHS = 10_000


def _is_ignored_path(
    relative_path: Path,
) -> bool:

    return any(
        part in IGNORED_DIRECTORIES
        for part in relative_path.parts
    )


def _is_important_file(
    path: Path,
) -> bool:

    if path.name in IMPORTANT_FILE_NAMES:
        return True

    return path.suffix.lower() in IMPORTANT_SUFFIXES


def _safe_relative_path(
    repo_root: Path,
    file_path: Path,
) -> str | None:

    try:
        resolved_file = file_path.resolve()
        resolved_root = repo_root.resolve()

        relative = resolved_file.relative_to(
            resolved_root
        )

        return relative.as_posix()

    except (
        OSError,
        ValueError,
    ):
        return None


def collect_repository_files(
    repo_path: Path,
) -> dict:

    repo_root = repo_path.resolve()

    selected_files = []
    all_paths = []

    total_chars = 0
    inventory_complete = True

    try:
        candidates = sorted(
            path
            for path in repo_root.rglob("*")
            if path.is_file()
        )

    except OSError:
        candidates = []
        inventory_complete = False

    for path in candidates:

        relative_string = _safe_relative_path(
            repo_root,
            path,
        )

        if relative_string is None:
            continue

        relative_path = Path(
            relative_string
        )

        if _is_ignored_path(
            relative_path
        ):
            continue

        if len(
            all_paths
        ) < MAX_INVENTORY_PATHS:
            all_paths.append(
                relative_string
            )

        else:
            inventory_complete = False

        if len(
            selected_files
        ) >= MAX_CONTENT_FILES:
            continue

        if not _is_important_file(
            path
        ):
            continue

        try:
            content = path.read_text(
                encoding="utf-8"
            )

        except (
            UnicodeDecodeError,
            OSError,
        ):
            continue

        truncated = False

        if len(
            content
        ) > MAX_CHARS_PER_FILE:

            content = content[
                :MAX_CHARS_PER_FILE
            ]

            truncated = True

        remaining_budget = (
            MAX_TOTAL_CHARS
            - total_chars
        )

        if remaining_budget <= 0:
            break

        if len(
            content
        ) > remaining_budget:

            content = content[
                :remaining_budget
            ]

            truncated = True

        selected_files.append(
            {
                "path": relative_string,
                "content": content,
                "truncated": truncated,
            }
        )

        total_chars += len(
            content
        )

    return {
        "file_count": len(
            selected_files
        ),
        "total_chars": total_chars,
        "files": selected_files,
        "all_paths": all_paths,
        "inventory_count": len(
            all_paths
        ),
        "inventory_complete": (
            inventory_complete
        ),
    }