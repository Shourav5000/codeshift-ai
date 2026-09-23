from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


EXTENSION_LANGUAGE_MAP = {
    ".py": "Python",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".go": "Go",
    ".rs": "Rust",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".kt": "Kotlin",
}


IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".next",
}


BUILD_FILES = {
    "pom.xml": "Maven",
    "build.gradle": "Gradle",
    "build.gradle.kts": "Gradle",
    "package.json": "npm",
    "pyproject.toml": "Python pyproject",
    "requirements.txt": "pip",
    "Pipfile": "Pipenv",
    "go.mod": "Go Modules",
    "Cargo.toml": "Cargo",
}


def _relative_path(
    path: Path,
    repo_path: Path,
) -> Path:
    try:
        return path.relative_to(repo_path)
    except ValueError:
        return path


def _should_ignore(
    path: Path,
    repo_path: Path | None = None,
) -> bool:
    candidate = (
        _relative_path(path, repo_path)
        if repo_path is not None
        else path
    )

    return any(
        part in IGNORED_DIRECTORIES
        for part in candidate.parts
    )


def _find_files(
    repo_path: Path,
    filename: str,
) -> list[Path]:
    files = [
        path
        for path in repo_path.rglob(filename)
        if path.is_file()
        and not _should_ignore(
            path,
            repo_path,
        )
    ]

    return sorted(
        files,
        key=lambda path: (
            len(
                _relative_path(
                    path,
                    repo_path,
                ).parts
            ),
            _relative_path(
                path,
                repo_path,
            ).as_posix(),
        ),
    )


def _detect_languages(
    repo_path: Path,
) -> dict[str, int]:
    language_counts: Counter[str] = Counter()

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue

        if _should_ignore(
            file_path,
            repo_path,
        ):
            continue

        language = EXTENSION_LANGUAGE_MAP.get(
            file_path.suffix.lower()
        )

        if language:
            language_counts[
                language
            ] += 1

    return dict(
        language_counts.most_common()
    )


def _detect_build_tools(
    repo_path: Path,
) -> list[str]:
    detected: list[str] = []

    for filename, tool in BUILD_FILES.items():
        if (
            _find_files(
                repo_path,
                filename,
            )
            and tool not in detected
        ):
            detected.append(tool)

    return detected


def _detect_frameworks(
    repo_path: Path,
) -> list[str]:
    frameworks: set[str] = set()

    java_build_files = (
        _find_files(
            repo_path,
            "pom.xml",
        )
        + _find_files(
            repo_path,
            "build.gradle",
        )
        + _find_files(
            repo_path,
            "build.gradle.kts",
        )
    )

    for build_file in java_build_files:
        content = build_file.read_text(
            encoding="utf-8",
            errors="ignore",
        ).lower()

        if "spring-boot" in content:
            frameworks.add(
                "Spring Boot"
            )

    for package_file in _find_files(
        repo_path,
        "package.json",
    ):
        try:
            data = json.loads(
                package_file.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )
        except json.JSONDecodeError:
            continue

        dependencies: dict = {}

        for group in (
            "dependencies",
            "devDependencies",
            "peerDependencies",
        ):
            value = data.get(
                group,
                {},
            )

            if isinstance(
                value,
                dict,
            ):
                dependencies.update(
                    value
                )

        if "react" in dependencies:
            frameworks.add("React")

        if "next" in dependencies:
            frameworks.add("Next.js")

        if "vue" in dependencies:
            frameworks.add("Vue")

        if "@angular/core" in dependencies:
            frameworks.add("Angular")

        if "vite" in dependencies:
            frameworks.add("Vite")

        if "express" in dependencies:
            frameworks.add("Express")

    python_text_parts: list[str] = []

    for filename in (
        "pyproject.toml",
        "requirements.txt",
    ):
        for manifest in _find_files(
            repo_path,
            filename,
        ):
            python_text_parts.append(
                manifest.read_text(
                    encoding="utf-8",
                    errors="ignore",
                ).lower()
            )

    python_text = "\n".join(
        python_text_parts
    )

    if "fastapi" in python_text:
        frameworks.add("FastAPI")

    if "django" in python_text:
        frameworks.add("Django")

    if "flask" in python_text:
        frameworks.add("Flask")

    return sorted(
        frameworks
    )


def _version_sort_key(
    value: str,
) -> tuple:
    pieces = re.findall(
        r"\d+|[A-Za-z]+",
        value,
    )

    normalized = []

    for piece in pieces:
        if piece.isdigit():
            normalized.append(
                (
                    0,
                    int(piece),
                )
            )
        else:
            normalized.append(
                (
                    1,
                    piece.lower(),
                )
            )

    return tuple(
        normalized
    )


def _detect_java_version(
    repo_path: Path,
) -> str | None:
    versions: list[str] = []

    pom_patterns = [
        r"<java\.version>\s*([^<]+?)\s*</java\.version>",
        r"<maven\.compiler\.source>\s*([^<]+?)\s*</maven\.compiler\.source>",
        r"<maven\.compiler\.target>\s*([^<]+?)\s*</maven\.compiler\.target>",
    ]

    for pom_file in _find_files(
        repo_path,
        "pom.xml",
    ):
        content = pom_file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        for pattern in pom_patterns:
            match = re.search(
                pattern,
                content,
            )

            if match:
                value = (
                    match.group(1)
                    .strip()
                )

                if value:
                    versions.append(
                        value
                    )

                break

    gradle_patterns = [
        r"JavaLanguageVersion\.of\(\s*(\d+)\s*\)",
        r"(?:sourceCompatibility|targetCompatibility)\s*=\s*(?:JavaVersion\.VERSION_)?['\"]?(\d+)['\"]?",
    ]

    gradle_files = (
        _find_files(
            repo_path,
            "build.gradle",
        )
        + _find_files(
            repo_path,
            "build.gradle.kts",
        )
    )

    for gradle_file in gradle_files:
        content = gradle_file.read_text(
            encoding="utf-8",
            errors="ignore",
        )

        for pattern in gradle_patterns:
            match = re.search(
                pattern,
                content,
            )

            if match:
                value = (
                    match.group(1)
                    .strip()
                )

                if value:
                    versions.append(
                        value
                    )

                break

    unique_versions = sorted(
        set(versions),
        key=_version_sort_key,
    )

    if not unique_versions:
        return None

    return ", ".join(
        unique_versions
    )


def _detect_tests(
    repo_path: Path,
) -> bool:
    test_paths = [
        "test",
        "tests",
        "src/test",
        "__tests__",
    ]

    for test_path in test_paths:
        if (
            repo_path
            / test_path
        ).exists():
            return True

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue

        if _should_ignore(
            file_path,
            repo_path,
        ):
            continue

        relative_parts = {
            part.lower()
            for part in _relative_path(
                file_path,
                repo_path,
            ).parts
        }

        if (
            "src" in relative_parts
            and "test" in relative_parts
        ):
            return True

        name = file_path.name.lower()

        if (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith("test.java")
            or name.endswith("test.kt")
            or name.endswith(".spec.ts")
            or name.endswith(".test.ts")
            or name.endswith(".test.js")
        ):
            return True

    return False


def _count_files(
    repo_path: Path,
) -> int:
    count = 0

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue

        if _should_ignore(
            file_path,
            repo_path,
        ):
            continue

        count += 1

    return count


def scan_repository(
    repo_path: Path,
) -> dict:
    languages = _detect_languages(
        repo_path
    )

    primary_language = (
        next(iter(languages))
        if languages
        else None
    )

    return {
        "primary_language": (
            primary_language
        ),
        "languages": languages,
        "frameworks": (
            _detect_frameworks(
                repo_path
            )
        ),
        "build_tools": (
            _detect_build_tools(
                repo_path
            )
        ),
        "java_version": (
            _detect_java_version(
                repo_path
            )
        ),
        "has_tests": (
            _detect_tests(
                repo_path
            )
        ),
        "files_analyzed": (
            _count_files(
                repo_path
            )
        ),
    }
