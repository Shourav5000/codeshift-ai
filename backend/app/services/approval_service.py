from __future__ import annotations


def evaluate_human_approval(
    code_review: dict,
    test_execution: dict,
) -> dict:
    """
    Determine whether a reviewed proposal may proceed to human approval.

    Human approval is required only when there are executable,
    reviewer-approved changes and baseline validation has passed.
    """

    reviews = code_review.get(
        "reviews",
        [],
    )

    if not isinstance(
        reviews,
        list,
    ):
        reviews = []

    review_status = code_review.get(
        "review_status",
        code_review.get(
            "status",
        ),
    )

    safe_to_apply = bool(
        code_review.get(
            "safe_to_apply",
            False,
        )
    )

    approved_change_count = sum(
        1
        for review in reviews
        if isinstance(
            review,
            dict,
        )
        and review.get(
            "decision"
        )
        == "approved"
    )

    #
    # A genuinely empty approved proposal is a valid no-op.
    #
    if (
        not reviews
        and review_status == "approved"
        and safe_to_apply
    ):
        return {
            "status": "no_changes_required",
            "approved": False,
            "requires_human_approval": False,
            "reason": (
                "No executable repository changes "
                "were proposed."
            ),
        }

    #
    # Any review that is not approved/safe must stop here.
    #
    if (
        review_status != "approved"
        or not safe_to_apply
        or approved_change_count == 0
    ):
        return {
            "status": "blocked",
            "approved": False,
            "requires_human_approval": False,
            "reason": (
                "Code review has not approved "
                "the proposed change set."
            ),
        }

    test_status = test_execution.get(
        "status",
    )

    if test_status != "passed":
        return {
            "status": "blocked",
            "approved": False,
            "requires_human_approval": False,
            "reason": (
                "Baseline validation must pass "
                "before human approval."
            ),
        }

    return {
        "status": "awaiting_human_approval",
        "approved": False,
        "requires_human_approval": True,
        "reason": (
            "Automated review and validation completed. "
            "Human approval is required before "
            "repository changes."
        ),
    }