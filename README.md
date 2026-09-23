# CodeShift AI

**Agentic Software Intelligence & Modernization Platform**

CodeShift AI is a full-stack AI-assisted software modernization platform that analyzes GitHub repositories, builds evidence about a codebase, identifies technical debt and security risk, proposes bounded changes, independently reviews those changes, validates the repository, and keeps a human in control before repository mutation.

> AI should help engineers understand and modernize software, but code changes should remain evidence-grounded, reviewable, testable, and explicitly controlled.

## Live Application

**Production:** https://codeshiftai.dev

**Backend health:** https://d381c47qj4bdxn.cloudfront.net/health

The frontend is hosted on AWS Amplify behind the custom `codeshiftai.dev` domain. The backend runs as a Dockerized FastAPI service on Amazon ECS with AWS Fargate.

> CodeShift AI is a portfolio and engineering demonstration project. Cloud resources may be restricted, scaled down, or changed outside demonstration periods.

---

## What CodeShift AI Does

CodeShift accepts a GitHub repository URL and can:

- validate and clone a repository
- inventory repository files and source structure
- detect languages, frameworks, build systems, and Java versions
- discover nested Maven and Gradle projects
- analyze mixed Java/Kotlin repositories
- resolve dependencies
- check dependencies against OSV
- run Semgrep static analysis
- identify technical debt and maintainability concerns
- generate an evidence-grounded architecture assessment
- create a modernization plan
- propose bounded code changes
- independently review proposed changes
- run baseline validation before mutation
- show validation results per discovered build project
- require explicit human approval before mutation
- apply approved patches
- rerun validation after patching
- create Git branches and commits
- publish validated changes through GitHub pull requests
- retry GitHub publishing without reapplying a validated patch

---

## End-to-End Workflow

```text
GitHub Repository
        |
        v
Repository Validation
        |
        v
Repository Clone
        |
        v
Repository Intelligence
        |
        +--> Languages / Frameworks / Java Version
        +--> Nested Maven / Gradle Projects
        +--> Source / Test Structure
        |
        v
Dependency Analysis
        |
        v
OSV Vulnerability Scan
        |
        v
Semgrep Static Analysis
        |
        v
Technical Debt Analysis
        |
        v
Architecture Assessment
        |
        v
Modernization Planning
        |
        v
Bounded Code Change Proposal
        |
        v
Independent AI Review
        |
        v
Baseline Build / Test Validation
        |
        v
Human Approval Gate
        |
        v
Patch Application
        |
        v
Post-Patch Validation
        |
        v
Git Branch + Commit
        |
        v
GitHub Publish
        |
        v
Pull Request Created
```

If the available evidence does not justify a repository change, CodeShift can safely finish with `no_changes_required` instead of manufacturing a patch.

---

## Verified End-to-End Result

The complete workflow has been exercised through successful GitHub pull-request creation using a writable fork of Spring's `gs-rest-service`.

Verified stages included:

- repository analysis
- mixed Java/Kotlin detection
- Java 17 detection
- Spring Boot detection
- nested Maven and Gradle project discovery
- dependency resolution
- OSV vulnerability scanning
- Semgrep static analysis
- technical-debt analysis
- architecture assessment
- modernization planning
- bounded change proposal
- independent automated review
- validation across four build projects
- human approval
- patch application
- post-patch validation
- Git branch and commit creation
- GitHub publishing
- pull-request creation

Final workflow state:

```text
PULL_REQUEST_CREATED
```

Verified pull request:

https://github.com/Shourav5000/gs-rest-service/pull/1

---

## GitHub Publishing and Repository Access

Analysis and publishing intentionally have different permission requirements.

### Analysis-only use

CodeShift can analyze public GitHub repositories without write access. This includes repository intelligence, dependency analysis, vulnerability scanning, Semgrep, architecture assessment, modernization planning, proposal generation, review, and baseline validation.

### Publishing changes

Publishing requires write access to the repository where CodeShift creates its branch.

For a **fine-grained GitHub personal access token**, use:

```text
Repository access:
Only select repositories
```

Recommended repository permissions:

```text
Contents       Read and write
Pull requests  Read and write
Metadata       Read-only
```

No account-level permissions are required for the current workflow.

### Repositories you own

If the token can write to the analyzed repository, CodeShift can:

1. create or reuse a CodeShift branch
2. publish validated file changes
3. open a pull request against the default branch

### Repositories you do not own

For an upstream repository where the token does not have write access, create a fork under the authenticated GitHub account.

Example:

```text
Upstream:
spring-guides/gs-rest-service

Writable fork:
Shourav5000/gs-rest-service
```

Add the fork to the token's selected repositories and grant the permissions above.

For the simplest workflow, analyze the writable fork directly:

```text
https://github.com/Shourav5000/gs-rest-service
```

The publishing service also supports using an existing writable fork when the upstream repository itself is not writable.

### Publish retries

A GitHub permission failure does not invalidate an already validated patch. After repository access is corrected, CodeShift can retry publishing without intentionally reapplying the patch.

---

## Production AWS Architecture

```text
                         Route 53
                       codeshiftai.dev
                              |
                              v
                    +-------------------+
                    |   AWS Amplify     |
                    | React / TypeScript|
                    +-------------------+
                              |
                              | HTTPS API calls
                              v
                    +-------------------+
                    | Amazon CloudFront |
                    +-------------------+
                              |
                              v
                    +-------------------+
                    | Application Load  |
                    |     Balancer       |
                    +-------------------+
                              |
                              v
               +--------------------------------+
               | Amazon ECS on AWS Fargate     |
               | Dockerized FastAPI Application |
               | API + SQS Analysis Worker      |
               +--------------------------------+
                       |               |
                       |               |
                       v               v
              +----------------+   +----------------+
              | Amazon RDS     |   | Amazon SQS     |
              | PostgreSQL     |   | Analysis Jobs  |
              +----------------+   +----------------+

Additional AWS services:
- Amazon ECR
- AWS Secrets Manager
- Amazon CloudWatch
- AWS IAM
- Amazon VPC
- AWS Security Groups
```

### AWS Services Used

- **Route 53** for the custom domain and DNS
- **AWS Amplify** for React hosting and deployment
- **Amplify managed SSL** for HTTPS
- **CloudFront** for the public backend HTTPS endpoint
- **Application Load Balancer** for backend traffic routing
- **ECS** for container orchestration
- **Fargate** for serverless container execution
- **ECR** for Docker image storage
- **RDS for PostgreSQL** for persistent analysis state
- **SQS** for durable asynchronous analysis jobs
- **Secrets Manager** for runtime secrets
- **CloudWatch Logs** for application and worker logging
- **IAM** for service and task permissions
- **VPC** for application networking
- **Security Groups** for network isolation
- **AWS CLI** for deployment and operational validation

The ECS task is not directly exposed publicly on port `8000`; backend ingress is routed through the Application Load Balancer.

---

## Asynchronous Processing and Reliability

Repository analysis can take longer than a normal HTTP request, so CodeShift uses an asynchronous job architecture.

```text
Frontend
   |
   | POST /analyze
   v
FastAPI
   |
   | enqueue
   v
Amazon SQS
   |
   v
Analysis Worker
   |
   +--> LangGraph workflow
   +--> repository scanners
   +--> dependency analysis
   +--> Semgrep
   +--> LLM analysis
   +--> test execution
   |
   v
PostgreSQL analysis state
   ^
   |
Frontend polls analysis status
```

Reliability features include:

- durable SQS-backed jobs
- automatic retry handling
- SQS visibility-timeout extension
- per-stage progress persistence
- live frontend polling
- elapsed-time display
- retry-state messaging
- analysis timeout protection
- bounded OpenAI retries and request timeouts
- CloudWatch stage and worker logs

The current portfolio deployment runs the SQS consumer alongside FastAPI inside the ECS task.

---

## Live Analysis Experience

The frontend shows the active pipeline in real time.

Stages:

1. Validate repository
2. Clone repository
3. Scan repository
4. Collect evidence
5. Analyze code structure
6. Analyze dependencies
7. Check vulnerabilities
8. Run static analysis
9. Analyze technical debt
10. Assess architecture
11. Plan modernization
12. Prepare code proposal
13. Independent review
14. Run baseline tests
15. Evaluate safety gate

Completed, active, pending, retry, and elapsed-time states are surfaced directly in the UI.

---

## Multi-Project and Mixed-Language Support

CodeShift recursively discovers:

- `pom.xml`
- `build.gradle`
- `build.gradle.kts`
- Maven Wrapper files
- Gradle Wrapper files
- Java toolchain configuration
- Spring Boot signals
- nested source and test directories

### Mixed Java/Kotlin repositories

Java structure analysis runs whenever Java exists in the language inventory, even if Kotlin is detected as the primary language.

The Java scanner can identify:

- classes
- controllers
- services
- repositories
- entities
- configuration classes
- components
- mapped superclasses
- test classes
- packages
- methods
- annotations

### Per-project validation

CodeShift reports each discovered build project separately with:

- project path
- build tool
- command
- status
- exit code
- error output when applicable

This prevents one successful module from hiding another module's failure.

---

## Technology Stack

### Backend

- Python 3.12
- FastAPI
- Uvicorn
- Pydantic
- Pydantic Settings
- SQLAlchemy
- psycopg
- PostgreSQL
- boto3
- Git CLI
- uv

### AI / Agentic Orchestration

- LangGraph
- LangChain
- OpenAI API
- stateful multi-stage workflow
- independent proposal review
- evidence-grounded architecture analysis
- technical-debt analysis
- modernization planning
- bounded code-change generation
- human-in-the-loop approval

### Frontend

- React 19
- React DOM 19
- TypeScript 6
- Vite 8
- HTML5
- CSS3
- Fetch API
- responsive dashboard UI
- live asynchronous polling

### Repository / Build Analysis

- Git
- Maven
- Maven Wrapper
- Gradle
- Gradle Wrapper
- Java / OpenJDK 17
- recursive build discovery
- Java version detection
- Spring Boot detection
- mixed Java/Kotlin analysis
- multi-project validation

### Security / Static Analysis

- Semgrep
- OSV
- dependency vulnerability analysis
- deterministic safety checks
- pre-patch validation
- post-patch validation
- CORS allow-listing

### Docker / Containers

- Docker
- Docker Desktop
- Docker Compose
- Debian Bookworm-based Python container
- OpenJDK 17 inside the backend image
- Maven inside the backend image
- Semgrep inside the backend image
- Amazon ECR
- Amazon ECS
- AWS Fargate

### AWS / Cloud

- Route 53
- Amplify
- CloudFront
- Application Load Balancer
- ECS
- Fargate
- ECR
- RDS for PostgreSQL
- SQS
- Secrets Manager
- CloudWatch
- IAM
- VPC
- Security Groups
- AWS CLI

### GitHub Integration

- GitHub REST API
- repository cloning
- branch creation
- repository file updates
- commit creation
- pull-request creation
- fine-grained personal access tokens
- selected-repository access
- retryable publishing
- fork-aware publishing

### Development Tooling

- PowerShell
- Postman
- Swagger / OpenAPI
- GitHub
- Git
- npm
- TypeScript compiler
- Vite production builds
- Python import / bytecode validation
- Docker image validation
- health-check validation

---

## Core Components

### Repository Scanner

Detects languages, frameworks, build systems, Java versions, tests, nested projects, and source structure.

### Repository Content Collector

Collects repository evidence used by downstream agents.

### Code Structure Scanner

Analyzes Java structure, including Java code inside mixed-language repositories.

### Dependency Scanner

Discovers dependency manifests and resolves dependencies across supported nested projects.

### Vulnerability Scanner

Queries OSV using resolved dependency versions.

### Semgrep Scanner

Runs static analysis over the cloned repository.

### Technical Debt Agent

Evaluates maintainability, testing gaps, security findings, and modernization opportunities.

### Architecture Agent

Produces an architecture assessment grounded in repository evidence.

### Modernization Planner

Creates a target-state modernization plan.

### Code Change Agent

Generates intentionally bounded code changes.

### Reviewer Agent

Independently reviews proposed modifications.

### Test Runner

Runs baseline and post-patch validation, including nested Maven/Gradle projects.

### Human Approval Gate

Blocks mutation until review and baseline validation succeed.

### Patch Service

Applies approved and validated changes.

### Git Publish Service

Creates local Git branches and commits for validated modifications.

### GitHub Publish Service

Creates or reuses branches, publishes validated files, supports writable forks, retries publishing after permission correction, and creates pull requests.

### Analysis Store

Persists workflow state to PostgreSQL.

---

## Human-in-the-Loop Safety

```text
Repository Evidence
        |
        v
AI Analysis
        |
        v
Bounded Proposal
        |
        v
Independent Review
        |
        v
Baseline Validation
        |
        v
Human Approval
        |
        v
Patch Application
        |
        v
Post-Patch Validation
        |
        v
Git Commit / Pull Request
```

Controls include:

- no mutation during initial analysis
- evidence-based proposals
- bounded modifications
- independent proposal review
- baseline validation before approval
- explicit human approval
- post-patch validation
- safe no-op completion
- controlled Git and GitHub publishing
- selected-repository token access
- secrets stored outside the Docker image
- restricted network access between AWS tiers

---

## Docker Deployment

Backend base image:

```dockerfile
FROM python:3.12-slim-bookworm
```

The image includes:

- Python 3.12
- uv
- Git
- curl
- OpenJDK 17
- Maven
- Semgrep

Production flow:

```text
backend source
      |
      v
docker build
      |
      v
local validation
      |
      v
docker tag
      |
      v
Amazon ECR
      |
      v
ECS task-definition revision
      |
      v
ECS service deployment
      |
      v
AWS Fargate
      |
      v
ALB health check
```

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
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── uv.lock
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.tsx
│   │   └── App.css
│   ├── index.html
│   └── package.json
│
├── docker-compose.yml
└── README.md
```

---

## Running Locally

### Requirements

- Python 3.12+
- uv
- Node.js and npm
- Git
- Docker Desktop, if using containers
- Java and Maven for local Java validation
- Semgrep

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app
```

Backend:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://localhost:5173
```

The frontend uses `VITE_API_BASE` to select the backend API.

### Environment Variables

```env
OPENAI_API_KEY=...
GITHUB_TOKEN=...
DATABASE_URL=...
SQS_QUEUE_URL=...
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

Do not commit credentials or `.env` files.

### GitHub Token Setup

Recommended fine-grained token configuration:

```text
Repository access:
Only select repositories

Repository permissions:
Contents       Read and write
Pull requests  Read and write
Metadata       Read-only
```

If CodeShift needs to publish into a new repository, add that repository to the token's selected repository list.

### Docker Compose

```bash
docker compose up --build
```

---

## Production Deployment

### Frontend

A push to `main` triggers AWS Amplify deployment.

Production:

```text
https://codeshiftai.dev
```

The custom domain is managed through Route 53 with an Amplify-managed TLS certificate.

### Backend

Deployment flow:

1. Build the Docker image.
2. Validate the image locally.
3. Authenticate Docker to ECR.
4. Tag and push the image.
5. Register a new ECS task-definition revision.
6. Update the ECS service.
7. Wait for service stability.
8. Verify the public health endpoint.

Backend routing:

```text
CloudFront -> ALB -> ECS/Fargate
```

---

## Example: End-to-End Spring Repository

Writable test fork:

```text
https://github.com/Shourav5000/gs-rest-service
```

The final end-to-end run demonstrated:

- mixed Kotlin and Java source detection
- Java 17
- Spring Boot
- Maven and Gradle
- four independently validated projects
- 59 files analyzed
- 6 Java classes detected
- 72 dependencies resolved
- OSV vulnerability findings
- Semgrep findings
- automated review
- human approval
- validated patch application
- successful post-patch tests
- Git branch creation
- GitHub publishing
- pull-request creation

Pull request:

https://github.com/Shourav5000/gs-rest-service/pull/1

---

## Example: Controlled No-Op

CodeShift was also tested against:

```text
https://github.com/Shourav5000/codeshift-demo
```

The repository is intentionally minimal.

CodeShift correctly completed analysis and validation without inventing unnecessary changes, returning `no_changes_required`.

A safe no-op is an important result for an autonomous engineering system.

---

## Current Status

Implemented, deployed, and exercised capabilities include:

- GitHub repository ingestion
- SQS-backed asynchronous analysis
- automatic retries
- SQS visibility heartbeats
- live progress tracking
- repository inventory
- language detection
- framework detection
- Java version detection
- mixed Java/Kotlin analysis
- nested Maven/Gradle discovery
- code-structure analysis
- dependency analysis
- OSV vulnerability scanning
- Semgrep static analysis
- technical-debt analysis
- architecture assessment
- modernization planning
- bounded code-change proposals
- independent automated review
- multi-project baseline validation
- human approval gating
- patch application
- post-patch testing
- PostgreSQL persistence
- Git branch and commit creation
- GitHub pull-request publishing
- retryable publish workflow
- fork-aware GitHub publishing
- Dockerized backend
- Docker Compose local environment
- Amazon ECR publishing
- ECS/Fargate deployment
- RDS PostgreSQL
- SQS
- ALB
- CloudFront
- Amplify
- Route 53
- managed HTTPS
- Secrets Manager
- CloudWatch
- IAM
- VPC
- Security Groups

---

## Current Limitations

CodeShift AI is an engineering portfolio project rather than a production multi-tenant SaaS platform.

Future production hardening could include:

- user authentication
- API authorization
- rate limiting and quotas
- separate independently scalable worker services
- stronger isolation for untrusted repository build scripts
- disposable per-analysis execution environments
- resource limits for test execution
- richer audit history
- production alerting and observability
- automated workspace cleanup
- organization-level GitHub authorization
- broader dependency-ecosystem support
- stronger cloud cost controls

A major security improvement for a larger production deployment would be executing cloned repository build commands inside disposable sandboxes rather than inside the long-lived application task.

---

## Why I Built CodeShift AI

Software modernization is rarely just a code-generation problem.

Before changing an existing system, an engineer needs to understand the architecture, dependencies, vulnerabilities, build process, tests, deployment constraints, technical debt, and potential impact of each modification.

CodeShift AI brings those activities into one controlled workflow.

Rather than asking an LLM to simply rewrite a repository, CodeShift first gathers evidence. It then reasons about the system, proposes narrowly scoped changes, independently reviews them, validates the repository, requires human authorization, applies the approved patch, validates again, and can publish the result through a GitHub pull request.

The project combines software engineering, AI orchestration, cloud infrastructure, DevOps, security analysis, repository automation, and human-in-the-loop controls into one end-to-end modernization platform.

---

## Author

**Shourav Kumar Mandal**

Software engineer focused on Java, Spring Boot, enterprise modernization, cloud engineering, AI-assisted software development, software architecture, secure automation, and agentic systems.
