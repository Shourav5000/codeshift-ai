from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


TEST_TIMEOUT_SECONDS = 300


def _resolve_maven_command(
    repo_path: Path,
) -> list[str] | None:
    """
    Resolve Maven in the safest preferred order:

    1. Repository Maven Wrapper
    2. System Maven installation

    Windows requires the .cmd wrapper when applicable.
    """

    if os.name == "nt":
        wrapper = repo_path / "mvnw.cmd"

        if wrapper.exists():
            return [
                str(wrapper),
                "test",
            ]

        system_maven = (
            shutil.which("mvn.cmd")
            or shutil.which("mvn")
        )

    else:
        wrapper = repo_path / "mvnw"

        if wrapper.exists():
            return [
                str(wrapper),
                "test",
            ]

        system_maven = shutil.which(
            "mvn"
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
    """
    Resolve Gradle in the safest preferred order:

    1. Repository Gradle Wrapper
    2. System Gradle installation
    """

    if os.name == "nt":
        wrapper = repo_path / "gradlew.bat"

        if wrapper.exists():
            return [
                str(wrapper),
                "test",
            ]

        system_gradle = (
            shutil.which("gradle.bat")
            or shutil.which("gradle")
        )

    else:
        wrapper = repo_path / "gradlew"

        if wrapper.exists():
            return [
                str(wrapper),
                "test",
            ]

        system_gradle = shutil.which(
            "gradle"
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
    """
    Execute one repository test command and normalize the result.
    """

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
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def run_repository_tests(
    repo_path: Path,
    build_tools: list[str],
) -> dict:
    """
    Execute the repository's baseline test command.

    CodeShift prefers project wrappers when available and falls back
    to locally installed build tools.

    At this stage, one primary build system is tested. Maven is
    preferred when both Maven and Gradle are detected.
    """

    repo_path = Path(
        repo_path
    ).resolve()

    normalized_tools = {
        str(tool).strip().lower()
        for tool in build_tools
        if tool
    }

    command: list[str] | None = None
    build_tool: str | None = None

    if "maven" in normalized_tools:
        command = _resolve_maven_command(
            repo_path
        )

        build_tool = "Maven"

    elif "gradle" in normalized_tools:
        command = _resolve_gradle_command(
            repo_path
        )

        build_tool = "Gradle"

    else:
        return {
            "status": "skipped",
            "reason": (
                "No supported build tool was "
                "detected for automated testing."
            ),
            "tests": [],
        }

    if command is None:
        return {
            "status": "error",
            "reason": (
                f"{build_tool} was detected in the repository "
                "but no executable or repository wrapper "
                "could be resolved."
            ),
            "tests": [],
        }

    test_result = _run_command(
        command,
        repo_path,
    )

    overall_status = (
        "passed"
        if test_result.get(
            "status"
        )
        == "passed"
        else test_result.get(
            "status",
            "error",
        )
    )

    return {
        "status": overall_status,
        "build_tool": build_tool,
        "tests": [
            test_result
        ],
    }