from pydantic import BaseModel, Field, HttpUrl


class RepositoryAnalysisRequest(BaseModel):
    repository_url: HttpUrl


class RepositoryAnalysisResponse(BaseModel):
    analysis_id: str

    repository_url: str
    status: str

    repository_name: str | None = None
    primary_language: str | None = None

    languages: dict[str, int] = Field(
        default_factory=dict
    )

    frameworks: list[str] = Field(
        default_factory=list
    )

    build_tools: list[str] = Field(
        default_factory=list
    )

    java_version: str | None = None

    has_tests: bool = False

    files_analyzed: int = 0

    code_structure: dict = Field(
        default_factory=dict
    )

    class_count: int = 0

    dependency_analysis: dict = Field(
        default_factory=dict
    )

    dependency_count: int = 0

    vulnerability_analysis: dict = Field(
        default_factory=dict
    )

    vulnerability_count: int = 0

    semgrep_analysis: dict = Field(
        default_factory=dict
    )

    semgrep_finding_count: int = 0

    technical_debt: list[dict] = Field(
        default_factory=list
    )

    architecture_assessment: str | None = None

    modernization_plan: dict = Field(
        default_factory=dict
    )

    code_change_proposal: dict = Field(
        default_factory=dict
    )

    code_review: dict = Field(
        default_factory=dict
    )

    test_execution: dict = Field(
        default_factory=dict
    )

    human_approval: dict = Field(
        default_factory=dict
    )

    message: str


class ApprovalActionRequest(BaseModel):
    comment: str | None = None


class ApprovalDecisionResponse(BaseModel):
    analysis_id: str
    status: str
    approved: bool
    comment: str | None = None
    message: str


class PatchApplicationResponse(BaseModel):
    analysis_id: str
    status: str

    patch_result: dict = Field(
        default_factory=dict
    )

    post_patch_tests: dict = Field(
        default_factory=dict
    )

    message: str

class PublishResponse(BaseModel):
    analysis_id: str
    status: str

    branch: str | None = None

    local_commit_sha: str | None = None
    remote_commit_sha: str | None = None

    default_branch: str | None = None

    pr_number: int | None = None
    pr_url: str | None = None

    message: str