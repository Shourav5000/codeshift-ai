from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


TEST_TIMEOUT_SECONDS = 300
MAX_PROJECTS_TO_TEST = 8

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


def _relative_path(
    path: Path,
    repo_path: Path,
) -> str:
    try:
        relative = path.relative_to(
            repo_path
        )
    except ValueError:
        return str(path)

    value = relative.as_posix()

    return value or "."


def _should_ignore(
    path: Path,
    repo_path: Path,
) -> bool:
    try:
        relative = path.relative_to(
            repo_path
        )
    except ValueError:
        relative = path

    return any(
        part in IGNORED_DIRECTORIES
        for part in relative.parts
    )


def _find_project_roots(
    repo_path: Path,
    filenames: tuple[str, ...],
) -> list[Path]:
    roots: set[Path] = set()

    for filename in filenames:
        for file_path in repo_path.rglob(
            filename
        ):
            if (
                not file_path.is_file()
                or _should_ignore(
                    file_path,
                    repo_path,
                )
            ):
                continue

            roots.add(
                file_path.parent.resolve()
            )

    return sorted(
        roots,
        key=lambda path: (
            len(
                path.relative_to(
                    repo_path
                ).parts
            ),
            path.as_posix(),
        ),
    )


def _prune_nested_roots(
    roots: list[Path],
) -> list[Path]:
    selected: list[Path] = []

    for root in roots:
        if any(
            parent == root
            or parent in root.parents
            for parent in selected
        ):
            continue

        selected.append(root)

    return selected


def _discover_build_projects(
    repo_path: Path,
) -> list[tuple[str, Path]]:
    maven_roots = _prune_nested_roots(
        _find_project_roots(
            repo_path,
            (
                "pom.xml",
            ),
        )
    )

    gradle_roots = _prune_nested_roots(
        _find_project_roots(
            repo_path,
            (
                "build.gradle",
                "build.gradle.kts",
            ),
        )
    )

    maven_root_set = set(
        maven_roots
    )

    projects: list[
        tuple[str, Path]
    ] = [
        (
            "Maven",
            root,
        )
        for root in maven_roots
    ]

    for root in gradle_roots:
        if root in maven_root_set:
            continue

        projects.append(
            (
                "Gradle",
                root,
            )
        )

    return sorted(
        projects,
        key=lambda item: (
            len(
                item[1]
                .relative_to(
                    repo_path
                )
                .parts
            ),
            item[1].as_posix(),
            item[0],
        ),
    )


def _resolve_maven_command(
    repo_path: Path,
) -> list[str] | None:
    if os.name == "nt":
        wrapper = (
            repo_path
            / "mvnw.cmd"
        )

        if wrapper.exists():
            return [
                str(wrapper),
                "test",
            ]

        system_maven = (
            shutil.which(
                "mvn.cmd"
            )
            or shutil.which(
                "mvn"
            )
        )

    else:
        wrapper = (
            repo_path
            / "mvnw"
        )

        if wrapper.exists():
            return [
                str(wrapper),
                "test",
            ]

        system_maven = (
            shutil.which(
                "mvn"
            )
        )

    if not system_maven:
        return None

    return [
        system_maven,
        "test",
    ]


def _resolve_gradle_command(
    repo_path: Path,
) -> list[str] | None:
    if os.name == "nt":
        wrapper = (
            repo_path
            / "gradlew.bat"
        )

        if wrapper.exists():
            return [
                str(wrapper),
                "test",
            ]

        system_gradle = (
            shutil.which(
                "gradle.bat"
            )
            or shutil.which(
                "gradle"
            )
        )

    else:
        wrapper = (
            repo_path
            / "gradlew"
        )

        if wrapper.exists():
            return [
                str(wrapper),
                "test",
            ]

        system_gradle = (
            shutil.which(
                "gradle"
            )
        )

    if not system_gradle:
        return None

    return [
        system_gradle,
        "test",
    ]


def _run_command(
    command: list[str],
    repo_path: Path,
) -> dict:
    try:
        result = subprocess.run(
            command,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=TEST_TIMEOUT_SECONDS,
            shell=False,
        )

    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "status": "error",
            "exit_code": None,
            "stdout": (
                exc.stdout
                if isinstance(
                    exc.stdout,
                    str,
                )
                else ""
            ),
            "stderr": (
                "Test command exceeded "
                f"{TEST_TIMEOUT_SECONDS} seconds."
            ),
        }

    except FileNotFoundError as exc:
        return {
            "command": command,
            "status": "error",
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
        }

    except OSError as exc:
        return {
            "command": command,
            "status": "error",
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
        }

    status = (
        "passed"
        if result.returncode == 0
        else "failed"
    )

    return {
        "command": command,
        "status": status,
        "exit_code": (
            result.returncode
        ),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def _missing_command_result(
    build_tool: str,
    project_path: str,
) -> dict:
    return {
        "project_path": (
            project_path
        ),
        "build_tool": (
            build_tool
        ),
        "command": [],
        "status": "error",
        "exit_code": None,
        "stdout": "",
        "stderr": (
            f"{build_tool} was detected in "
            f"{project_path}, but no wrapper "
            "or system executable could be "
            "resolved."
        ),
    }


def run_repository_tests(
    repo_path: Path,
    build_tools: list[str],
) -> dict:
    repo_path = Path(
        repo_path
    ).resolve()

    normalized_tools = {
        str(tool).strip().lower()
        for tool in build_tools
        if tool
    }

    projects = (
        _discover_build_projects(
            repo_path
        )
    )

    if not projects:
        return {
            "status": "skipped",
            "reason": (
                "No supported Maven or Gradle "
                "build project was detected "
                "for automated testing."
            ),
            "tests": [],
        }

    if (
        len(projects)
        > MAX_PROJECTS_TO_TEST
    ):
        return {
            "status": "error",
            "reason": (
                "Automatic baseline validation "
                f"found {len(projects)} independent "
                "build projects, which exceeds the "
                f"safety limit of {MAX_PROJECTS_TO_TEST}."
            ),
            "tests": [],
        }

    tests: list[dict] = []
    build_tools_used: list[str] = []

    for (
        build_tool,
        project_root,
    ) in projects:
        normalized_tool = (
            build_tool.lower()
        )

        if (
            normalized_tools
            and normalized_tool
            not in normalized_tools
        ):
            continue

        project_path = (
            _relative_path(
                project_root,
                repo_path,
            )
        )

        if build_tool == "Maven":
            command = (
                _resolve_maven_command(
                    project_root
                )
            )
        else:
            command = (
                _resolve_gradle_command(
                    project_root
                )
            )

        if command is None:
            tests.append(
                _missing_command_result(
                    build_tool,
                    project_path,
                )
            )
            continue

        test_result = (
            _run_command(
                command,
                project_root,
            )
        )

        test_result[
            "project_path"
        ] = project_path

        test_result[
            "build_tool"
        ] = build_tool

        tests.append(
            test_result
        )

        if (
            build_tool
            not in build_tools_used
        ):
            build_tools_used.append(
                build_tool
            )

    if not tests:
        return {
            "status": "skipped",
            "reason": (
                "Supported build projects were "
                "discovered, but none matched the "
                "detected build tool set."
            ),
            "tests": [],
        }

    statuses = {
        str(
            test.get(
                "status",
                "error",
            )
        )
        for test in tests
    }

    if statuses == {
        "passed"
    }:
        overall_status = (
            "passed"
        )
    elif "failed" in statuses:
        overall_status = (
            "failed"
        )
    else:
        overall_status = (
            "error"
        )

    return {
        "status": overall_status,
        "build_tool": ", ".join(
            build_tools_used
        )
        or None,
        "project_count": len(
            tests
        ),
        "reason": (
            "Validated "
            f"{len(tests)} independent "
            "build project"
            f"{'' if len(tests) == 1 else 's'}."
        ),
        "tests": tests,
    }
