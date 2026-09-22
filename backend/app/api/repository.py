from pathlib import Path

from fastapi import (
    APIRouter,
    HTTPException,
)

from app.graphs.repository_analysis import (
    repository_analysis_graph,
)

from app.models.repository import (
    ApprovalActionRequest,
    ApprovalDecisionResponse,
    PatchApplicationResponse,
    PublishResponse,
    RepositoryAnalysisRequest,
    RepositoryAnalysisResponse,
)

from app.services.analysis_store import (
    create_analysis,
    get_analysis,
    update_analysis,
)

from app.services.git_publish_service import (
    publish_validated_changes,
)

from app.services.github_service import (
    create_pull_request_from_analysis,
)

from app.services.patch_service import (
    apply_patch_plan,
)

from app.services.test_runner import (
    run_repository_tests,
)


router = APIRouter(
    prefix="/api/repositories",
    tags=["Repository Analysis"],
)


@router.post(
    "/analyze",
    response_model=RepositoryAnalysisResponse,
)
async def analyze_repository(
    request: RepositoryAnalysisRequest,
):
    repository_url = str(
        request.repository_url
    )

    initial_state = {
        "repository_url": repository_url,
        "current_step": "initializing",
        "status": "started",
    }

    try:
        result = (
            await repository_analysis_graph.ainvoke(
                initial_state
            )
        )

        analysis_id = create_analysis(
            result
        )

        return RepositoryAnalysisResponse(
            analysis_id=analysis_id,

            repository_url=repository_url,

            status=result.get(
                "status",
                "completed",
            ),

            repository_name=result.get(
                "repository_name"
            ),

            primary_language=result.get(
                "primary_language"
            ),

            languages=result.get(
                "languages",
                {},
            ),

            frameworks=result.get(
                "frameworks",
                [],
            ),

            build_tools=result.get(
                "build_tools",
                [],
            ),

            java_version=result.get(
                "java_version"
            ),

            has_tests=result.get(
                "has_tests",
                False,
            ),

            files_analyzed=result.get(
                "files_analyzed",
                0,
            ),

            code_structure=result.get(
                "code_structure",
                {},
            ),

            class_count=result.get(
                "class_count",
                0,
            ),

            dependency_analysis=result.get(
                "dependency_analysis",
                {},
            ),

            dependency_count=result.get(
                "dependency_count",
                0,
            ),

            vulnerability_analysis=result.get(
                "vulnerability_analysis",
                {},
            ),

            vulnerability_count=result.get(
                "vulnerability_count",
                0,
            ),

            semgrep_analysis=result.get(
                "semgrep_analysis",
                {},
            ),

            semgrep_finding_count=result.get(
                "semgrep_finding_count",
                0,
            ),

            technical_debt=result.get(
                "technical_debt",
                [],
            ),

            architecture_assessment=result.get(
                "architecture_assessment"
            ),

            modernization_plan=result.get(
                "modernization_plan",
                {},
            ),

            code_change_proposal=result.get(
                "code_change_proposal",
                {},
            ),

            code_review=result.get(
                "code_review",
                {},
            ),

            test_execution=result.get(
                "test_execution",
                {},
            ),

            human_approval=result.get(
                "human_approval",
                {},
            ),

            message=(
                "Repository analysis "
                "completed successfully."
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except RuntimeError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Repository analysis failed: "
                f"{str(exc)}"
            ),
        ) from exc


@router.post(
    "/{analysis_id}/approve",
    response_model=ApprovalDecisionResponse,
)
async def approve_analysis(
    analysis_id: str,
    request: ApprovalActionRequest,
):
    analysis = get_analysis(
        analysis_id
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    approval_state = analysis.get(
        "human_approval",
        {},
    )

    if (
        approval_state.get("status")
        != "awaiting_human_approval"
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "This analysis is not eligible "
                "for approval."
            ),
        )

    analysis[
        "human_approval"
    ] = {
        "status": "approved",
        "approved": True,
        "comment": request.comment,
    }

    analysis[
        "status"
    ] = "approved"

    update_analysis(
        analysis_id,
        analysis,
    )

    return ApprovalDecisionResponse(
        analysis_id=analysis_id,
        status="approved",
        approved=True,
        comment=request.comment,
        message=(
            "Human approval recorded. "
            "Repository changes may now proceed "
            "to the controlled patch stage."
        ),
    )


@router.post(
    "/{analysis_id}/reject",
    response_model=ApprovalDecisionResponse,
)
async def reject_analysis(
    analysis_id: str,
    request: ApprovalActionRequest,
):
    analysis = get_analysis(
        analysis_id
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    current_approval = analysis.get(
        "human_approval",
        {},
    )

    if current_approval.get(
        "status"
    ) in {
        "approved",
        "rejected",
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                "A human decision has already "
                "been recorded for this analysis."
            ),
        )

    analysis[
        "human_approval"
    ] = {
        "status": "rejected",
        "approved": False,
        "comment": request.comment,
    }

    analysis[
        "status"
    ] = "rejected"

    update_analysis(
        analysis_id,
        analysis,
    )

    return ApprovalDecisionResponse(
        analysis_id=analysis_id,
        status="rejected",
        approved=False,
        comment=request.comment,
        message=(
            "Analysis rejected. "
            "No repository changes will be applied."
        ),
    )


@router.post(
    "/{analysis_id}/apply",
    response_model=PatchApplicationResponse,
)
async def apply_analysis_changes(
    analysis_id: str,
):
    analysis = get_analysis(
        analysis_id
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    human_approval = analysis.get(
        "human_approval",
        {},
    )

    if not human_approval.get(
        "approved",
        False,
    ):
        raise HTTPException(
            status_code=409,
            detail=(
                "Human approval is required "
                "before applying changes."
            ),
        )

    patch_result = apply_patch_plan(
        analysis
    )

    patch_status = patch_result.get(
        "status"
    )

    if patch_status not in {
        "applied",
        "partially_applied",
    }:
        analysis[
            "patch_result"
        ] = patch_result

        analysis[
            "status"
        ] = "patch_blocked"

        update_analysis(
            analysis_id,
            analysis,
        )

        return PatchApplicationResponse(
            analysis_id=analysis_id,
            status="patch_blocked",
            patch_result=patch_result,
            post_patch_tests={},
            message=(
                "No repository changes were "
                "applied."
            ),
        )

    repo_path_value = analysis.get(
        "repo_path"
    )

    if not repo_path_value:
        raise HTTPException(
            status_code=500,
            detail=(
                "Repository working directory "
                "is unavailable."
            ),
        )

    post_patch_tests = (
        run_repository_tests(
            Path(
                repo_path_value
            ),
            analysis.get(
                "build_tools",
                [],
            ),
        )
    )

    analysis[
        "patch_result"
    ] = patch_result

    analysis[
        "post_patch_tests"
    ] = post_patch_tests

    if (
        post_patch_tests.get(
            "status"
        )
        == "passed"
    ):
        analysis[
            "status"
        ] = "patch_validated"

        response_status = (
            "patch_validated"
        )

        message = (
            "Changes were applied and "
            "post-patch tests passed."
        )

    else:
        analysis[
            "status"
        ] = "patch_tests_failed"

        response_status = (
            "patch_tests_failed"
        )

        message = (
            "Changes were applied, but "
            "post-patch tests did not pass."
        )

    update_analysis(
        analysis_id,
        analysis,
    )

    return PatchApplicationResponse(
        analysis_id=analysis_id,
        status=response_status,
        patch_result=patch_result,
        post_patch_tests=post_patch_tests,
        message=message,
    )


@router.post(
    "/{analysis_id}/publish",
    response_model=PublishResponse,
)
async def publish_analysis_changes(
    analysis_id: str,
):
    analysis = get_analysis(
        analysis_id
    )

    if analysis is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis not found.",
        )

    existing_publish = analysis.get(
        "publish_result",
        {},
    )

    if (
        analysis.get("status")
        == "patch_validated"
    ):
        publish_result = (
            publish_validated_changes(
                analysis
            )
        )

        if (
            publish_result.get(
                "status"
            )
            != "committed"
        ):
            analysis[
                "publish_result"
            ] = publish_result

            analysis[
                "status"
            ] = "publish_failed"

            update_analysis(
                analysis_id,
                analysis,
            )

            return PublishResponse(
                analysis_id=analysis_id,
                status="publish_failed",

                branch=publish_result.get(
                    "branch"
                ),

                local_commit_sha=(
                    publish_result.get(
                        "commit_sha"
                    )
                ),

                message=publish_result.get(
                    "reason",
                    "Local Git publish failed.",
                ),
            )

        analysis[
            "publish_result"
        ] = publish_result

        analysis[
            "status"
        ] = "committed"

        update_analysis(
            analysis_id,
            analysis,
        )

    elif (
        analysis.get("status")
        in {
            "committed",
            "github_publish_failed",
        }
        and existing_publish.get(
            "status"
        )
        == "committed"
    ):
        publish_result = (
            existing_publish
        )

    else:
        raise HTTPException(
            status_code=409,
            detail=(
                "Changes must be applied "
                "and post-patch tests must "
                "pass before publishing."
            ),
        )

    github_result = (
        create_pull_request_from_analysis(
            analysis,
            publish_result,
        )
    )

    analysis[
        "github_publish_result"
    ] = github_result

    if (
        github_result.get(
            "status"
        )
        != "pull_request_created"
    ):
        analysis[
            "status"
        ] = "github_publish_failed"

        update_analysis(
            analysis_id,
            analysis,
        )

        return PublishResponse(
            analysis_id=analysis_id,

            status=(
                "github_publish_failed"
            ),

            branch=publish_result.get(
                "branch"
            ),

            local_commit_sha=(
                publish_result.get(
                    "commit_sha"
                )
            ),

            remote_commit_sha=(
                github_result.get(
                    "remote_commit_sha"
                )
            ),

            default_branch=(
                github_result.get(
                    "default_branch"
                )
            ),

            message=github_result.get(
                "reason",
                "GitHub publish failed.",
            ),
        )

    analysis[
        "status"
    ] = "pull_request_created"

    update_analysis(
        analysis_id,
        analysis,
    )

    return PublishResponse(
        analysis_id=analysis_id,

        status="pull_request_created",

        branch=github_result.get(
            "branch"
        ),

        local_commit_sha=(
            publish_result.get(
                "commit_sha"
            )
        ),

        remote_commit_sha=(
            github_result.get(
                "remote_commit_sha"
            )
        ),

        default_branch=(
            github_result.get(
                "default_branch"
            )
        ),

        pr_number=github_result.get(
            "pr_number"
        ),

        pr_url=github_result.get(
            "pr_url"
        ),

        message=(
            "Validated changes were "
            "published to GitHub and "
            "a pull request was created."
        ),
    )