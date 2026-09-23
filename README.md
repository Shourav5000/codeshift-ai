# CodeShift AI

**Agentic Software Intelligence & Modernization Platform**

CodeShift AI is an AI-assisted software modernization platform that analyzes GitHub repositories, identifies technical debt and security risk, proposes bounded code changes, independently reviews those changes, runs validation tests, and keeps a human in control before repository mutation.

The guiding principle is simple:

> AI can analyze, recommend, review, and prepare changes, but repository mutation should remain controlled, testable, and explicitly approved.

## Live Demo

**Frontend**

```text
https://main.d1kebvhpd2c1en.amplifyapp.com
```

**Backend health endpoint**

```text
https://d381c47qj4bdxn.cloudfront.net/health
```

> CodeShift AI is a portfolio/development project. Public cloud resources may be scaled down, restricted, or disabled outside demonstration periods.

---

## What It Does

CodeShift AI can:

- analyze a GitHub repository
- inventory repository files and project structure
- detect languages, frameworks, build tools, and Java versions
- inspect project dependencies
- scan dependencies for known vulnerabilities
- run Semgrep static analysis
- identify technical debt and maintainability issues
- generate an architecture assessment
- create a modernization plan
- propose bounded code changes
- independently review proposed changes
- run baseline build and test validation
- require explicit human approval before mutation
- apply approved patches
- rerun tests after patch application
- create Git branches and commits
- publish pull requests through GitHub

The workflow is intentionally staged so that analysis, proposal generation, review, validation, approval, patching, and publishing remain separate steps.

---

## End-to-End Workflow

```text
GitHub Repository
       |
       v
Repository Intelligence
       |
       v
Architecture Analysis
       |
       v
Technical Debt Analysis
       |
       v
Dependency + Vulnerability Scanning
       |
       v
Semgrep Static Analysis
       |
       v
Modernization Planning
       |
       v
Bounded Code Change Proposal
       |
       v
Independent Review
       |
       v
Baseline Build / Tests
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
Git Branch / Commit
       |
       v
GitHub Pull Request
```

---

## AWS Cloud Architecture

The production portfolio deployment runs on AWS.

```text
User Browser
    |
    v
AWS Amplify
React + TypeScript Frontend
    |
    v
Amazon CloudFront
HTTPS Distribution
    |
    v
Application Load Balancer
    |
    v
Amazon ECS on AWS Fargate
Dockerized FastAPI Backend
    |
    +----------------------+
    |                      |
    v                      v
Amazon RDS              External Services
PostgreSQL              GitHub / OpenAI / OSV
    |
    v
Persistent Analysis State
```

### AWS Services Used

- **AWS Amplify** for frontend hosting and deployment
- **Amazon CloudFront** for HTTPS delivery and backend edge distribution
- **Elastic Load Balancing / Application Load Balancer** for routing traffic to the backend
- **Amazon ECS** for container orchestration
- **AWS Fargate** for serverless container execution
- **Amazon ECR** for Docker image storage
- **Amazon RDS for PostgreSQL** for persistent application data
- **AWS Secrets Manager** for runtime secret injection
- **Amazon CloudWatch Logs** for ECS application logging
- **AWS IAM** for task execution permissions and service access
- **Amazon VPC** networking
- **AWS Security Groups** for traffic isolation between ALB, ECS, and RDS
- **AWS CLI** for deployment and infrastructure validation

The ECS task is not directly exposed to the public internet on port 8000. Backend ingress is restricted to the Application Load Balancer security group.

---

## Docker and Containerization

CodeShift AI uses Docker for repeatable local and cloud execution.

### Local Container Stack

Docker Compose can run:

- PostgreSQL
- the FastAPI backend
- the React frontend

### AWS Container Deployment

```text
Backend Source
    |
    v
Docker Image
    |
    v
Amazon ECR
    |
    v
Amazon ECS
    |
    v
AWS Fargate
```

This allows the backend to run from a reproducible container image locally and in AWS.

---

## Technology Stack

### Backend

- **Python 3.12**
- **FastAPI**
- **LangGraph**
- **LangChain**
- **OpenAI API**
- **Pydantic**
- **SQLAlchemy**
- **psycopg**
- **PostgreSQL**
- **Git CLI**
- Maven integration

### Frontend

- **React**
- **TypeScript**
- **Vite**
- **CSS**
- responsive dashboard UI

### AI / Agentic Workflow

- repository intelligence
- architecture analysis agent
- technical debt agent
- modernization planning agent
- code proposal agent
- independent reviewer agent
- human approval gate
- controlled patch execution

### Security and Static Analysis

- **Semgrep**
- **OSV vulnerability database**
- Maven dependency resolution
- deterministic safety checks
- reviewer approval checks
- pre-patch and post-patch test validation

### DevOps / Cloud

- **Docker**
- **Docker Compose**
- **Amazon ECR**
- **Amazon ECS**
- **AWS Fargate**
- **AWS Amplify**
- **Amazon CloudFront**
- **Application Load Balancer**
- **Amazon RDS for PostgreSQL**
- **AWS Secrets Manager**
- **Amazon CloudWatch**
- **AWS IAM**
- **Amazon VPC**
- **AWS Security Groups**
- **AWS CLI**

### GitHub Integration

- GitHub REST API
- repository cloning
- branch creation
- file updates
- commits
- pull request creation

---

## Main Components

### Repository Scanner

Collects repository evidence including file inventory, programming language signals, build tools, framework signals, Java version, source structure, and test structure.

### Architecture Agent

Produces an architecture assessment grounded in repository files that were actually discovered.

### Technical Debt Agent

Identifies maintainability issues, testing gaps, outdated patterns, and modernization opportunities.

### Dependency Scanner

Inspects dependency metadata and resolves Maven dependency information.

### Vulnerability Scanner

Checks dependency versions against OSV vulnerability data.

### Semgrep Scanner

Runs static analysis rules against the repository and returns security and code-quality findings.

### Modernization Planner

Produces a target-state recommendation and modernization plan based on repository evidence.

### Code Change Agent

Generates bounded code-change proposals instead of unrestricted repository rewrites.

### Reviewer Agent

Independently reviews proposed changes before they are allowed to proceed.

### Test Runner

Runs project validation before mutation and again after patch application.

### Human Approval Gate

Requires an explicit human decision before repository mutation when executable changes are proposed.

### Patch Service

Applies only approved and validated changes.

### GitHub Publish Service

Creates a branch, commits changes, and can publish a pull request.

### Persistence Layer

Analysis state is stored in PostgreSQL when a database connection is configured.

Local development also supports workspace persistence under:

```text
backend/.codeshift/
```

Repository clones are stored in durable analysis workspaces so later approval and patch steps can continue from the same repository state.

---

## Safety Design

CodeShift AI intentionally separates reasoning and execution.

```text
Repository Evidence
        |
        v
AI Proposal
        |
        v
Deterministic Safety Checks
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
Patch
        |
        v
Post-Patch Validation
        |
        v
Pull Request
```

Safety controls include:

- no repository mutation during initial analysis
- bounded code-change proposals
- independent review before patching
- baseline tests before mutation
- explicit human approval
- post-patch test validation
- blocking unsupported dependency versions
- protection against invented GitHub Action SHAs
- restrictions on unsupported Kubernetes security edits
- checks around credential-related changes
- applying only reviewer-approved changes
- pull-request publishing only after validation gates succeed

The cloud deployment also uses:

- AWS Secrets Manager instead of embedding production secrets in container images
- restricted ECS ingress from the ALB security group
- private RDS access from the application tier
- IAM-based service permissions
- CloudWatch logging

---

## Example Validation: Spring PetClinic

CodeShift AI was tested against the Spring PetClinic repository.

The analysis detected:

- **132 files**
- **45 Java classes**
- **173 dependencies**
- **6 known vulnerability findings**
- **16 Semgrep findings**

CodeShift then proposed four bounded changes, including:

- a PostgreSQL JDBC dependency update
- Kubernetes `allowPrivilegeEscalation: false` hardening

The proposed changes passed independent review and baseline testing.

After explicit human approval, CodeShift applied the patch and the post-patch validation passed.

This demonstrated the complete workflow from repository ingestion through safe patch validation.

---

## Production Smoke Test

The deployed AWS environment was also tested with:

```text
https://github.com/Shourav5000/codeshift-demo
```

The production pipeline successfully:

- cloned and analyzed the repository
- detected Maven
- detected Java 17
- generated technical-debt findings
- produced an architecture assessment
- ran `mvn test`
- passed baseline validation
- returned a controlled `no_changes_required` result when no executable patch was justified

This validated the deployed path across the frontend, CDN, load balancer, ECS backend, AI workflow, persistence layer, and external integrations.

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
│   ├── .codeshift/
│   ├── pyproject.toml
│   └── uv.lock
│
├── frontend/
│   ├── src/
│   ├── public/
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
- Node.js / npm
- Git
- Java
- Maven or Maven Wrapper
- Semgrep
- Docker Desktop, if using the containerized stack

### Backend

```bash
cd backend
uv sync
```

Create:

```text
backend/.env
```

Example:

```env
OPENAI_API_KEY=your_openai_api_key
GITHUB_TOKEN=your_github_token
DATABASE_URL=your_postgresql_connection_string
CORS_ORIGINS=http://localhost:5173,http://localhost:8080
```

Do not commit `.env`.

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

For production builds, the frontend reads:

```text
VITE_API_BASE
```

to determine the backend base URL.

### Docker Compose

From the repository root:

```bash
docker compose up --build
```

The local stack includes PostgreSQL, the backend, and the frontend.

---

## AWS Deployment Overview

### Backend

1. Build the backend Docker image.
2. Push the image to Amazon ECR.
3. Deploy the image through Amazon ECS on AWS Fargate.
4. Inject secrets through AWS Secrets Manager.
5. Connect the ECS service to Amazon RDS PostgreSQL.
6. Route traffic through an Application Load Balancer.
7. Place Amazon CloudFront in front of the backend for HTTPS delivery.
8. Send application logs to Amazon CloudWatch.

### Frontend

1. Connect the GitHub repository to AWS Amplify.
2. Build the Vite frontend from the `frontend` directory.
3. Set the production `VITE_API_BASE` environment variable.
4. Deploy the `main` branch through Amplify.

---

## Current Status

The main CodeShift AI workflow is implemented and deployed.

Completed capabilities include:

- repository analysis
- architecture assessment
- technical-debt analysis
- dependency scanning
- vulnerability scanning
- Semgrep analysis
- modernization planning
- bounded code-change generation
- independent automated review
- baseline testing
- human approval
- patch application
- post-patch validation
- PostgreSQL persistence
- durable repository workspaces
- GitHub branch creation
- pull-request publishing
- responsive React frontend
- Dockerized backend
- local Docker Compose stack
- Amazon ECR image publishing
- Amazon ECS / AWS Fargate backend deployment
- Amazon RDS PostgreSQL deployment
- Application Load Balancer routing
- Amazon CloudFront HTTPS distribution
- AWS Amplify frontend deployment
- AWS Secrets Manager integration
- CloudWatch logging
- AWS security-group isolation

---

## Current Limitations

CodeShift AI is a portfolio and engineering demonstration project, not a production multi-tenant SaaS platform.

Important future improvements include:

- authentication and user accounts
- API authorization
- rate limiting and quotas
- background job processing for long-running analyses
- stronger isolation for untrusted repository build scripts
- per-analysis execution sandboxes
- improved GitHub retry and conflict handling
- richer audit history
- production monitoring and alerting
- automatic workspace cleanup
- organization-level access controls
- stronger cost controls for public deployments

One of the most important production hardening steps would be running cloned repository build/test commands inside isolated disposable sandboxes rather than directly inside the long-lived application environment.

---

## Future Ideas

Potential extensions include:

- isolated ephemeral execution environments
- asynchronous job queues
- richer action and evidence tracing
- repository history analysis
- multi-repository analysis
- organization dashboards
- CI/CD integrations
- policy-as-code controls
- cost and risk scoring
- additional language ecosystems
- automated migration playbooks

---

## Why I Built It

Modernizing an existing application is usually more difficult than building a new one.

Before changing a codebase, an engineer needs to understand:

- architecture
- dependencies
- vulnerabilities
- technical debt
- build configuration
- test behavior
- modernization constraints
- the risk of each proposed change

CodeShift AI brings those steps into one controlled workflow.

Instead of asking an LLM to simply "rewrite this repository," CodeShift gathers evidence first, proposes bounded changes, reviews them independently, validates the project, and keeps the final mutation decision under human control.

---

## Author

**Shourav Kumar Mandal**

Software engineer focused on Java, Spring Boot, cloud modernization, AI-assisted software engineering, software architecture, and enterprise application development.
