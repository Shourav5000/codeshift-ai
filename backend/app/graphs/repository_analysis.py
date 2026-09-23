from __future__ import annotations

from pathlib import Path
from typing import TypedDict

from langgraph.graph import (
    END,
    START,
    StateGraph,
)

from app.agents.architecture_agent import (
    analyze_architecture,
)

from app.agents.code_agent import (
    create_code_change_proposal,
)

from app.agents.reviewer_agent import (
    review_code_change_proposal,
)

from app.agents.modernization_planner import (
    create_modernization_plan,
)

from app.agents.technical_debt_agent import (
    analyze_technical_debt,
)

from app.services.approval_service import (
    evaluate_human_approval,
)

from app.services.code_structure_scanner import (
    scan_java_structure,
)

from app.services.dependency_scanner import (
    scan_dependencies,
)

from app.services.git_service import (
    clone_repository,
    validate_github_url,
)

from app.services.repository_content_service import (
    collect_repository_files,
)

from app.services.repository_scanner import (
    scan_repository,
)

from app.services.semgrep_scanner import (
    scan_with_semgrep,
)

from app.services.test_runner import (
    run_repository_tests,
)

from app.services.vulnerability_scanner import (
    scan_vulnerabilities,
)


class RepositoryState(
    TypedDict,
    total=False,
):
    repository_url: str
    current_step: str
    status: str
    repository_name: str
    workspace_path: str
    repo_path: str
    primary_language: str | None
    languages: dict[str, int]
    frameworks: list[str]
    build_tools: list[str]
    java_version: str | None
    has_tests: bool
    files_analyzed: int
    repository_files: dict
    code_structure: dict
    class_count: int
    dependency_analysis: dict
    dependency_count: int
    vulnerability_analysis: dict
    vulnerability_count: int
    semgrep_analysis: dict
    semgrep_finding_count: int
    technical_debt: list[dict]
    architecture_assessment: str
    modernization_plan: dict
    code_change_proposal: dict
    code_review: dict
    test_execution: dict
    human_approval: dict
    error: str


def validate_repository(
    state: RepositoryState,
) -> RepositoryState:

    validate_github_url(
        state["repository_url"]
    )

    repository_name = (
        state["repository_url"]
        .rstrip("/")
        .split("/")[-1]
        .replace(
            ".git",
            "",
        )
    )

    return {
        **state,
        "repository_name": (
            repository_name
        ),
        "current_step": (
            "repository_validation"
        ),
        "status": "validated",
    }


def clone_repo(
    state: RepositoryState,
) -> RepositoryState:

    (
        workspace_path,
        repo_path,
    ) = clone_repository(
        state["repository_url"]
    )

    return {
        **state,
        "workspace_path": str(
            workspace_path
        ),
        "repo_path": str(
            repo_path
        ),
        "current_step": (
            "repository_clone"
        ),
        "status": "cloned",
    }


def analyze_repository_files(
    state: RepositoryState,
) -> RepositoryState:

    repo_path = Path(
        state["repo_path"]
    )

    analysis = scan_repository(
        repo_path
    )

    return {
        **state,
        **analysis,
        "current_step": (
            "repository_analysis"
        ),
        "status": "analyzed",
    }


def collect_repository_content(
    state: RepositoryState,
) -> RepositoryState:

    repo_path = Path(
        state["repo_path"]
    )

    repository_files = (
        collect_repository_files(
            repo_path
        )
    )

    return {
        **state,
        "repository_files": (
            repository_files
        ),
        "current_step": (
            "repository_content_collection"
        ),
        "status": (
            "repository_content_collected"
        ),
    }


def analyze_code_structure(
    state: RepositoryState,
) -> RepositoryState:

    repo_path = Path(
        state["repo_path"]
    )

    code_structure = {}

    languages = (
        state.get(
            "languages",
            {},
        )
        or {}
    )

    if "Java" in languages:
        code_structure = (
            scan_java_structure(
                repo_path
            )
        )

    return {
        **state,
        "code_structure": (
            code_structure
        ),
        "class_count": (
            code_structure.get(
                "class_count",
                0,
            )
        ),
        "current_step": (
            "code_structure_analysis"
        ),
        "status": (
            "structure_analyzed"
        ),
    }


def analyze_dependencies(
    state: RepositoryState,
) -> RepositoryState:

    repo_path = Path(
        state["repo_path"]
    )

    dependency_analysis = (
        scan_dependencies(
            repo_path
        )
    )

    return {
        **state,
        "dependency_analysis": (
            dependency_analysis
        ),
        "dependency_count": (
            dependency_analysis.get(
                "dependency_count",
                0,
            )
        ),
        "current_step": (
            "dependency_analysis"
        ),
        "status": (
            "dependencies_analyzed"
        ),
    }


def analyze_vulnerabilities(
    state: RepositoryState,
) -> RepositoryState:

    vulnerability_analysis = (
        scan_vulnerabilities(
            state.get(
                "dependency_analysis",
                {},
            )
        )
    )

    return {
        **state,
        "vulnerability_analysis": (
            vulnerability_analysis
        ),
        "vulnerability_count": (
            vulnerability_analysis.get(
                "vulnerability_count",
                0,
            )
        ),
        "current_step": (
            "vulnerability_analysis"
        ),
        "status": (
            "vulnerabilities_analyzed"
        ),
    }


def analyze_semgrep(
    state: RepositoryState,
) -> RepositoryState:

    repo_path = Path(
        state["repo_path"]
    )

    semgrep_analysis = (
        scan_with_semgrep(
            repo_path
        )
    )

    return {
        **state,
        "semgrep_analysis": (
            semgrep_analysis
        ),
        "semgrep_finding_count": (
            semgrep_analysis.get(
                "finding_count",
                0,
            )
        ),
        "current_step": (
            "semgrep_analysis"
        ),
        "status": (
            "semgrep_analyzed"
        ),
    }


async def technical_debt_analysis(
    state: RepositoryState,
) -> RepositoryState:

    repository_summary = {
        "repository_name": (
            state.get(
                "repository_name"
            )
        ),
        "primary_language": (
            state.get(
                "primary_language"
            )
        ),
        "languages": (
            state.get(
                "languages",
                {},
            )
        ),
        "frameworks": (
            state.get(
                "frameworks",
                [],
            )
        ),
        "build_tools": (
            state.get(
                "build_tools",
                [],
            )
        ),
        "java_version": (
            state.get(
                "java_version"
            )
        ),
        "has_tests": (
            state.get(
                "has_tests",
                False,
            )
        ),
        "files_analyzed": (
            state.get(
                "files_analyzed",
                0,
            )
        ),
        "class_count": (
            state.get(
                "class_count",
                0,
            )
        ),
        "code_structure": (
            state.get(
                "code_structure",
                {},
            )
        ),
        "dependency_analysis": (
            state.get(
                "dependency_analysis",
                {},
            )
        ),
        "vulnerability_analysis": (
            state.get(
                "vulnerability_analysis",
                {},
            )
        ),
        "semgrep_analysis": (
            state.get(
                "semgrep_analysis",
                {},
            )
        ),
    }

    findings = (
        await analyze_technical_debt(
            repository_summary
        )
    )

    return {
        **state,
        "technical_debt": (
            findings
        ),
        "current_step": (
            "technical_debt_analysis"
        ),
        "status": (
            "debt_analyzed"
        ),
    }


async def architecture_analysis(
    state: RepositoryState,
) -> RepositoryState:

    repository_summary = {
        "repository_name": (
            state.get(
                "repository_name"
            )
        ),
        "primary_language": (
            state.get(
                "primary_language"
            )
        ),
        "languages": (
            state.get(
                "languages",
                {},
            )
        ),
        "frameworks": (
            state.get(
                "frameworks",
                [],
            )
        ),
        "build_tools": (
            state.get(
                "build_tools",
                [],
            )
        ),
        "java_version": (
            state.get(
                "java_version"
            )
        ),
        "has_tests": (
            state.get(
                "has_tests",
                False,
            )
        ),
        "files_analyzed": (
            state.get(
                "files_analyzed",
                0,
            )
        ),
        "class_count": (
            state.get(
                "class_count",
                0,
            )
        ),
        "code_structure": (
            state.get(
                "code_structure",
                {},
            )
        ),
        "dependency_analysis": (
            state.get(
                "dependency_analysis",
                {},
            )
        ),
        "vulnerability_analysis": (
            state.get(
                "vulnerability_analysis",
                {},
            )
        ),
        "semgrep_analysis": (
            state.get(
                "semgrep_analysis",
                {},
            )
        ),
        "repository_files": (
            state.get(
                "repository_files",
                {},
            )
        ),
        "technical_debt": (
            state.get(
                "technical_debt",
                [],
            )
        ),
    }

    assessment = (
        await analyze_architecture(
            repository_summary
        )
    )

    return {
        **state,
        "architecture_assessment": (
            assessment
        ),
        "current_step": (
            "architecture_analysis"
        ),
        "status": (
            "architecture_analyzed"
        ),
    }


async def modernization_planning(
    state: RepositoryState,
) -> RepositoryState:

    repository_summary = {
        "repository_name": (
            state.get(
                "repository_name"
            )
        ),
        "primary_language": (
            state.get(
                "primary_language"
            )
        ),
        "languages": (
            state.get(
                "languages",
                {},
            )
        ),
        "frameworks": (
            state.get(
                "frameworks",
                [],
            )
        ),
        "build_tools": (
            state.get(
                "build_tools",
                [],
            )
        ),
        "java_version": (
            state.get(
                "java_version"
            )
        ),
        "has_tests": (
            state.get(
                "has_tests",
                False,
            )
        ),
        "files_analyzed": (
            state.get(
                "files_analyzed",
                0,
            )
        ),
        "class_count": (
            state.get(
                "class_count",
                0,
            )
        ),
        "code_structure": (
            state.get(
                "code_structure",
                {},
            )
        ),
        "dependency_analysis": (
            state.get(
                "dependency_analysis",
                {},
            )
        ),
        "vulnerability_analysis": (
            state.get(
                "vulnerability_analysis",
                {},
            )
        ),
        "semgrep_analysis": (
            state.get(
                "semgrep_analysis",
                {},
            )
        ),
    }

    technical_debt = (
        state.get(
            "technical_debt",
            [],
        )
    )

    architecture_assessment = (
        state.get(
            "architecture_assessment",
            "",
        )
    )

    modernization_plan = (
        await create_modernization_plan(
            repository_summary,
            technical_debt,
            architecture_assessment,
        )
    )

    return {
        **state,
        "modernization_plan": (
            modernization_plan
        ),
        "current_step": (
            "modernization_planning"
        ),
        "status": (
            "modernization_planned"
        ),
    }


async def code_change_planning(
    state: RepositoryState,
) -> RepositoryState:

    repository_context = {
        "repository_name": (
            state.get(
                "repository_name"
            )
        ),
        "primary_language": (
            state.get(
                "primary_language"
            )
        ),
        "frameworks": (
            state.get(
                "frameworks",
                [],
            )
        ),
        "build_tools": (
            state.get(
                "build_tools",
                [],
            )
        ),
        "java_version": (
            state.get(
                "java_version"
            )
        ),
        "code_structure": (
            state.get(
                "code_structure",
                {},
            )
        ),
        "dependency_analysis": (
            state.get(
                "dependency_analysis",
                {},
            )
        ),
        "vulnerability_analysis": (
            state.get(
                "vulnerability_analysis",
                {},
            )
        ),
        "semgrep_analysis": (
            state.get(
                "semgrep_analysis",
                {},
            )
        ),
        "technical_debt": (
            state.get(
                "technical_debt",
                [],
            )
        ),
        "architecture_assessment": (
            state.get(
                "architecture_assessment",
                "",
            )
        ),
        "modernization_plan": (
            state.get(
                "modernization_plan",
                {},
            )
        ),
        "repository_files": (
            state.get(
                "repository_files",
                {},
            )
        ),
    }

    proposal = (
        await create_code_change_proposal(
            repository_context
        )
    )

    return {
        **state,
        "code_change_proposal": (
            proposal
        ),
        "current_step": (
            "code_change_planning"
        ),
        "status": (
            "changes_proposed"
        ),
    }


async def code_change_review(
    state: RepositoryState,
) -> RepositoryState:

    review_context = {
        "repository_name": (
            state.get(
                "repository_name"
            )
        ),
        "primary_language": (
            state.get(
                "primary_language"
            )
        ),
        "frameworks": (
            state.get(
                "frameworks",
                [],
            )
        ),
        "build_tools": (
            state.get(
                "build_tools",
                [],
            )
        ),
        "java_version": (
            state.get(
                "java_version"
            )
        ),
        "code_structure": (
            state.get(
                "code_structure",
                {},
            )
        ),
        "dependency_analysis": (
            state.get(
                "dependency_analysis",
                {},
            )
        ),
        "vulnerability_analysis": (
            state.get(
                "vulnerability_analysis",
                {},
            )
        ),
        "semgrep_analysis": (
            state.get(
                "semgrep_analysis",
                {},
            )
        ),
        "technical_debt": (
            state.get(
                "technical_debt",
                [],
            )
        ),
        "architecture_assessment": (
            state.get(
                "architecture_assessment",
                "",
            )
        ),
        "modernization_plan": (
            state.get(
                "modernization_plan",
                {},
            )
        ),
        "repository_files": (
            state.get(
                "repository_files",
                {},
            )
        ),
        "code_change_proposal": (
            state.get(
                "code_change_proposal",
                {},
            )
        ),
    }

    review = (
        await review_code_change_proposal(
            review_context
        )
    )

    return {
        **state,
        "code_review": (
            review
        ),
        "current_step": (
            "code_change_review"
        ),
        "status": (
            "review_completed"
        ),
    }


def test_execution(
    state: RepositoryState,
) -> RepositoryState:

    repo_path = Path(
        state["repo_path"]
    )

    review = state.get(
        "code_review",
        {},
    )

    safe_to_apply = review.get(
        "safe_to_apply",
        False,
    )

    if not safe_to_apply:
        return {
            **state,
            "test_execution": {
                "status": "skipped",
                "reason": (
                    "Code review did not approve "
                    "the proposed change set."
                ),
                "tests": [],
            },
            "current_step": (
                "test_execution"
            ),
            "status": (
                "tests_skipped"
            ),
        }

    test_result = (
        run_repository_tests(
            repo_path,
            state.get(
                "build_tools",
                [],
            ),
        )
    )

    return {
        **state,
        "test_execution": (
            test_result
        ),
        "current_step": (
            "test_execution"
        ),
        "status": (
            "tests_completed"
        ),
    }


def human_approval_gate(
    state: RepositoryState,
) -> RepositoryState:

    approval = evaluate_human_approval(
        state.get(
            "code_review",
            {},
        ),
        state.get(
            "test_execution",
            {},
        ),
    )

    approval_status = approval.get(
        "status",
        "awaiting_human_approval",
    )

    if (
        approval_status
        == "no_changes_required"
    ):
        workflow_status = (
            "no_changes_required"
        )

    elif (
        approval_status
        == "blocked"
    ):
        workflow_status = (
            "blocked"
        )

    else:
        workflow_status = (
            "awaiting_human_approval"
        )

    return {
        **state,
        "human_approval": (
            approval
        ),
        "current_step": (
            "human_approval"
        ),
        "status": (
            workflow_status
        ),
    }


workflow = StateGraph(
    RepositoryState
)


workflow.add_node(
    "validate_repository",
    validate_repository,
)

workflow.add_node(
    "clone_repository",
    clone_repo,
)

workflow.add_node(
    "analyze_repository",
    analyze_repository_files,
)

workflow.add_node(
    "collect_repository_content",
    collect_repository_content,
)

workflow.add_node(
    "analyze_code_structure",
    analyze_code_structure,
)

workflow.add_node(
    "analyze_dependencies",
    analyze_dependencies,
)

workflow.add_node(
    "analyze_vulnerabilities",
    analyze_vulnerabilities,
)

workflow.add_node(
    "analyze_semgrep",
    analyze_semgrep,
)

workflow.add_node(
    "technical_debt_analysis",
    technical_debt_analysis,
)

workflow.add_node(
    "architecture_analysis",
    architecture_analysis,
)

workflow.add_node(
    "modernization_planning",
    modernization_planning,
)

workflow.add_node(
    "code_change_planning",
    code_change_planning,
)

workflow.add_node(
    "code_change_review",
    code_change_review,
)

workflow.add_node(
    "test_execution",
    test_execution,
)

workflow.add_node(
    "human_approval",
    human_approval_gate,
)


workflow.add_edge(
    START,
    "validate_repository",
)

workflow.add_edge(
    "validate_repository",
    "clone_repository",
)

workflow.add_edge(
    "clone_repository",
    "analyze_repository",
)

workflow.add_edge(
    "analyze_repository",
    "collect_repository_content",
)

workflow.add_edge(
    "collect_repository_content",
    "analyze_code_structure",
)

workflow.add_edge(
    "analyze_code_structure",
    "analyze_dependencies",
)

workflow.add_edge(
    "analyze_dependencies",
    "analyze_vulnerabilities",
)

workflow.add_edge(
    "analyze_vulnerabilities",
    "analyze_semgrep",
)

workflow.add_edge(
    "analyze_semgrep",
    "technical_debt_analysis",
)

workflow.add_edge(
    "technical_debt_analysis",
    "architecture_analysis",
)

workflow.add_edge(
    "architecture_analysis",
    "modernization_planning",
)

workflow.add_edge(
    "modernization_planning",
    "code_change_planning",
)

workflow.add_edge(
    "code_change_planning",
    "code_change_review",
)

workflow.add_edge(
    "code_change_review",
    "test_execution",
)

workflow.add_edge(
    "test_execution",
    "human_approval",
)

workflow.add_edge(
    "human_approval",
    END,
)


repository_analysis_graph = (
    workflow.compile()
)