from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import datetime


def _run_git(
    repo_path: Path,
    args: list[str],
) -> dict:

    try:
        completed = subprocess.run(
            [
                "git",
                *args,
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            shell=False,
        )

        return {
            "command": [
                "git",
                *args,
            ],
            "exit_code": (
                completed.returncode
            ),
            "stdout": (
                completed.stdout.strip()
            ),
            "stderr": (
                completed.stderr.strip()
            ),
            "success": (
                completed.returncode == 0
            ),
        }

    except OSError as exc:
        return {
            "command": [
                "git",
                *args,
            ],
            "exit_code": None,
            "stdout": "",
            "stderr": str(exc),
            "success": False,
        }


def publish_validated_changes(
    analysis: dict,
) -> dict:

    if (
        analysis.get("status")
        != "patch_validated"
    ):
        return {
            "status": "blocked",
            "reason": (
                "Only successfully validated "
                "patches may be published."
            ),
        }

    human_approval = analysis.get(
        "human_approval",
        {},
    )

    if not human_approval.get(
        "approved",
        False,
    ):
        return {
            "status": "blocked",
            "reason": (
                "Human approval is required "
                "before publishing changes."
            ),
        }

    repo_path_value = analysis.get(
        "repo_path"
    )

    if not repo_path_value:
        return {
            "status": "error",
            "reason": (
                "Repository working directory "
                "is unavailable."
            ),
        }

    repo_path = Path(
        repo_path_value
    ).resolve()

    if not repo_path.exists():
        return {
            "status": "error",
            "reason": (
                "Repository working directory "
                "does not exist."
            ),
        }

    status_result = _run_git(
        repo_path,
        [
            "status",
            "--porcelain",
        ],
    )

    if not status_result[
        "success"
    ]:
        return {
            "status": "error",
            "reason": (
                "Unable to inspect Git status."
            ),
            "git": status_result,
        }

    if not status_result[
        "stdout"
    ]:
        return {
            "status": "blocked",
            "reason": (
                "No repository changes are "
                "available to commit."
            ),
        }

    timestamp = datetime.utcnow().strftime(
        "%Y%m%d%H%M%S"
    )

    branch_name = (
        f"codeshift/modernization-{timestamp}"
    )

    branch_result = _run_git(
        repo_path,
        [
            "checkout",
            "-b",
            branch_name,
        ],
    )

    if not branch_result[
        "success"
    ]:
        return {
            "status": "error",
            "reason": (
                "Unable to create Git branch."
            ),
            "git": branch_result,
        }

    add_result = _run_git(
        repo_path,
        [
            "add",
            "--all",
        ],
    )

    if not add_result[
        "success"
    ]:
        return {
            "status": "error",
            "reason": (
                "Unable to stage repository "
                "changes."
            ),
            "git": add_result,
        }

    commit_message = (
        "chore: apply CodeShift AI "
        "modernization changes"
    )

    commit_result = _run_git(
        repo_path,
        [
            "commit",
            "-m",
            commit_message,
        ],
    )

    if not commit_result[
        "success"
    ]:
        return {
            "status": "error",
            "reason": (
                "Unable to create Git commit."
            ),
            "git": commit_result,
        }

    commit_sha_result = _run_git(
        repo_path,
        [
            "rev-parse",
            "HEAD",
        ],
    )

    commit_sha = None

    if commit_sha_result[
        "success"
    ]:
        commit_sha = (
            commit_sha_result[
                "stdout"
            ]
        )

    return {
        "status": "committed",
        "branch": branch_name,
        "commit_sha": commit_sha,
        "commit_message": (
            commit_message
        ),
        "push_required": True,
    }