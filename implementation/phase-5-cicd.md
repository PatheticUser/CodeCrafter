# Phase 5 — CI/CD Pipeline

> **Effort:** ~2 days · **Dependencies:** Phase 4  
> **Goal:** Automated testing, linting, image building, and deployment via GitHub Actions. Every push is validated. Every merge to main deploys automatically.

---

## 5.1 Pipeline Design

### What You're Building

A three-stage pipeline triggered on every push and pull request:

**Stage 1: Validate** — runs in parallel:
- Ruff lint + format check (fast, catches style issues)
- Backend pytest with coverage (medium, catches logic bugs)
- Frontend lint + build (medium, catches UI issues)

**Stage 2: Build** — runs only on main branch, after all validation passes:
- Build multi-arch Docker images for API and frontend
- Push to GitHub Container Registry (GHCR)
- Tag with both `latest` and the commit SHA

**Stage 3: Deploy** — runs after successful build:
- SSH into production server
- Pull latest images
- Run database migrations
- Rolling restart of containers
- Verify health check

### Principles

- **Fail fast** — lint runs first because it's fastest (2-3 seconds). No point running 5-minute test suites if code style is broken.
- **Parallel where possible** — backend tests and frontend tests are independent, run simultaneously.
- **Gate on main** — builds and deploys only happen on main branch merges. Feature branches get validation only.
- **Reproducible** — use locked dependency files (`uv.lock`, `package-lock.json`) and pinned action versions.

---

## 5.2 Main CI Workflow

### What To Configure

Create `.github/workflows/ci.yml` with these jobs:

**Lint Job:**
1. Check out code
2. Install uv using the official `astral-sh/setup-uv` action
3. Install dependencies with `uv sync --frozen`
4. Run `ruff check src/ tests/` — lint errors fail the job
5. Run `ruff format --check src/ tests/` — formatting violations fail the job

**Backend Test Job:**
1. Depends on lint passing
2. Start PostgreSQL and Redis as service containers (GitHub Actions supports this natively)
3. Install uv and dependencies
4. Run pytest with coverage:
   - `--cov=src` for coverage tracking
   - `--cov-report=xml` for Codecov upload
   - `--junitxml=test-results.xml` for test result reporting
5. Set environment variables pointing to the service containers (database URL, Redis URL, test JWT secret)
6. Upload coverage report to Codecov
7. Fail if coverage drops below 70%

**Frontend Test Job:**
1. Depends on lint passing (runs in parallel with backend tests)
2. Set up Node.js with npm cache
3. Run `npm ci` in the frontend directory
4. Run linting (`npm run lint`)
5. Run build (`npm run build`) — build failures catch import errors and type issues
6. Optionally run frontend unit tests if they exist

**Build Job:**
1. Depends on BOTH test jobs passing
2. Only runs on main branch (`if: github.ref == 'refs/heads/main'`)
3. Set up Docker Buildx for multi-platform builds
4. Authenticate to GHCR using `GITHUB_TOKEN` (automatically available)
5. Build and push API image with two tags: `latest` and commit SHA
6. Build and push frontend image with same tagging strategy
7. Use GitHub Actions cache (`type=gha`) for Docker layer caching — dramatically speeds up rebuilds

### Best Practices

- **Pin action versions to SHA** — use `actions/checkout@v4` at minimum, ideally pin to commit SHA. Prevents supply chain attacks via compromised actions.

- **Use uv's official action** — `astral-sh/setup-uv@v4` handles installation, caching, and PATH setup correctly.

- **Service container health checks** — configure postgres and redis services with health check commands and retries. The job waits until services are healthy before running tests.

- **Secrets management** — never hardcode secrets in workflow files. Use GitHub repository secrets for deploy SSH keys, server addresses, and production passwords.

- **Cache aggressively** — cache uv dependencies, npm dependencies, and Docker layers. First run may take 5 minutes; cached runs should complete in under 2 minutes.

- **Fail fast on the first error** — use `pytest -x` in CI to stop on first failure. Faster feedback.

---

## 5.3 Deploy Workflow

### What To Configure

Create `.github/workflows/deploy.yml` triggered by successful CI runs on main:

1. **Trigger** — use `workflow_run` trigger, watching the CI workflow on main branch. Only deploy if CI concluded successfully.

2. **SSH deployment**:
   - Use `appleboy/ssh-action` to SSH into the production server
   - Commands to run on server:
     - `cd /opt/codecrafter`
     - `git pull origin main` (get latest compose files and configs)
     - `docker compose pull` (pull new images from GHCR)
     - `docker compose up -d --remove-orphans` (restart with new images)
     - `docker image prune -f` (clean up old images)

3. **Post-deploy verification**:
   - Wait 15 seconds for containers to start
   - Hit the health endpoint from the GitHub Actions runner
   - If health check fails, the deploy job fails and alerts are sent

4. **Rollback plan** — if deploy fails, the previous images are still available in GHCR. Manual rollback: `docker compose pull specific-sha-tag && docker compose up -d`.

### Best Practices

- **Zero-downtime deploys** — if running multiple API replicas, restart one at a time (rolling update). Single-replica setups will have a brief (~5 second) downtime during restart.

- **Run migrations before deploying new code** — database schema changes must be backward-compatible. The old code should work with the new schema during the rolling restart window.

- **Separate deploy credentials** — the deploy SSH key should be a dedicated key with limited permissions, not your personal key.

- **Deployment notifications** — add a step to send a message to Slack/Discord on successful deploy and on failure. Include the commit message and author.

---

## 5.4 Dependency Management

### What To Configure

Create `.github/dependabot.yml` to automatically create PRs for dependency updates:

- **Python dependencies** — weekly scan of `pyproject.toml`
- **npm dependencies** — weekly scan of `frontend/package.json`
- **Docker base images** — weekly scan of Dockerfiles
- **GitHub Actions** — weekly scan of workflow files

Group related updates into single PRs to reduce noise (e.g., all Python deps in one PR).

### Best Practices

- **Review Dependabot PRs carefully** — automated updates can introduce breaking changes. The CI pipeline should catch most issues, but manual review of changelogs is important for major version bumps.

- **Use Renovate instead of Dependabot if you prefer** — Renovate has more configuration options, better grouping, and supports more ecosystems.

- **Pin to minor versions in pyproject.toml** — `"fastapi>=0.110,<0.112"` instead of `"fastapi>=0.110"`. This allows patch updates while preventing unexpected major changes.

---

## 5.5 Branch Protection

### What To Configure in GitHub Settings

Go to Settings → Branches → Add rule for `main`:

1. **Require pull request** — no direct pushes to main. All changes go through PRs.
2. **Require status checks** — all three CI jobs (lint, test-backend, test-frontend) must pass before merging.
3. **Require branches to be up to date** — PRs must be rebased on latest main before merging. Prevents merge-and-break scenarios.
4. **No force pushes** — protect commit history.
5. **No branch deletion** — prevent accidental deletion of main.

### Best Practices

- **Squash merge PRs** — keeps main history clean. One commit per feature/fix.
- **Delete branches after merge** — enable auto-delete in repository settings. Prevents branch proliferation.
- **Require at least 1 review** — if working with a team. Skip for solo projects.

---

## 5.6 Local Pre-commit Hooks

### What To Configure

Create `.pre-commit-config.yaml` with hooks that run before every commit:

1. **Ruff lint with auto-fix** — catches and fixes style issues before they reach CI
2. **Ruff format** — applies formatting on changed files
3. **Quick pytest run** — `pytest -x -q --no-header` runs fast subset of tests

### How To Set Up

Install the pre-commit framework and install hooks:
- `uv add --dev pre-commit`
- `uv run pre-commit install`

Now every `git commit` automatically runs lint + format + quick tests. Failures prevent the commit.

### Best Practices

- **Keep hooks fast** — pre-commit should take < 10 seconds. Run full test suite in CI, not locally.
- **Don't skip hooks** — `git commit --no-verify` should be rare and deliberate.
- **Commit the config file** — `.pre-commit-config.yaml` is part of the project. New contributors get hooks automatically after `pre-commit install`.

---

## Phase 5 Final Checklist

- [ ] Push to any branch triggers lint + tests
- [ ] PR to `main` shows required status checks
- [ ] Cannot merge PR with failing checks
- [ ] Merge to `main` triggers image build + push to GHCR
- [ ] Successful build triggers deployment to production server
- [ ] Deploy job verifies health check after restart
- [ ] Failed deploy sends alert notification
- [ ] Dependabot creates weekly dependency update PRs
- [ ] Pre-commit hooks run lint + format + quick tests locally
- [ ] Docker images tagged with both `latest` and commit SHA
- [ ] Coverage reports uploaded and visible in PR comments
- [ ] Full CI pipeline completes in under 5 minutes (cached)
