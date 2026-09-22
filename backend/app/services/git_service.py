from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4


_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_DATA_ROOT = Path(
    os.getenv(
        "CODESHIFT_DATA_DIR",
        str(_BACKEND_ROOT / ".codeshift"),
    )
)

_WORKSPACES_DIR = (
    _DATA_ROOT
    / "workspaces"
)

_WORKSPACES_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def validate_github_url(
    repository_url: str,
) -> None:

    parsed = urlparse(
        repository_url
    )

    if parsed.scheme not in {
        "http",
        "https",
    }:
        raise ValueError(
            "Repository URL must use HTTP or HTTPS."
        )

    if (
        parsed.netloc.lower()
        != "github.com"
    ):
        raise ValueError(
            "Only github.com repositories are supported right now."
        )

    path_parts = [
        part
        for part in parsed.path.split(
            "/"
        )
        if part
    ]

    if len(
        path_parts
    ) < 2:
        raise ValueError(
            "GitHub URL must contain both owner and repository name."
        )


def clone_repository(
    repository_url: str,
) -> tuple[Path, Path]:
    """
    Clone a repository into a durable CodeShift workspace.

    The workspace survives Python process termination and backend
    restarts.

    Returns:
        workspace_path,
        repository_path
    """

    validate_github_url(
        repository_url
    )

    workspace_id = str(
        uuid4()
    )

    workspace_path = (
        _WORKSPACES_DIR
        / workspace_id
    )

    repo_path = (
        workspace_path
        / "repository"
    )

    workspace_path.mkdir(
        parents=True,
        exist_ok=False,
    )

    try:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                repository_url,
                str(
                    repo_path
                ),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

    except subprocess.CalledProcessError as exc:
        shutil.rmtree(
            workspace_path,
            ignore_errors=True,
        )

        raise RuntimeError(
            exc.stderr.strip()
            or "Failed to clone repository."
        ) from exc

    except subprocess.TimeoutExpired as exc:
        shutil.rmtree(
            workspace_path,
            ignore_errors=True,
        )

        raise RuntimeError(
            "Repository clone timed out."
        ) from exc

    except Exception:
        shutil.rmtree(
            workspace_path,
            ignore_errors=True,
        )
        raise

    return (
        workspace_path,
        repo_path,
    )
