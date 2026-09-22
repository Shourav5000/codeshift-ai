# CodeShift AI

CodeShift AI is an AI-assisted software modernization platform that analyzes a GitHub repository, finds technical debt and security issues, proposes code changes, reviews those changes, runs tests, and requires human approval before anything is applied.

The goal is simple: help developers understand and modernize a codebase without giving an AI system unrestricted control over the repository.

---

## What It Does

CodeShift AI can:

- analyze a GitHub repository
- detect languages, frameworks, build tools, Java versions, and project structure
- inspect dependencies
- scan for known vulnerabilities
- run Semgrep static analysis
- identify technical debt
- review software architecture
- create a modernization plan
- propose code changes
- review proposed changes before applying them
- run baseline tests
- require explicit human approval
- apply approved patches
- run tests again after the patch
- create a Git branch and pull request

The workflow is designed so that AI can recommend and prepare changes, but a human stays in control of the final decision.

---

## How the Workflow Works

```text
GitHub Repository
       ↓
Repository Analysis
       ↓
Architecture + Technical Debt Analysis
       ↓
Dependency + Security Scanning
       ↓
Modernization Plan
       ↓
Proposed Code Changes
       ↓
Independent Review
       ↓
Baseline Tests
       ↓
Human Approval
       ↓
Patch Application
       ↓
Post-Patch Tests
       ↓
GitHub Pull Request
```

---

## Why I Built It

Modernizing an existing application is usually more difficult than building a new one.

Before changing anything, developers need to understand:

- the current architecture
- dependencies
- security problems
- technical debt
- build configuration
- testing behavior
- the risk of each proposed change

CodeShift AI brings those steps into one workflow.

Instead of asking an LLM to simply "rewrite this project," CodeShift first gathers repository evidence, analyzes it, reviews proposed changes, validates the project, and requires a human decision before modifying the codebase.

---

## Tech Stack

### Backend

- **Python 3.12**
- **FastAPI** for REST APIs
- **LangGraph** for the multi-step agent workflow
- **LangChain** for LLM integration
- **OpenAI API** for AI reasoning and code analysis
- **Pydantic** for request and response models
- **Git CLI** for repository operations

### Frontend

- **React**
- **TypeScript**
- **Vite**
- **CSS**
- Responsive dashboard for desktop, tablet, and mobile

### Security and Code Analysis

- **Semgrep** for static analysis
- **OSV** for known vulnerability lookup
- **Maven dependency resolution**
- Custom repository scanners
- Custom deterministic safety checks

### GitHub Integration

- GitHub REST API
- Branch creation
- File updates
- Commit creation
- Pull request creation

### Local Persistence

CodeShift stores analysis data and cloned workspaces locally under:

```text
backend/.codeshift/
```

This allows analysis state and repository workspaces to survive process restarts.

---

## Main Components

### Repository Scanner

Collects basic information about the project, including:

- programming languages
- build tools
- frameworks
- Java version
- test structure
- file inventory

### Architecture Agent

Reviews the repository structure and creates an architecture assessment based on the files that were actually found.

### Technical Debt Agent

Looks for maintainability problems, outdated patterns, testing gaps, and modernization opportunities.

### Dependency Scanner

Inspects project dependencies and resolves Maven dependency information.

### Vulnerability Scanner

Checks dependency versions against OSV vulnerability data.

### Semgrep Scanner

Runs static analysis rules against the repository and returns security and code-quality findings.

### Modernization Planner

Creates a proposed target state and modernization plan based on the repository analysis.

### Code Change Agent

Generates bounded code changes using repository evidence.

It also includes additional safety checks to avoid unsupported or speculative changes.

### Reviewer Agent

Reviews the proposed changes separately before they are allowed to continue through the pipeline.

### Test Runner

Runs project tests before and after a patch is applied.

### Human Approval Gate

Even if the automated review and tests pass, CodeShift still requires explicit human approval before modifying the repository.

### Patch Service

Applies only approved and validated changes.

### GitHub Publish Service

Creates a branch, commits the changes, and can open a pull request.

---

## Safety Design

One of the main goals of this project was to avoid giving the AI unrestricted control.

CodeShift separates the process into several stages:

```text
Repository Evidence
        ↓
AI Proposal
        ↓
Safety Checks
        ↓
Independent Review
        ↓
Tests
        ↓
Human Approval
        ↓
Patch
        ↓
Post-Patch Tests
        ↓
Pull Request
```

Some of the safety checks include:

- blocking unsupported dependency versions
- preventing invented GitHub Action SHAs
- avoiding unsupported Kubernetes security changes
- checking for sensitive credential-related changes
- applying only reviewer-approved changes
- requiring successful validation before publishing

This makes the system more controlled and easier to inspect.

---

## Example Test

I tested CodeShift against the Spring PetClinic repository.

The analysis detected:

- 132 files
- 45 Java classes
- 173 dependencies
- 6 known vulnerability findings
- 16 Semgrep findings

CodeShift then proposed four safe changes, including:

- a PostgreSQL JDBC dependency update
- Kubernetes `allowPrivilegeEscalation: false` hardening

The proposed changes passed review and baseline tests.

After human approval, CodeShift applied the patch and the post-patch tests passed successfully.

This test helped validate the complete workflow from repository analysis through patch validation.

---

## Project Structure

```text
codeshift-ai/
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   ├── graphs/
│   │   ├── models/
│   │   ├── services/
│   │   └── main.py
│   ├── pyproject.toml
│   └── uv.lock
│
├── frontend/
│   ├── src/
│   ├── public/
│   └── package.json
│
└── README.md
```

---

## Running the Project Locally

### Requirements

You will need:

- Python 3.12+
- `uv`
- Node.js
- Git
- Java 21+
- Maven or Maven Wrapper
- Semgrep

---

### Backend

```bash
cd backend
uv sync
```

Create a file named:

```text
backend/.env
```

Example:

```env
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_token
```

Do not commit the `.env` file.

Start the backend:

```bash
uv run uvicorn app.main:app
```

API:

```text
http://127.0.0.1:8000
```

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

---

### Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

---

## Current Status

The main CodeShift workflow is working end to end.

Implemented:

- repository analysis
- architecture analysis
- technical debt analysis
- dependency scanning
- vulnerability scanning
- Semgrep analysis
- modernization planning
- code change generation
- automated review
- baseline testing
- human approval
- patch application
- post-patch validation
- local persistence
- GitHub branch creation
- pull request publishing
- responsive frontend

---

## Current Limitations

CodeShift is currently a portfolio and development project, not a production multi-user SaaS platform.

The main future improvements would be:

- sandboxed build and test execution
- database-backed persistence
- authentication and user management
- background jobs
- stronger GitHub retry and conflict handling
- better audit history
- Docker deployment
- production observability
- automatic cleanup of old workspaces

The most important production security improvement would be isolating Maven and Gradle execution inside containers or another sandbox because cloned repositories can contain untrusted build scripts.

---

## Future Ideas

Possible future extensions include:

- Docker-based isolated repository execution
- PostgreSQL and pgvector
- Redis-backed background jobs
- multi-repository analysis
- repository history analysis
- organization-level dashboards
- richer evidence and action tracing
- CI/CD integrations
- cloud deployment

---

## Author

**Shourav Kumar Mandal**

Software engineer interested in Java, Spring Boot, cloud modernization, AI-assisted software engineering, and enterprise application architecture.
