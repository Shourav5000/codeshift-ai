from __future__ import annotations

from pathlib import Path


def _safe_target_path(
    repo_path: Path,
    relative_path: str,
) -> Path:

    repo_root = repo_path.resolve()

    target = (
        repo_root
        / relative_path
    ).resolve()

    if (
        target != repo_root
        and repo_root not in target.parents
    ):
        raise ValueError(
            "Unsafe repository path detected."
        )

    return target


def _find_approved_changes(
    analysis: dict,
) -> list[dict]:

    proposal = analysis.get(
        "code_change_proposal",
        {},
    )

    proposed_changes = proposal.get(
        "changes",
        [],
    )

    if not isinstance(
        proposed_changes,
        list,
    ):
        return []

    review = analysis.get(
        "code_review",
        {},
    )

    reviews = review.get(
        "reviews",
        [],
    )

    if not isinstance(
        reviews,
        list,
    ):
        return []

    approved_indexes = {
        item.get(
            "change_index"
        )
        for item in reviews
        if (
            isinstance(
                item,
                dict,
            )
            and item.get(
                "decision"
            )
            == "approved"
        )
    }

    approved_changes = []

    for index, change in enumerate(
        proposed_changes
    ):
        if index not in approved_indexes:
            continue

        if not isinstance(
            change,
            dict,
        ):
            continue

        if change.get(
            "verification_required",
            False,
        ):
            continue

        if not change.get(
            "automation_candidate",
            False,
        ):
            continue

        approved_changes.append(
            change
        )

    return approved_changes


def prepare_patch_plan(
    analysis: dict,
) -> dict:

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
                "Human approval has not "
                "been granted."
            ),
            "change_count": 0,
            "changes": [],
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
            "change_count": 0,
            "changes": [],
        }

    repo_path = Path(
        repo_path_value
    ).resolve()

    if not repo_path.exists():
        return {
            "status": "error",
            "reason": (
                "Repository working directory "
                "no longer exists."
            ),
            "change_count": 0,
            "changes": [],
        }

    approved_changes = (
        _find_approved_changes(
            analysis
        )
    )

    patch_plan = []

    for change in approved_changes:

        relative_path = change.get(
            "file"
        )

        if not isinstance(
            relative_path,
            str,
        ):
            continue

        if not relative_path.strip():
            continue

        try:
            target_path = (
                _safe_target_path(
                    repo_path,
                    relative_path,
                )
            )

        except ValueError:
            patch_plan.append(
                {
                    "file": relative_path,
                    "ready_for_patch": False,
                    "reason": (
                        "Unsafe repository path."
                    ),
                }
            )
            continue

        proposed_change = change.get(
            "proposed_change",
            {},
        )

        if not isinstance(
            proposed_change,
            dict,
        ):
            proposed_change = {}

        before = proposed_change.get(
            "before"
        )

        after = proposed_change.get(
            "after"
        )

        change_type = change.get(
            "change_type"
        )

        ready = True
        reason = None
        occurrence_count = 0

        if change_type == "modify":

            if not target_path.exists():
                ready = False
                reason = (
                    "Target file does not exist."
                )

            elif not target_path.is_file():
                ready = False
                reason = (
                    "Target path is not a file."
                )

            elif not isinstance(
                before,
                str,
            ):
                ready = False
                reason = (
                    "Exact before text is missing."
                )

            elif not isinstance(
                after,
                str,
            ):
                ready = False
                reason = (
                    "Exact after text is missing."
                )

            else:
                try:
                    current_content = (
                        target_path.read_text(
                            encoding="utf-8"
                        )
                    )

                    occurrence_count = (
                        current_content.count(
                            before
                        )
                    )

                    if occurrence_count == 0:
                        ready = False
                        reason = (
                            "Proposed before text "
                            "was not found exactly "
                            "in the target file."
                        )

                    elif occurrence_count > 1:
                        ready = False
                        reason = (
                            "Proposed before text "
                            "appears more than once. "
                            "Automatic replacement "
                            "would be ambiguous."
                        )

                except UnicodeDecodeError:
                    ready = False
                    reason = (
                        "Target file is not a "
                        "supported UTF-8 text file."
                    )

                except OSError as exc:
                    ready = False
                    reason = str(
                        exc
                    )

        elif change_type == "create":

            if target_path.exists():
                ready = False
                reason = (
                    "Create operation blocked "
                    "because target already exists."
                )

            elif before is not None:
                ready = False
                reason = (
                    "Create operation requires "
                    "before to be null."
                )

            elif not isinstance(
                after,
                str,
            ):
                ready = False
                reason = (
                    "Create operation requires "
                    "complete UTF-8 file content "
                    "in after."
                )

        else:
            ready = False
            reason = (
                "Only modify and create "
                "operations are currently supported."
            )

        patch_plan.append(
            {
                "file": relative_path,
                "absolute_path": str(
                    target_path
                ),
                "exists": (
                    target_path.exists()
                ),
                "change_type": (
                    change_type
                ),
                "title": change.get(
                    "title"
                ),
                "before": before,
                "after": after,
                "before_occurrences": (
                    occurrence_count
                ),
                "ready_for_patch": ready,
                "reason": reason,
            }
        )

    ready_count = sum(
        1
        for item in patch_plan
        if item.get(
            "ready_for_patch"
        )
    )

    return {
        "status": "prepared",
        "change_count": len(
            patch_plan
        ),
        "ready_change_count": (
            ready_count
        ),
        "blocked_change_count": (
            len(
                patch_plan
            )
            - ready_count
        ),
        "changes": patch_plan,
    }


def apply_patch_plan(
    analysis: dict,
) -> dict:

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
                "Human approval has not "
                "been granted."
            ),
            "applied_count": 0,
            "changes": [],
        }

    plan = prepare_patch_plan(
        analysis
    )

    if plan.get(
        "status"
    ) != "prepared":
        return plan

    ready_changes = [
        item
        for item in plan.get(
            "changes",
            [],
        )
        if item.get(
            "ready_for_patch"
        )
    ]

    if not ready_changes:
        return {
            "status": "blocked",
            "reason": (
                "No approved changes contain "
                "a safe, applicable patch."
            ),
            "applied_count": 0,
            "changes": plan.get(
                "changes",
                [],
            ),
        }

    applied = []

    for change in ready_changes:

        target_path = Path(
            change[
                "absolute_path"
            ]
        )

        change_type = change.get(
            "change_type"
        )

        try:
            if change_type == "modify":

                before = change[
                    "before"
                ]

                after = change[
                    "after"
                ]

                current_content = (
                    target_path.read_text(
                        encoding="utf-8"
                    )
                )

                occurrence_count = (
                    current_content.count(
                        before
                    )
                )

                if occurrence_count != 1:
                    applied.append(
                        {
                            "file": change[
                                "file"
                            ],
                            "status": "blocked",
                            "reason": (
                                "File changed after "
                                "patch planning or "
                                "replacement became "
                                "ambiguous."
                            ),
                        }
                    )
                    continue

                updated_content = (
                    current_content.replace(
                        before,
                        after,
                        1,
                    )
                )

                if (
                    updated_content
                    == current_content
                ):
                    applied.append(
                        {
                            "file": change[
                                "file"
                            ],
                            "status": "blocked",
                            "reason": (
                                "Patch produced no "
                                "content change."
                            ),
                        }
                    )
                    continue

                target_path.write_text(
                    updated_content,
                    encoding="utf-8",
                )

                applied.append(
                    {
                        "file": change[
                            "file"
                        ],
                        "status": "applied",
                        "change_type": "modify",
                        "title": change.get(
                            "title"
                        ),
                    }
                )

            elif change_type == "create":

                after = change.get(
                    "after"
                )

                if target_path.exists():
                    applied.append(
                        {
                            "file": change[
                                "file"
                            ],
                            "status": "blocked",
                            "reason": (
                                "Target file already "
                                "exists."
                            ),
                        }
                    )
                    continue

                if not isinstance(
                    after,
                    str,
                ):
                    applied.append(
                        {
                            "file": change[
                                "file"
                            ],
                            "status": "blocked",
                            "reason": (
                                "Create content is "
                                "invalid."
                            ),
                        }
                    )
                    continue

                target_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                target_path.write_text(
                    after,
                    encoding="utf-8",
                )

                applied.append(
                    {
                        "file": change[
                            "file"
                        ],
                        "status": "applied",
                        "change_type": "create",
                        "title": change.get(
                            "title"
                        ),
                    }
                )

            else:
                applied.append(
                    {
                        "file": change[
                            "file"
                        ],
                        "status": "blocked",
                        "reason": (
                            "Unsupported change type."
                        ),
                    }
                )

        except OSError as exc:
            applied.append(
                {
                    "file": change[
                        "file"
                    ],
                    "status": "error",
                    "reason": str(
                        exc
                    ),
                }
            )

    applied_count = sum(
        1
        for item in applied
        if item.get(
            "status"
        )
        == "applied"
    )

    failed_count = (
        len(
            applied
        )
        - applied_count
    )

    if applied_count == 0:
        overall_status = "blocked"

    elif failed_count > 0:
        overall_status = (
            "partially_applied"
        )

    else:
        overall_status = "applied"

    return {
        "status": overall_status,
        "applied_count": (
            applied_count
        ),
        "failed_count": (
            failed_count
        ),
        "changes": applied,
    }