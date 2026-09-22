from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

import base64
import json
import os

from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen


GITHUB_API_URL = "https://api.github.com"


class GitHubAPIError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code


def _parse_repository_url(
    repository_url: str,
) -> tuple[str, str]:

    parsed = urlparse(
        repository_url
    )

    if parsed.hostname not in {
        "github.com",
        "www.github.com",
    }:
        raise ValueError(
            "Only github.com repositories "
            "are supported."
        )

    parts = [
        part
        for part in parsed.path.split("/")
        if part
    ]

    if len(parts) != 2:
        raise ValueError(
            "Invalid GitHub repository URL."
        )

    owner = parts[0]
    repository = parts[1]

    if repository.endswith(".git"):
        repository = repository[:-4]

    if not owner or not repository:
        raise ValueError(
            "Invalid GitHub repository URL."
        )

    return owner, repository


def _get_github_token() -> str:

    token = os.getenv(
        "GITHUB_TOKEN"
    )

    if not token:
        raise GitHubAPIError(
            "GITHUB_TOKEN is not configured."
        )

    return token


def _github_request(
    method: str,
    path: str,
    body: dict | None = None,
) -> dict:

    token = _get_github_token()

    url = (
        f"{GITHUB_API_URL}"
        f"{path}"
    )

    data = None

    if body is not None:
        data = json.dumps(
            body
        ).encode(
            "utf-8"
        )

    request = Request(
        url=url,
        data=data,
        method=method,
        headers={
            "Accept": (
                "application/vnd.github+json"
            ),
            "Authorization": (
                f"Bearer {token}"
            ),
            "X-GitHub-Api-Version": (
                "2022-11-28"
            ),
            "User-Agent": (
                "CodeShift-AI"
            ),
            "Content-Type": (
                "application/json"
            ),
        },
    )

    try:
        with urlopen(
            request,
            timeout=30,
        ) as response:

            response_body = (
                response.read()
            )

            if not response_body:
                return {}

            return json.loads(
                response_body.decode(
                    "utf-8"
                )
            )

    except HTTPError as exc:

        error_message = (
            f"GitHub API returned "
            f"HTTP {exc.code}."
        )

        try:
            response_body = (
                exc.read().decode(
                    "utf-8"
                )
            )

            payload = json.loads(
                response_body
            )

            github_message = (
                payload.get(
                    "message"
                )
            )

            if github_message:
                error_message = (
                    "GitHub API error: "
                    f"{github_message}"
                )

        except (
            ValueError,
            UnicodeDecodeError,
        ):
            pass

        raise GitHubAPIError(
            error_message,
            status_code=exc.code,
        ) from exc

    except URLError as exc:
        raise GitHubAPIError(
            "Unable to reach GitHub API."
        ) from exc


def _get_repository(
    owner: str,
    repository: str,
) -> dict:

    return _github_request(
        "GET",
        (
            f"/repos/{owner}/"
            f"{repository}"
        ),
    )


def _get_branch_ref(
    owner: str,
    repository: str,
    branch: str,
) -> dict:

    encoded_branch = quote(
        branch,
        safe="",
    )

    return _github_request(
        "GET",
        (
            f"/repos/{owner}/"
            f"{repository}/git/ref/"
            f"heads/{encoded_branch}"
        ),
    )


def _create_branch(
    owner: str,
    repository: str,
    branch: str,
    base_sha: str,
) -> dict:

    return _github_request(
        "POST",
        (
            f"/repos/{owner}/"
            f"{repository}/git/refs"
        ),
        {
            "ref": (
                f"refs/heads/"
                f"{branch}"
            ),
            "sha": base_sha,
        },
    )


def _get_file_info(
    owner: str,
    repository: str,
    relative_path: str,
    branch: str,
) -> dict:

    encoded_path = quote(
        relative_path,
        safe="/",
    )

    query = urlencode(
        {
            "ref": branch,
        }
    )

    return _github_request(
        "GET",
        (
            f"/repos/{owner}/"
            f"{repository}/contents/"
            f"{encoded_path}?"
            f"{query}"
        ),
    )


def _get_file_info_if_exists(
    owner: str,
    repository: str,
    relative_path: str,
    branch: str,
) -> dict | None:

    try:
        return _get_file_info(
            owner,
            repository,
            relative_path,
            branch,
        )

    except GitHubAPIError as exc:

        if exc.status_code == 404:
            return None

        raise


def _encode_content(
    content: str,
) -> str:

    return (
        base64.b64encode(
            content.encode(
                "utf-8"
            )
        ).decode(
            "ascii"
        )
    )


def _create_file(
    owner: str,
    repository: str,
    relative_path: str,
    branch: str,
    content: str,
) -> dict:

    encoded_path = quote(
        relative_path,
        safe="/",
    )

    encoded_content = (
        _encode_content(
            content
        )
    )

    return _github_request(
        "PUT",
        (
            f"/repos/{owner}/"
            f"{repository}/contents/"
            f"{encoded_path}"
        ),
        {
            "message": (
                "chore: apply CodeShift AI "
                "modernization change"
            ),
            "content": encoded_content,
            "branch": branch,
        },
    )


def _update_file(
    owner: str,
    repository: str,
    relative_path: str,
    branch: str,
    content: str,
    existing_sha: str,
) -> dict:

    encoded_path = quote(
        relative_path,
        safe="/",
    )

    encoded_content = (
        _encode_content(
            content
        )
    )

    return _github_request(
        "PUT",
        (
            f"/repos/{owner}/"
            f"{repository}/contents/"
            f"{encoded_path}"
        ),
        {
            "message": (
                "chore: apply CodeShift AI "
                "modernization change"
            ),
            "content": encoded_content,
            "sha": existing_sha,
            "branch": branch,
        },
    )


def _create_pull_request(
    owner: str,
    repository: str,
    branch: str,
    base_branch: str,
    body: str,
) -> dict:

    return _github_request(
        "POST",
        (
            f"/repos/{owner}/"
            f"{repository}/pulls"
        ),
        {
            "title": (
                "CodeShift AI modernization"
            ),
            "head": branch,
            "base": base_branch,
            "body": body,
        },
    )


def _validate_local_file(
    repo_path: Path,
    relative_path: str,
) -> Path:

    repo_root = (
        repo_path.resolve()
    )

    target = (
        repo_root
        / relative_path
    ).resolve()

    if (
        target != repo_root
        and repo_root
        not in target.parents
    ):
        raise ValueError(
            "Unsafe repository path."
        )

    if not target.exists():
        raise ValueError(
            f"File does not exist: "
            f"{relative_path}"
        )

    if not target.is_file():
        raise ValueError(
            f"Path is not a file: "
            f"{relative_path}"
        )

    return target


def create_pull_request_from_analysis(
    analysis: dict,
    publish_result: dict,
) -> dict:

    repository_url = analysis.get(
        "repository_url"
    )

    if not repository_url:
        return {
            "status": "error",
            "reason": (
                "Repository URL is missing."
            ),
        }

    branch = publish_result.get(
        "branch"
    )

    if not branch:
        return {
            "status": "error",
            "reason": (
                "Git branch is missing."
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

    patch_result = analysis.get(
        "patch_result",
        {},
    )

    applied_changes = [
        change
        for change in patch_result.get(
            "changes",
            [],
        )
        if (
            isinstance(
                change,
                dict,
            )
            and change.get(
                "status"
            )
            == "applied"
        )
    ]

    if not applied_changes:
        return {
            "status": "blocked",
            "reason": (
                "No applied changes are "
                "available to publish."
            ),
        }

    try:
        owner, repository = (
            _parse_repository_url(
                repository_url
            )
        )

        repository_info = (
            _get_repository(
                owner,
                repository,
            )
        )

        default_branch = (
            repository_info.get(
                "default_branch"
            )
        )

        if not default_branch:
            return {
                "status": "error",
                "reason": (
                    "Unable to determine "
                    "the default branch."
                ),
            }

        base_ref = (
            _get_branch_ref(
                owner,
                repository,
                default_branch,
            )
        )

        base_sha = (
            base_ref.get(
                "object",
                {},
            ).get(
                "sha"
            )
        )

        if not base_sha:
            return {
                "status": "error",
                "reason": (
                    "Unable to determine "
                    "the base commit SHA."
                ),
            }

        _create_branch(
            owner,
            repository,
            branch,
            base_sha,
        )

        repo_path = Path(
            repo_path_value
        ).resolve()

        remote_commit_sha = None
        published_files = []

        for change in applied_changes:

            relative_path = (
                change.get(
                    "file"
                )
            )

            change_type = (
                change.get(
                    "change_type"
                )
            )

            if not isinstance(
                relative_path,
                str,
            ):
                continue

            if change_type not in {
                "create",
                "modify",
            }:
                return {
                    "status": "blocked",
                    "reason": (
                        "Unsupported published "
                        "change type: "
                        f"{change_type}"
                    ),
                }

            normalized_path = (
                relative_path.replace(
                    "\\",
                    "/",
                )
            )

            if normalized_path.startswith(
                ".github/workflows/"
            ):
                return {
                    "status": "blocked",
                    "reason": (
                        "Automatic modification "
                        "of GitHub Actions "
                        "workflow files is "
                        "disabled."
                    ),
                }

            target_path = (
                _validate_local_file(
                    repo_path,
                    relative_path,
                )
            )

            try:
                file_content = (
                    target_path.read_text(
                        encoding="utf-8"
                    )
                )

            except UnicodeDecodeError:
                return {
                    "status": "blocked",
                    "reason": (
                        "Only UTF-8 text files "
                        "may be published."
                    ),
                }

            remote_file = (
                _get_file_info_if_exists(
                    owner,
                    repository,
                    normalized_path,
                    branch,
                )
            )

            if change_type == "create":

                if remote_file is not None:
                    return {
                        "status": "blocked",
                        "reason": (
                            "Remote file already "
                            "exists but the approved "
                            "change requires creation: "
                            f"{normalized_path}"
                        ),
                    }

                file_result = (
                    _create_file(
                        owner,
                        repository,
                        normalized_path,
                        branch,
                        file_content,
                    )
                )

            else:

                if remote_file is None:
                    return {
                        "status": "blocked",
                        "reason": (
                            "Remote file does not "
                            "exist but the approved "
                            "change requires modification: "
                            f"{normalized_path}"
                        ),
                    }

                existing_sha = (
                    remote_file.get(
                        "sha"
                    )
                )

                if not existing_sha:
                    return {
                        "status": "error",
                        "reason": (
                            "Unable to determine "
                            "remote file SHA for "
                            f"{normalized_path}."
                        ),
                    }

                file_result = (
                    _update_file(
                        owner,
                        repository,
                        normalized_path,
                        branch,
                        file_content,
                        existing_sha,
                    )
                )

            commit = (
                file_result.get(
                    "commit",
                    {},
                )
            )

            remote_commit_sha = (
                commit.get(
                    "sha"
                )
                or remote_commit_sha
            )

            published_files.append(
                normalized_path
            )

        if not published_files:
            return {
                "status": "blocked",
                "reason": (
                    "No eligible files were "
                    "published."
                ),
            }

        review = analysis.get(
            "code_review",
            {},
        )

        test_result = analysis.get(
            "post_patch_tests",
            {},
        )

        pr_body = (
            "## CodeShift AI\n\n"
            "This pull request was created "
            "after the CodeShift AI "
            "modernization pipeline completed.\n\n"
            "### Validation\n"
            f"- Code review: "
            f"{review.get('review_status', 'unknown')}\n"
            f"- Post-patch tests: "
            f"{test_result.get('status', 'unknown')}\n"
            f"- Files changed: "
            f"{len(published_files)}\n\n"
            "Human approval was recorded "
            "before repository changes were "
            "published."
        )

        pull_request = (
            _create_pull_request(
                owner,
                repository,
                branch,
                default_branch,
                pr_body,
            )
        )

        return {
            "status": (
                "pull_request_created"
            ),
            "owner": owner,
            "repository": repository,
            "default_branch": (
                default_branch
            ),
            "branch": branch,
            "remote_commit_sha": (
                remote_commit_sha
            ),
            "published_files": (
                published_files
            ),
            "pr_number": (
                pull_request.get(
                    "number"
                )
            ),
            "pr_url": (
                pull_request.get(
                    "html_url"
                )
            ),
        }

    except (
        ValueError,
        GitHubAPIError,
        OSError,
    ) as exc:

        status_code = None

        if isinstance(
            exc,
            GitHubAPIError,
        ):
            status_code = (
                exc.status_code
            )

        return {
            "status": (
                "github_publish_failed"
            ),
            "reason": str(
                exc
            ),
            "github_status_code": (
                status_code
            ),
        }