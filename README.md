# CodeShift AI

**Agentic Software Intelligence & Modernization Platform**

CodeShift AI is a full-stack AI-assisted software modernization platform that analyzes GitHub repositories, builds evidence about the codebase, identifies technical debt and security risk, proposes bounded changes, independently reviews those changes, validates the repository, and keeps a human in control before any repository mutation occurs.

The project was built around a simple engineering principle:

> AI should help engineers understand and modernize software, but code changes should remain evidence-grounded, reviewable, testable, and explicitly controlled.

## Live Application

**CodeShift AI**

https://codeshiftai.dev

**Backend health endpoint**

https://d381c47qj4bdxn.cloudfront.net/health

The production frontend is hosted on AWS Amplify behind the custom `codeshiftai.dev` domain. The backend runs as a Dockerized FastAPI service on Amazon ECS with AWS Fargate.

> CodeShift AI is a portfolio and engineering demonstration project. Cloud resources may be restricted, scaled down, or changed outside demonstration periods.

---

## What CodeShift AI Does

CodeShift accepts a public GitHub repository URL and runs a staged modernization workflow that can:

- validate and clone a GitHub repository
- inventory repository files and source structure
- detect programming languages
- detect frameworks and build systems
- identify Java versions
- discover nested Maven and Gradle projects
- analyze multi-project repositories
- inspect and resolve dependencies
- check dependencies against the OSV vulnerability database
- run Semgrep static analysis
- identify technical debt and maintainability concerns
- generate an evidence-grounded architecture assessment
- create a modernization plan
- propose bounded code changes
- independently review proposed changes
- run baseline validation before mutation
- display validation results for each discovered build project
- require explicit human approval when executable changes are proposed
- apply approved patches
- rerun validation after patch application
- create Git branches and commits
- publish changes through GitHub pull requests

The application intentionally separates repository understanding, AI reasoning, validation, human approval, and mutation into distinct stages.

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
GitHub Pull Request
```

If CodeShift determines that the evidence does not justify a repository change, the workflow can safely finish with `no_changes_required` instead of manufacturing a patch.

---

## Production AWS Architecture

The production portfolio deployment uses a multi-service AWS architecture.

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
               |                                |
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
- Amazon ECR for Docker images
- AWS Secrets Manager for application secrets
- Amazon CloudWatch for logs
- AWS IAM for task and service permissions
- Amazon VPC and Security Groups for network isolation
```

### AWS Services Used

- **Amazon Route 53** for the `codeshiftai.dev` domain and DNS
- **AWS Amplify Hosting** for the React frontend and continuous deployment from `main`
- **AWS Amplify managed SSL** for HTTPS on the custom domain
- **Amazon CloudFront** for the public backend HTTPS endpoint
- **Elastic Load Balancing / Application Load Balancer** for backend traffic routing
- **Amazon ECS** for container orchestration
- **AWS Fargate** for serverless container execution
- **Amazon ECR** for versioned Docker image storage
- **Amazon RDS for PostgreSQL** for persistent analysis state
- **Amazon SQS** for durable asynchronous repository-analysis jobs
- **AWS Secrets Manager** for runtime secret injection
- **Amazon CloudWatch Logs** for application and worker logging
- **AWS IAM** for ECS task permissions and SQS access
- **Amazon VPC** for application networking
- **AWS Security Groups** for ALB, ECS, and RDS traffic isolation
- **AWS CLI** for deployment, task-definition management, and operational validation

The ECS task is not directly exposed to public traffic on port `8000`. Backend ingress is routed through the Application Load Balancer.

---

## Asynchronous Processing and Reliability

Repository analysis can take longer than a normal HTTP request, especially for larger Java projects. CodeShift therefore uses an asynchronous job architecture instead of keeping the original request open.

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
   +--> Semgrep
   +--> dependency resolution
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
- automatic retry handling for transient analysis failures
- SQS visibility-timeout extension for long-running jobs
- per-stage progress persistence
- frontend polling for live status updates
- elapsed-time display
- retry-state messaging
- analysis timeout protection
- OpenAI request timeouts and bounded retries
- CloudWatch stage and worker logs

The current portfolio deployment runs the SQS consumer alongside the FastAPI application inside the ECS task. A larger production deployment would normally separate the API and worker into independently scalable ECS services.

---

## Live Analysis Experience

The frontend displays the active analysis pipeline in real time rather than showing a generic loading spinner.

Stages include:

1. Validate repository
2. Clone repository
3. Scan repository
4. Collect repository evidence
5. Analyze code structure
6. Analyze dependencies
7. Check vulnerabilities
8. Run Semgrep
9. Analyze technical debt
10. Assess architecture
11. Plan modernization
12. Prepare code proposal
13. Run independent review
14. Run baseline tests
15. Evaluate the human safety gate

Completed stages, the currently active stage, pending stages, automatic retries, and elapsed time are surfaced directly in the UI.

---

## Multi-Project Repository Support

CodeShift supports repositories where the build files are not located at the repository root.

The repository scanner recursively discovers:

- `pom.xml`
- `build.gradle`
- `build.gradle.kts`
- Maven Wrapper files
- Gradle Wrapper files
- Java toolchain configuration
- Spring Boot build signals
- nested source and test directories

This allows CodeShift to analyze repositories containing multiple independently buildable projects, examples, or application variants.

For baseline validation, CodeShift can run tests from discovered nested project roots and report each project separately with:

- project path
- build tool
- command
- status
- exit code
- validation error output when applicable

This prevents a successful test in one module from hiding a failure in another module.

---

## Technology Stack

### Backend

- **Python 3.12**
- **FastAPI**
- **Uvicorn**
- **Pydantic**
- **Pydantic Settings**
- **SQLAlchemy**
- **psycopg**
- **PostgreSQL**
- **boto3**
- **Git CLI**
- **uv** for Python dependency and environment management

### AI and Agentic Orchestration

- **LangGraph**
- **LangChain**
- **LangChain OpenAI integration**
- **OpenAI API**
- stateful multi-stage agent workflow
- independent proposal review
- evidence-grounded architecture analysis
- technical-debt analysis
- modernization planning
- bounded code-change generation
- human-in-the-loop approval

### Frontend

- **React 19**
- **React DOM 19**
- **TypeScript 6**
- **Vite 8**
- **HTML5**
- **CSS3**
- Fetch API
- responsive dashboard UI
- live asynchronous analysis polling

### Repository and Build Analysis

- **Git**
- **Maven**
- **Maven Wrapper**
- **Gradle**
- **Gradle Wrapper**
- **Java / OpenJDK 17**
- recursive build-project discovery
- Java version detection
- Spring Boot detection
- source and test structure analysis
- multi-project baseline validation

### Security and Code Analysis

- **Semgrep**
- **OSV vulnerability database / API**
- dependency vulnerability analysis
- static analysis
- deterministic safety checks
- pre-patch validation
- post-patch validation
- independent proposal review
- CORS allow-listing

### Docker and Containerization

- **Docker**
- **Docker Desktop**
- **Docker Compose**
- **Debian Bookworm-based Python container**
- **OpenJDK 17 inside the backend image**
- **Maven inside the backend image**
- **Semgrep inside the backend image**
- **Amazon ECR**
- **Amazon ECS**
- **AWS Fargate**

The production backend is packaged as a reproducible Docker image and promoted through ECR into ECS task-definition revisions.

### AWS / Cloud

- **Amazon Route 53**
- **AWS Amplify**
- **Amazon CloudFront**
- **Application Load Balancer**
- **Amazon ECS**
- **AWS Fargate**
- **Amazon ECR**
- **Amazon RDS for PostgreSQL**
- **Amazon SQS**
- **AWS Secrets Manager**
- **Amazon CloudWatch**
- **AWS IAM**
- **Amazon VPC**
- **AWS Security Groups**
- **AWS CLI**

### GitHub Integration

- **GitHub REST API**
- repository cloning
- branch creation
- repository file updates
- commit creation
- pull request creation
- Git-based local patch workflow

### Development and Quality Tooling

- **PowerShell**
- **Postman**
- **Swagger / OpenAPI**
- **GitHub**
- **Git**
- **npm**
- **Vite production builds**
- **TypeScript compiler**
- backend import validation
- Docker image validation
- health-check validation

---

## Core Application Components

### Repository Scanner

Builds the initial technology profile by detecting:

- languages
- frameworks
- build systems
- Java versions
- tests
- nested project roots
- source structure

### Repository Content Collector

Collects repository evidence used by the AI agents so recommendations remain grounded in files that were actually discovered.

### Code Structure Scanner

Analyzes source organization, Java classes, package structure, and application structure.

### Dependency Scanner

Discovers dependency manifests and resolves dependency information across supported nested projects.

### Vulnerability Scanner

Queries the OSV vulnerability database using resolved dependency versions and returns known vulnerability findings.

### Semgrep Scanner

Runs static analysis over the cloned repository and captures security and code-quality findings.

### Technical Debt Agent

Evaluates maintainability, testing gaps, security findings, legacy patterns, and modernization opportunities.

### Architecture Agent

Produces a technical architecture assessment using repository evidence rather than assumptions about the codebase.

### Modernization Planner

Creates a target-state modernization plan based on the repository profile, architecture, vulnerabilities, and technical debt.

### Code Change Agent

Generates intentionally bounded code changes instead of unrestricted repository rewrites.

### Reviewer Agent

Independently reviews proposed modifications and determines whether they are supported by the available evidence and safe enough to continue.

### Test Runner

Runs baseline validation before mutation and reruns validation after an approved patch.

It supports nested Maven and Gradle projects and surfaces results per project.

### Human Approval Gate

Prevents repository mutation unless the automated review and baseline validation requirements are satisfied.

If validation is blocked, the frontend does not present an approval action.

### Patch Service

Applies only approved and validated change plans.

### Git Publish Service

Creates local Git branches and commits for validated modifications.

### GitHub Publish Service

Uses the GitHub API to publish repository changes and create pull requests.

### Analysis Store

Persists workflow state to PostgreSQL so the API, SQS worker, and frontend polling flow can share analysis progress.

---

## Human-in-the-Loop Safety Design

CodeShift separates reasoning from execution.

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
Deterministic Baseline Validation
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

- no repository mutation during initial analysis
- evidence-based code proposals
- bounded modifications
- independent proposal review
- validation before approval
- explicit human approval
- validation after patch application
- no-op completion when no safe change is justified
- protection against unsupported dependency modifications
- protection against invented GitHub Action commit SHAs
- controlled Git and GitHub publishing
- secrets stored outside the Docker image
- restricted network access between AWS tiers

The approval UI is state-aware. A repository with failed or unavailable baseline validation is shown as **blocked**, and approval controls are not offered until the required safety gates succeed.

---

## Docker Deployment

### Backend Image

The backend image is based on:

```dockerfile
FROM python:3.12-slim-bookworm
```

The image includes:

- Python 3.12
- `uv`
- FastAPI dependencies
- Git
- curl
- OpenJDK 17
- Maven
- Semgrep

This lets the ECS worker clone repositories, perform static analysis, resolve Maven dependencies, and execute Java baseline tests inside the container.

### Production Container Flow

```text
backend source
      |
      v
docker build
      |
      v
local image validation
      |
      v
docker tag
      |
      v
Amazon ECR
      |
      v
new ECS task-definition revision
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
- `uv`
- Node.js and npm
- Git
- Docker Desktop, if using containers
- Java and Maven for local Java-repository validation
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

Swagger UI:

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

The frontend uses:

```text
VITE_API_BASE
```

to select the backend API endpoint.

### Local Environment Variables

Typical backend configuration includes:

```env
OPENAI_API_KEY=...
GITHUB_TOKEN=...
DATABASE_URL=...
SQS_QUEUE_URL=...
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

Do not commit real credentials or `.env` files.

### Docker Compose

From the repository root:

```bash
docker compose up --build
```

---

## Production Deployment

### Frontend

The frontend is connected to GitHub through AWS Amplify.

A push to `main` triggers the Amplify production build and deployment.

Production domain:

```text
https://codeshiftai.dev
```

The custom domain is managed through Route 53 and uses an Amplify-managed TLS certificate.

### Backend

The backend deployment flow is:

1. Build the Docker image.
2. Validate the image locally.
3. Authenticate Docker to Amazon ECR.
4. Tag the image with the ECR repository URI.
5. Push the image to ECR.
6. Create a new ECS task-definition revision.
7. Update the ECS service.
8. Wait for the service to become stable.
9. Verify the public health endpoint.

The backend is currently served through:

```text
CloudFront -> ALB -> ECS/Fargate
```

---

## Example: Multi-Project Spring Repository

CodeShift was tested against:

```text
https://github.com/spring-guides/gs-rest-service
```

The analysis demonstrated nested-project support by detecting:

- Java as the primary language
- Java 17
- Spring Boot
- Maven and Gradle
- multiple nested Java and Kotlin project variants
- resolved Maven dependencies
- OSV vulnerability findings
- Semgrep findings
- project-specific baseline validation

This test also helped drive improvements to:

- recursive build discovery
- nested dependency scanning
- multi-project validation
- Java runtime compatibility
- blocked-approval UI behavior
- per-project test result visibility

---

## Example: Controlled No-Op

CodeShift was also tested against:

```text
https://github.com/Shourav5000/codeshift-demo
```

The repository is intentionally minimal.

CodeShift correctly:

- identified the repository structure
- detected Maven and Java configuration
- ran baseline validation
- completed its architecture and modernization analysis
- avoided inventing source code or dependencies
- returned `no_changes_required`

A safe no-op is an important outcome for an autonomous engineering system. The platform should not manufacture changes simply because it was asked to analyze a repository.

---

## Current Status

Implemented and deployed capabilities include:

- GitHub repository ingestion
- asynchronous SQS-backed analysis
- automatic worker retry handling
- live stage-by-stage frontend progress
- repository inventory
- language detection
- framework detection
- Java version detection
- nested Maven/Gradle project discovery
- code-structure analysis
- dependency analysis
- vulnerability scanning with OSV
- static analysis with Semgrep
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
- Dockerized backend
- Docker Compose local environment
- Amazon ECR image publishing
- ECS/Fargate backend deployment
- RDS PostgreSQL persistence
- SQS job processing
- ALB routing
- CloudFront backend distribution
- Amplify frontend hosting
- Route 53 custom domain
- managed HTTPS
- Secrets Manager integration
- CloudWatch logging
- IAM task permissions
- VPC and Security Group isolation

---

## Current Limitations

CodeShift AI is an engineering portfolio project, not a production multi-tenant SaaS platform.

Important production-hardening work would include:

- user authentication
- API authorization
- rate limiting and usage quotas
- dedicated independently scalable ECS worker services
- stronger isolation for untrusted repository build scripts
- disposable per-analysis execution environments
- resource limits for repository test execution
- richer audit history
- production alerting and observability
- automated workspace cleanup
- organization-level GitHub authorization
- stronger public-cloud cost controls
- broader support for additional dependency ecosystems

The most important security improvement would be executing cloned repository build commands inside disposable sandboxes rather than inside the long-lived application task.

---

## Why I Built CodeShift AI

Software modernization is rarely just a code-generation problem.

Before changing an existing system, an engineer needs to understand the architecture, dependencies, vulnerabilities, build process, tests, deployment constraints, technical debt, and the potential impact of each modification.

CodeShift AI brings those activities into one controlled workflow.

Rather than asking an LLM to simply rewrite a repository, CodeShift first gathers evidence. It then reasons about the system, proposes narrowly scoped changes, independently reviews those changes, validates the repository, and requires human authorization before mutation.

The project combines software engineering, AI orchestration, cloud infrastructure, DevOps, security analysis, and human-in-the-loop controls into a single end-to-end modernization platform.

---

## Author

**Shourav Kumar Mandal**

Software engineer focused on Java, Spring Boot, enterprise modernization, cloud engineering, AI-assisted software development, software architecture, and secure automation.
