/// <reference types="vite/client" />
import { useEffect, useState, type FormEvent } from 'react'

import './App.css'

const BACKEND_URL =
  import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'

const API_BASE = `${BACKEND_URL}/api/repositories`

const ANALYSIS_STAGES = [
  {
    key: 'repository_validation',
    label: 'Validate repository',
    detail: 'Checking the GitHub repository URL and request.',
  },
  {
    key: 'repository_clone',
    label: 'Clone repository',
    detail: 'Creating an isolated working copy for analysis.',
  },
  {
    key: 'repository_analysis',
    label: 'Scan repository',
    detail: 'Detecting languages, build tools and repository structure.',
  },
  {
    key: 'repository_content_collection',
    label: 'Collect evidence',
    detail: 'Selecting repository files and evidence for grounded analysis.',
  },
  {
    key: 'code_structure_analysis',
    label: 'Analyze code structure',
    detail: 'Inspecting classes, packages and source organization.',
  },
  {
    key: 'dependency_analysis',
    label: 'Analyze dependencies',
    detail: 'Resolving project dependencies and build metadata.',
  },
  {
    key: 'vulnerability_analysis',
    label: 'Check vulnerabilities',
    detail: 'Checking resolved dependencies for known vulnerabilities.',
  },
  {
    key: 'semgrep_analysis',
    label: 'Run static analysis',
    detail: 'Scanning the repository with Semgrep.',
  },
  {
    key: 'technical_debt_analysis',
    label: 'Analyze technical debt',
    detail: 'Evaluating maintainability, security and modernization signals.',
  },
  {
    key: 'architecture_analysis',
    label: 'Assess architecture',
    detail: 'Building an evidence-grounded architecture assessment.',
  },
  {
    key: 'modernization_planning',
    label: 'Plan modernization',
    detail: 'Creating the target-state modernization plan.',
  },
  {
    key: 'code_change_planning',
    label: 'Prepare code proposal',
    detail: 'Generating bounded repository changes when evidence supports them.',
  },
  {
    key: 'code_change_review',
    label: 'Independent review',
    detail: 'Reviewing the proposed change set against safety constraints.',
  },
  {
    key: 'test_execution',
    label: 'Run baseline tests',
    detail: 'Executing deterministic repository validation.',
  },
  {
    key: 'human_approval',
    label: 'Evaluate safety gate',
    detail: 'Determining whether human approval is required.',
  },
] as const

function formatElapsed(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60

  if (minutes === 0) {
    return `${seconds}s`
  }

  return `${minutes}m ${seconds.toString().padStart(2, '0')}s`
}

function stageState(
  currentStep: string | undefined,
  stageIndex: number,
) {
  if (
    !currentStep ||
    currentStep === 'queued' ||
    currentStep === 'initializing' ||
    currentStep === 'retrying'
  ) {
    return stageIndex === 0 ? 'active' : 'pending'
  }

  const completedIndex = ANALYSIS_STAGES.findIndex(
    (stage) => stage.key === currentStep,
  )

  if (completedIndex < 0) {
    return stageIndex === 0 ? 'active' : 'pending'
  }

  if (stageIndex <= completedIndex) {
    return 'complete'
  }

  if (stageIndex === completedIndex + 1) {
    return 'active'
  }

  return 'pending'
}


type Finding = {
  category?: string
  severity?: string
  confidence?: string
  finding?: string
  recommendation?: string
}

type ProposedChange = {
  file?: string
  change_type?: string
  title?: string
  reason?: string
  risk?: string
  automation_candidate?: boolean
  verification_required?: boolean
}

type AnalysisResult = {
  analysis_id: string
  repository_url: string
  status: string
  current_step?: string
  message?: string
  error?: string
  repository_name?: string | null
  primary_language?: string | null
  build_tools?: string[]
  frameworks?: string[]
  java_version?: string | null
  files_analyzed?: number
  class_count?: number
  dependency_count?: number
  vulnerability_count?: number
  semgrep_finding_count?: number
  technical_debt?: Finding[]
  architecture_assessment?: string

  modernization_plan?: {
    summary?: string
    target_state?: string
    priority?: string
  }

  code_change_proposal?: {
    summary?: string
    change_count?: number
    changes?: ProposedChange[]
    tests_to_run?: string[]
  }

  code_review?: {
    review_status?: string
    safe_to_apply?: boolean
    approved_change_count?: number
    changes_requested_count?: number
    rejected_change_count?: number
    summary?: string
  }

  test_execution?: {
    status?: string
    build_tool?: string
    project_count?: number
    reason?: string
    tests?: Array<{
      status?: string
      exit_code?: number | null
      command?: string[]
      project_path?: string
      build_tool?: string
      stderr?: string
    }>
  }

  human_approval?: {
    status?: string
    approved?: boolean
    reason?: string
    comment?: string
  }
}

type ActionResponse = {
  analysis_id?: string
  status?: string
  approved?: boolean
  message?: string

  patch_result?: {
    status?: string
    applied_count?: number
    failed_count?: number
  }

  post_patch_tests?: {
    status?: string
  }

  branch?: string
  pr_number?: number
  pr_url?: string
}

function statusClass(status?: string) {
  const value = status?.toLowerCase() ?? ''

  if (
    value.includes('passed') ||
    value.includes('approved') ||
    value.includes('validated') ||
    value.includes('created') ||
    value.includes('no_changes_required')
  ) {
    return 'status success'
  }

  if (
    value.includes('failed') ||
    value.includes('blocked') ||
    value.includes('rejected') ||
    value.includes('error')
  ) {
    return 'status danger'
  }

  return 'status warning'
}

function severityClass(severity?: string) {
  switch (severity?.toLowerCase()) {
    case 'critical':
    case 'high':
      return 'severity severity-high'

    case 'medium':
      return 'severity severity-medium'

    default:
      return 'severity severity-low'
  }
}

function App() {
  const [repositoryUrl, setRepositoryUrl] = useState('')

  const [analysis, setAnalysis] =
    useState<AnalysisResult | null>(null)

  const [actionResult, setActionResult] =
    useState<ActionResponse | null>(null)

  const [loading, setLoading] = useState(false)

  const [activeAction, setActiveAction] =
    useState('')

  const [error, setError] =
    useState('')

  const [elapsedSeconds, setElapsedSeconds] =
    useState(0)

  useEffect(() => {
    if (!loading) {
      return
    }

    const timer = window.setInterval(
      () => {
        setElapsedSeconds(
          (seconds) => seconds + 1,
        )
      },
      1000,
    )

    return () =>
      window.clearInterval(timer)
  }, [loading])

  async function parseResponse(response: Response) {
    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        data.detail ??
          data.message ??
          `Request failed with HTTP ${response.status}`,
      )
    }

    return data
  }

  async function analyzeRepository(
    event: FormEvent,
  ) {
    event.preventDefault()

    setLoading(true)
    setError('')
    setActionResult(null)
    setAnalysis(null)
    setElapsedSeconds(0)

    try {
      const response = await fetch(
        `${API_BASE}/analyze`,
        {
          method: 'POST',
          headers: {
            'Content-Type':
              'application/json',
          },
          body: JSON.stringify({
            repository_url:
              repositoryUrl.trim(),
          }),
        },
      )

      const job =
        await parseResponse(response)

      const analysisId =
        job.analysis_id

      if (!analysisId) {
        throw new Error(
          'Backend did not return an analysis ID.',
        )
      }

      setAnalysis({
        analysis_id: analysisId,
        repository_url:
          job.repository_url ?? repositoryUrl,
        status: job.status ?? 'queued',
        current_step: 'queued',
        message:
          job.message ??
          'Repository analysis is queued.',
      })

      while (true) {
        await new Promise((resolve) =>
          setTimeout(resolve, 3000),
        )

        const statusResponse =
          await fetch(
            `${API_BASE}/${analysisId}`,
          )

        const result =
          await parseResponse(
            statusResponse,
          )

        setAnalysis(result)

        if (
          result.status === 'processing' ||
          result.status === 'queued' ||
          result.status === 'started'
        ) {
          continue
        }

        if (
          result.status === 'failed'
        ) {
          throw new Error(
            result.error ??
              result.message ??
              'Repository analysis failed.',
          )
        }

        setAnalysis(result)
        break
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Repository analysis failed.',
      )
    } finally {
      setLoading(false)
    }
  }

  async function performAction(
    action:
      | 'approve'
      | 'reject'
      | 'apply'
      | 'publish',
  ) {
    if (!analysis?.analysis_id) {
      return
    }

    setActiveAction(action)
    setError('')
    setActionResult(null)

    try {
      const needsBody =
        action === 'approve' ||
        action === 'reject'

      const response = await fetch(
        `${API_BASE}/${analysis.analysis_id}/${action}`,
        {
          method: 'POST',

          headers: needsBody
            ? {
                'Content-Type':
                  'application/json',
              }
            : undefined,

          body: needsBody
            ? JSON.stringify({
                comment:
                  action === 'approve'
                    ? 'Approved from CodeShift AI dashboard.'
                    : 'Rejected from CodeShift AI dashboard.',
              })
            : undefined,
        },
      )

      const data =
        await parseResponse(response)

      setActionResult(data)

      setAnalysis((current) => {
        if (!current) {
          return current
        }

        if (action === 'approve') {
          return {
            ...current,
            status: 'approved',

            human_approval: {
              status: 'approved',
              approved: true,
              comment:
                'Approved from CodeShift AI dashboard.',
            },
          }
        }

        if (action === 'reject') {
          return {
            ...current,
            status: 'rejected',

            human_approval: {
              status: 'rejected',
              approved: false,
              comment:
                'Rejected from CodeShift AI dashboard.',
            },
          }
        }

        if (
          action === 'apply' &&
          data.status
        ) {
          return {
            ...current,
            status: data.status,
          }
        }

        if (
          action === 'publish' &&
          data.status
        ) {
          return {
            ...current,
            status: data.status,
          }
        }

        return current
      })
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : `${action} request failed.`,
      )
    } finally {
      setActiveAction('')
    }
  }

  const approved =
    analysis?.human_approval
      ?.approved === true

  const noChangesRequired =
    analysis?.status ===
      'no_changes_required' ||
    analysis?.human_approval
      ?.status ===
      'no_changes_required'

  const patchValidated =
    analysis?.status ===
      'patch_validated' ||
    actionResult?.status ===
      'patch_validated'

  const prCreated =
    analysis?.status ===
      'pull_request_created' ||
    actionResult?.status ===
      'pull_request_created'

  const humanGateComplete =
    approved ||
    noChangesRequired

  const canApprove =
    analysis?.human_approval
      ?.status ===
      'awaiting_human_approval'

  const approvalBlocked =
    analysis?.human_approval
      ?.status === 'blocked'

  const currentStep =
    analysis?.current_step ?? 'queued'

  const completedStageIndex =
    ANALYSIS_STAGES.findIndex(
      (stage) =>
        stage.key === currentStep,
    )

  const activeStageIndex =
    currentStep === 'retrying'
      ? 0
      : Math.min(
          Math.max(
            completedStageIndex + 1,
            0,
          ),
          ANALYSIS_STAGES.length - 1,
        )

  const activeStage =
    ANALYSIS_STAGES[activeStageIndex]

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">
            CS
          </div>

          <div>
            <div className="brand-name">
              CodeShift AI
            </div>

            <div className="brand-subtitle">
              Agentic Software Intelligence
            </div>
          </div>
        </div>

        <div className="topbar-actions">
          <span className="system-indicator">
            <span className="system-dot" />
            Safety gates enabled
          </span>

          <div className="topbar-badge">
            Modernization Platform
          </div>
        </div>
      </header>

      <main className="page">
        <section className="hero-section">
          <div className="hero-copy">
            <span className="eyebrow">
              Agentic software intelligence
            </span>

            <h1>
              Repository intelligence.
              <span> Safe modernization.</span>
            </h1>

            <p>
              CodeShift analyzes real repository evidence,
              identifies technical and security risk, proposes
              bounded changes, independently reviews them, and
              keeps a human in control before mutation.
            </p>

            <div className="hero-signals">
              <span>Evidence grounded</span>
              <span>Independent review</span>
              <span>Human approval</span>
              <span>Validated patching</span>
            </div>
          </div>

          <form
            className="analyze-card"
            onSubmit={analyzeRepository}
          >
            <div className="analyze-card-head">
              <div>
                <span className="section-label">
                  Repository intake
                </span>
                <h3>Start an analysis</h3>
              </div>

              <span className="terminal-badge">
                HTTPS · GitHub
              </span>
            </div>

            <label htmlFor="repository">
              GitHub repository URL
            </label>

            <div className="input-row">
              <input
                id="repository"
                type="url"
                value={repositoryUrl}
                onChange={(event) =>
                  setRepositoryUrl(
                    event.target.value,
                  )
                }
                placeholder="https://github.com/owner/repository"
                autoComplete="off"
                spellCheck={false}
                required
              />

              <button
                className="primary-button"
                type="submit"
                disabled={
                  loading ||
                  !repositoryUrl.trim()
                }
              >
                {loading
                  ? 'Analyzing...'
                  : 'Analyze repository'}
              </button>
            </div>

            <div className="input-help">
              Read-first workflow. Repository mutation is blocked
              until review, tests and explicit human approval succeed.
            </div>
          </form>
        </section>

        {error && (
          <div className="error-banner">
            <strong>
              Request failed
            </strong>

            <span>
              {error}
            </span>
          </div>
        )}

        {loading && (
          <section className="analysis-progress-card">
            <div className="progress-header">
              <div className="progress-heading">
                <div className="progress-orbit">
                  <span />
                  <span />
                  <span />
                </div>

                <div>
                  <span className="section-label">
                    Live analysis
                  </span>

                  <h2>
                    {currentStep === 'retrying'
                      ? 'Retrying automatically'
                      : 'CodeShift is working'}
                  </h2>

                  <p>
                    {analysis?.message ??
                      activeStage?.detail ??
                      'Preparing repository analysis.'}
                  </p>
                </div>
              </div>

              <div className="progress-runtime">
                <span>Elapsed</span>
                <strong>
                  {formatElapsed(
                    elapsedSeconds,
                  )}
                </strong>
              </div>
            </div>

            {currentStep === 'retrying' && (
              <div className="retry-notice">
                <span className="retry-icon">
                  {'\u21BB'}
                </span>

                <div>
                  <strong>
                    Temporary processing issue detected
                  </strong>
                  <p>
                    CodeShift is retrying this analysis automatically.
                    You do not need to submit the repository again.
                  </p>
                </div>
              </div>
            )}

            <div className="analysis-stage-grid">
              {ANALYSIS_STAGES.map(
                (stage, index) => {
                  const state =
                    stageState(
                      currentStep,
                      index,
                    )

                  return (
                    <div
                      className={`analysis-stage ${state}`}
                      key={stage.key}
                    >
                      <div className="stage-indicator">
                        {state === 'complete'
                          ? '\u2713'
                          : state === 'active'
                            ? (
                                <span className="mini-spinner" />
                              )
                            : index + 1}
                      </div>

                      <div className="stage-copy">
                        <strong>
                          {stage.label}
                        </strong>

                        <small>
                          {state === 'complete'
                            ? 'Complete'
                            : state === 'active'
                              ? stage.detail
                              : 'Waiting'}
                        </small>
                      </div>
                    </div>
                  )
                },
              )}
            </div>

            <div className="progress-footer">
              <span className="live-dot" />
              Live progress updates every few seconds
            </div>
          </section>
        )}

        {analysis && !loading && (
          <>
            <section className="workflow-card">
              <div>
                <span className="section-label">
                  Workflow
                </span>

                <h2>
                  Modernization pipeline
                </h2>
              </div>

              <div className="workflow">
                <div className="workflow-step complete">
                  <span>
                    1
                  </span>

                  <div>
                    <strong>
                      Analyzed
                    </strong>

                    <small>
                      Repository intelligence
                      complete
                    </small>
                  </div>
                </div>

                <div className="workflow-line" />

                <div className="workflow-step complete">
                  <span>
                    2
                  </span>

                  <div>
                    <strong>
                      Reviewed
                    </strong>

                    <small>
                      {analysis.code_review
                        ?.review_status ??
                        'Complete'}
                    </small>
                  </div>
                </div>

                <div className="workflow-line" />

                <div className="workflow-step complete">
                  <span>
                    3
                  </span>

                  <div>
                    <strong>
                      Tests
                    </strong>

                    <small>
                      {analysis.test_execution
                        ?.status ??
                        'Unknown'}
                    </small>
                  </div>
                </div>

                <div className="workflow-line" />

                <div
                  className={`workflow-step ${
                    humanGateComplete
                      ? 'complete'
                      : 'active'
                  }`}
                >
                  <span>
                    4
                  </span>

                  <div>
                    <strong>
                      Human approval
                    </strong>

                    <small>
                      {noChangesRequired
                        ? 'Not required'
                        : analysis
                            .human_approval
                            ?.status}
                    </small>
                  </div>
                </div>

                <div className="workflow-line" />

                <div
                  className={`workflow-step ${
                    patchValidated ||
                    noChangesRequired
                      ? 'complete'
                      : ''
                  }`}
                >
                  <span>
                    5
                  </span>

                  <div>
                    <strong>
                      Patch
                    </strong>

                    <small>
                      {noChangesRequired
                        ? 'Not required'
                        : patchValidated
                          ? 'Validated'
                          : 'Waiting'}
                    </small>
                  </div>
                </div>

                <div className="workflow-line" />

                <div
                  className={`workflow-step ${
                    prCreated ||
                    noChangesRequired
                      ? 'complete'
                      : ''
                  }`}
                >
                  <span>
                    6
                  </span>

                  <div>
                    <strong>
                      Pull request
                    </strong>

                    <small>
                      {noChangesRequired
                        ? 'Not required'
                        : prCreated
                          ? 'Created'
                          : 'Waiting'}
                    </small>
                  </div>
                </div>
              </div>
            </section>

            <section className="trust-banner">
              <div className="trust-icon">✓</div>
              <div>
                <strong>Evidence-grounded execution</strong>
                <p>
                  Proposed changes must survive deterministic safety checks,
                  independent review, baseline validation and the human gate
                  before CodeShift can modify repository state.
                </p>
              </div>
              <span>Human-in-the-loop</span>
            </section>

            {noChangesRequired && (
              <section className="result-card">
                <div>
                  <span className="section-label">
                    Analysis complete
                  </span>

                  <h3>
                    No repository changes required
                  </h3>

                  <p className="panel-copy">
                    CodeShift completed its
                    analysis and validation, but
                    no executable changes were
                    proposed. Human approval,
                    patch application and pull
                    request creation are not
                    required.
                  </p>
                </div>

                <span className="status success">
                  Complete
                </span>
              </section>
            )}

            <section className="summary-header">
              <div>
                <span className="section-label">
                  Analysis
                </span>

                <h2>
                  {analysis.repository_name ??
                    'Repository'}
                </h2>

                <a
                  href={
                    analysis.repository_url
                  }
                  target="_blank"
                  rel="noreferrer"
                >
                  {
                    analysis.repository_url
                  }
                </a>
              </div>

              <span
                className={statusClass(
                  analysis.status,
                )}
              >
                {noChangesRequired
                  ? 'Analysis complete'
                  : analysis.status}
              </span>
            </section>

            <section className="metrics-grid">
              <div className="metric-card">
                <span>
                  Files analyzed
                </span>

                <strong>
                  {analysis.files_analyzed ??
                    0}
                </strong>
              </div>

              <div className="metric-card">
                <span>
                  Classes
                </span>

                <strong>
                  {analysis.class_count ?? 0}
                </strong>
              </div>

              <div className="metric-card">
                <span>
                  Dependencies
                </span>

                <strong>
                  {analysis.dependency_count ??
                    0}
                </strong>
              </div>

              <div className="metric-card">
                <span>
                  Vulnerabilities
                </span>

                <strong>
                  {analysis
                    .vulnerability_count ??
                    0}
                </strong>
              </div>

              <div className="metric-card">
                <span>
                  Semgrep findings
                </span>

                <strong>
                  {analysis
                    .semgrep_finding_count ??
                    0}
                </strong>
              </div>
            </section>

            <section className="content-grid">
              <article className="panel">
                <div className="panel-heading">
                  <div>
                    <span className="section-label">
                      Repository
                    </span>

                    <h3>
                      Technology profile
                    </h3>
                  </div>
                </div>

                <div className="detail-list">
                  <div>
                    <span>
                      Language
                    </span>

                    <strong>
                      {analysis
                        .primary_language ??
                        'Not detected'}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Java
                    </span>

                    <strong>
                      {analysis.java_version ??
                        'N/A'}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Build tools
                    </span>

                    <strong>
                      {analysis.build_tools
                        ?.join(', ') ||
                        'None'}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Frameworks
                    </span>

                    <strong>
                      {analysis.frameworks
                        ?.join(', ') ||
                        'None'}
                    </strong>
                  </div>
                </div>
              </article>

              <article className="panel">
                <div className="panel-heading">
                  <div>
                    <span className="section-label">
                      Automated review
                    </span>

                    <h3>
                      Safety decision
                    </h3>
                  </div>

                  <span
                    className={statusClass(
                      analysis.code_review
                        ?.review_status,
                    )}
                  >
                    {analysis.code_review
                      ?.review_status ??
                      'unknown'}
                  </span>
                </div>

                <p className="panel-copy">
                  {analysis.code_review
                    ?.summary ??
                    'No reviewer summary available.'}
                </p>

                <div className="review-stats">
                  <div>
                    <strong>
                      {analysis.code_review
                        ?.approved_change_count ??
                        0}
                    </strong>

                    <span>
                      Approved
                    </span>
                  </div>

                  <div>
                    <strong>
                      {analysis.code_review
                        ?.changes_requested_count ??
                        0}
                    </strong>

                    <span>
                      Changes requested
                    </span>
                  </div>

                  <div>
                    <strong>
                      {analysis.code_review
                        ?.rejected_change_count ??
                        0}
                    </strong>

                    <span>
                      Rejected
                    </span>
                  </div>
                </div>
              </article>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="section-label">
                    Technical debt
                  </span>

                  <h3>
                    Detected findings
                  </h3>
                </div>

                <span className="count-badge">
                  {analysis.technical_debt
                    ?.length ?? 0}
                </span>
              </div>

              <div className="findings-list">
                {analysis.technical_debt?.map(
                  (finding, index) => (
                    <div
                      className="finding"
                      key={`${finding.finding}-${index}`}
                    >
                      <div className="finding-top">
                        <div>
                          <span className="finding-category">
                            {
                              finding.category
                            }
                          </span>

                          <h4>
                            {
                              finding.finding
                            }
                          </h4>
                        </div>

                        <span
                          className={severityClass(
                            finding.severity,
                          )}
                        >
                          {finding.severity ??
                            'unknown'}
                        </span>
                      </div>

                      <p>
                        {
                          finding.recommendation
                        }
                      </p>
                    </div>
                  ),
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="section-label">
                    Modernization
                  </span>

                  <h3>
                    Target state
                  </h3>
                </div>

                <span className="priority-badge">
                  {analysis
                    .modernization_plan
                    ?.priority ??
                    'unknown'}
                </span>
              </div>

              <p className="lead">
                {analysis
                  .modernization_plan
                  ?.summary}
              </p>

              <p className="panel-copy">
                {analysis
                  .modernization_plan
                  ?.target_state}
              </p>
            </section>

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="section-label">
                    Proposed patch
                  </span>

                  <h3>
                    Code changes
                  </h3>
                </div>

                <span className="count-badge">
                  {analysis
                    .code_change_proposal
                    ?.change_count ??
                    0}
                </span>
              </div>

              <p className="panel-copy">
                {analysis
                  .code_change_proposal
                  ?.summary}
              </p>

              <div className="changes-list">
                {analysis
                  .code_change_proposal
                  ?.changes?.map(
                    (change, index) => (
                      <div
                        className="change-card"
                        key={`${change.file}-${index}`}
                      >
                        <div className="change-heading">
                          <div>
                            <span className="change-type">
                              {
                                change.change_type
                              }
                            </span>

                            <h4>
                              {
                                change.title
                              }
                            </h4>

                            <code>
                              {
                                change.file
                              }
                            </code>
                          </div>

                          <span
                            className={severityClass(
                              change.risk,
                            )}
                          >
                            {change.risk ??
                              'unknown'}{' '}
                            risk
                          </span>
                        </div>

                        <p>
                          {change.reason}
                        </p>
                      </div>
                    ),
                  )}
              </div>
            </section>

            <section className="content-grid">
              <article className="panel">
                <div className="panel-heading">
                  <div>
                    <span className="section-label">
                      Validation
                    </span>

                    <h3>
                      Baseline tests
                    </h3>
                  </div>

                  <span
                    className={statusClass(
                      analysis.test_execution
                        ?.status,
                    )}
                  >
                    {analysis.test_execution
                      ?.status ??
                      'unknown'}
                  </span>
                </div>

                <div className="detail-list">
                  <div>
                    <span>
                      Build tools
                    </span>

                    <strong>
                      {analysis
                        .test_execution
                        ?.build_tool ??
                        'N/A'}
                    </strong>
                  </div>

                  <div>
                    <span>
                      Projects validated
                    </span>

                    <strong>
                      {analysis
                        .test_execution
                        ?.project_count ??
                        analysis
                          .test_execution
                          ?.tests
                          ?.length ??
                        0}
                    </strong>
                  </div>
                </div>

                {analysis
                  .test_execution
                  ?.reason && (
                  <p className="validation-summary">
                    {analysis
                      .test_execution
                      .reason}
                  </p>
                )}

                {analysis
                  .test_execution
                  ?.tests &&
                  analysis.test_execution
                    .tests.length > 0 && (
                    <div className="validation-projects">
                      {analysis
                        .test_execution
                        .tests.map(
                          (test, index) => {
                            const command =
                              test.command
                                ?.map((part) => {
                                  const pieces =
                                    part.split(
                                      /[\\/]/,
                                    )

                                  return pieces[
                                    pieces.length -
                                      1
                                  ]
                                })
                                .join(' ') ??
                              'N/A'

                            const errorText =
                              test.stderr
                                ?.trim()

                            return (
                              <div
                                className="validation-project"
                                key={`${test.project_path ?? 'project'}-${index}`}
                              >
                                <div className="validation-project-head">
                                  <div>
                                    <strong>
                                      {test.project_path ??
                                        '.'}
                                    </strong>
                                    <small>
                                      {test.build_tool ??
                                        'Build'}
                                    </small>
                                  </div>

                                  <span
                                    className={statusClass(
                                      test.status,
                                    )}
                                  >
                                    {test.status ??
                                      'unknown'}
                                  </span>
                                </div>

                                <div className="validation-project-meta">
                                  <span>
                                    Exit code:{' '}
                                    <strong>
                                      {test.exit_code ??
                                        'N/A'}
                                    </strong>
                                  </span>

                                  <code>
                                    {command}
                                  </code>
                                </div>

                                {errorText &&
                                  test.status !==
                                    'passed' && (
                                    <pre className="validation-error">
                                      {errorText.slice(
                                        -1200,
                                      )}
                                    </pre>
                                  )}
                              </div>
                            )
                          },
                        )}
                    </div>
                  )}
              </article>

              <article className="panel">
                <div className="panel-heading">
                  <div>
                    <span className="section-label">
                      Human gate
                    </span>

                    <h3>
                      {noChangesRequired
                        ? 'Approval not required'
                        : approvalBlocked
                          ? 'Validation blocked'
                          : 'Approval'}
                    </h3>
                  </div>

                  <span
                    className={statusClass(
                      analysis
                        .human_approval
                        ?.status,
                    )}
                  >
                    {noChangesRequired
                      ? 'Complete'
                      : analysis
                          .human_approval
                          ?.status}
                  </span>
                </div>

                <p className="panel-copy">
                  {analysis
                    .human_approval
                    ?.reason ??
                    analysis
                      .human_approval
                      ?.comment ??
                    'A human decision is required before applying changes.'}
                </p>
              </article>
            </section>

            <section className="actions-panel">
              <div>
                <span className="section-label">
                  Controlled execution
                </span>

                <h3>
                  Repository actions
                </h3>

                <p>
                  {noChangesRequired
                    ? 'No repository actions are required because CodeShift did not propose any executable changes.'
                    : approvalBlocked
                      ? analysis.human_approval?.reason ??
                        'Baseline validation must pass before human approval.'
                      : 'Changes are never published until the automated review, validation and human approval gates succeed.'}
                </p>
              </div>

              <div className="action-buttons">
                {noChangesRequired && (
                  <span className="status success">
                    No action required
                  </span>
                )}

                {approvalBlocked && (
                  <span className="status danger">
                    Approval unavailable
                  </span>
                )}

                {canApprove && (
                    <>
                      <button
                        className="secondary-button reject-button"
                        disabled={Boolean(
                          activeAction,
                        )}
                        onClick={() =>
                          performAction(
                            'reject',
                          )
                        }
                      >
                        {activeAction ===
                        'reject'
                          ? 'Rejecting...'
                          : 'Reject'}
                      </button>

                      <button
                        className="primary-button"
                        disabled={Boolean(
                          activeAction,
                        )}
                        onClick={() =>
                          performAction(
                            'approve',
                          )
                        }
                      >
                        {activeAction ===
                        'approve'
                          ? 'Approving...'
                          : 'Approve changes'}
                      </button>
                    </>
                  )}

                {!noChangesRequired &&
                  approved &&
                  !patchValidated && (
                    <button
                      className="primary-button"
                      disabled={Boolean(
                        activeAction,
                      )}
                      onClick={() =>
                        performAction(
                          'apply',
                        )
                      }
                    >
                      {activeAction ===
                      'apply'
                        ? 'Applying patch...'
                        : 'Apply validated patch'}
                    </button>
                  )}

                {!noChangesRequired &&
                  patchValidated &&
                  !prCreated && (
                    <button
                      className="primary-button publish-button"
                      disabled={Boolean(
                        activeAction,
                      )}
                      onClick={() =>
                        performAction(
                          'publish',
                        )
                      }
                    >
                      {activeAction ===
                      'publish'
                        ? 'Publishing...'
                        : 'Publish pull request'}
                    </button>
                  )}
              </div>
            </section>

            {actionResult && (
              <section className="result-card">
                <div>
                  <span className="section-label">
                    Latest action
                  </span>

                  <h3>
                    {actionResult.message ??
                      actionResult.status}
                  </h3>
                </div>

                <span
                  className={statusClass(
                    actionResult.status,
                  )}
                >
                  {actionResult.status}
                </span>

                {actionResult.patch_result && (
                  <div className="result-details">
                    <span>
                      Applied:{' '}
                      <strong>
                        {actionResult
                          .patch_result
                          .applied_count ??
                          0}
                      </strong>
                    </span>

                    <span>
                      Failed:{' '}
                      <strong>
                        {actionResult
                          .patch_result
                          .failed_count ??
                          0}
                      </strong>
                    </span>

                    <span>
                      Post-patch tests:{' '}
                      <strong>
                        {actionResult
                          .post_patch_tests
                          ?.status ??
                          'unknown'}
                      </strong>
                    </span>
                  </div>
                )}

                {actionResult.pr_url && (
                  <a
                    className="pr-link"
                    href={
                      actionResult.pr_url
                    }
                    target="_blank"
                    rel="noreferrer"
                  >
                    Open pull request #
                    {
                      actionResult.pr_number
                    }{' '}
                    →
                  </a>
                )}
              </section>
            )}

            <section className="panel">
              <div className="panel-heading">
                <div>
                  <span className="section-label">
                    Architecture
                  </span>

                  <h3>
                    Assessment
                  </h3>
                </div>
              </div>

              <p className="panel-copy">
                Architecture assessment is generated before baseline
                test execution. Final validation results are shown in
                the Validation section above.
              </p>

              <pre className="architecture-text">
                {
                  analysis.architecture_assessment
                }
              </pre>
            </section>
          </>
        )}
      </main>

      <footer className="footer">
        CodeShift AI · Evidence-grounded agentic modernization · Human-controlled execution
      </footer>
    </div>
  )
}

export default App