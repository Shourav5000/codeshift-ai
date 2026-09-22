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


def _should_ignore(path: Path) -> bool:
    return any(
        part in IGNORED_DIRECTORIES
        for part in path.parts
    )


def _detect_languages(repo_path: Path) -> dict[str, int]:
    language_counts: Counter[str] = Counter()

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue

        if _should_ignore(file_path):
            continue

        language = EXTENSION_LANGUAGE_MAP.get(
            file_path.suffix.lower()
        )

        if language:
            language_counts[language] += 1

    return dict(language_counts.most_common())


def _detect_build_tools(repo_path: Path) -> list[str]:
    detected = []

    build_files = {
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

    for filename, tool in build_files.items():
        if (repo_path / filename).exists():
            detected.append(tool)

    return detected


def _detect_frameworks(repo_path: Path) -> list[str]:
    frameworks = set()

    pom_file = repo_path / "pom.xml"

    if pom_file.exists():
        content = pom_file.read_text(
            encoding="utf-8",
            errors="ignore",
        ).lower()

        if "spring-boot" in content:
            frameworks.add("Spring Boot")

    package_file = repo_path / "package.json"

    if package_file.exists():
        try:
            data = json.loads(
                package_file.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            )

            dependencies = {}
            dependencies.update(data.get("dependencies", {}))
            dependencies.update(data.get("devDependencies", {}))

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

        except json.JSONDecodeError:
            pass

    pyproject_file = repo_path / "pyproject.toml"
    requirements_file = repo_path / "requirements.txt"

    python_text = ""

    if pyproject_file.exists():
        python_text += pyproject_file.read_text(
            encoding="utf-8",
            errors="ignore",
        ).lower()

    if requirements_file.exists():
        python_text += requirements_file.read_text(
            encoding="utf-8",
            errors="ignore",
        ).lower()

    if "fastapi" in python_text:
        frameworks.add("FastAPI")

    if "django" in python_text:
        frameworks.add("Django")

    if "flask" in python_text:
        frameworks.add("Flask")

    return sorted(frameworks)


def _detect_java_version(repo_path: Path) -> str | None:
    pom_file = repo_path / "pom.xml"

    if not pom_file.exists():
        return None

    content = pom_file.read_text(
        encoding="utf-8",
        errors="ignore",
    )

    patterns = [
        r"<java\.version>(.*?)</java\.version>",
        r"<maven\.compiler\.source>(.*?)</maven\.compiler\.source>",
        r"<maven\.compiler\.target>(.*?)</maven\.compiler\.target>",
    ]

    for pattern in patterns:
        match = re.search(pattern, content)

        if match:
            return match.group(1).strip()

    return None


def _detect_tests(repo_path: Path) -> bool:
    test_paths = [
        "test",
        "tests",
        "src/test",
        "__tests__",
    ]

    for test_path in test_paths:
        if (repo_path / test_path).exists():
            return True

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue

        if _should_ignore(file_path):
            continue

        name = file_path.name.lower()

        if (
            name.startswith("test_")
            or name.endswith("_test.py")
            or name.endswith("test.java")
            or name.endswith(".spec.ts")
            or name.endswith(".test.ts")
            or name.endswith(".test.js")
        ):
            return True

    return False


def _count_files(repo_path: Path) -> int:
    count = 0

    for file_path in repo_path.rglob("*"):
        if not file_path.is_file():
            continue

        if _should_ignore(file_path):
            continue

        count += 1

    return count


def scan_repository(repo_path: Path) -> dict:
    languages = _detect_languages(repo_path)

    primary_language = (
        next(iter(languages))
        if languages
        else None
    )

    return {
        "primary_language": primary_language,
        "languages": languages,
        "frameworks": _detect_frameworks(repo_path),
        "build_tools": _detect_build_tools(repo_path),
        "java_version": _detect_java_version(repo_path),
        "has_tests": _detect_tests(repo_path),
        "files_analyzed": _count_files(repo_path),
    }