# Phase 7 — Observability & Production Hardening

> **Effort:** ~2 days · **Dependencies:** Phase 6  
> **Goal:** Make production debuggable, measurable, and alertable. When something breaks at 3 AM, you should be able to diagnose it from logs and metrics without SSHing into the server.

---

## 7.1 Structured Logging

### Why This Matters

The current codebase has zero logging. When something fails in production, you have no visibility. Print statements don't cut it — they're unstructured, unsearchable, and mixed with stdout noise.

### What To Do

1. **Install `structlog`** — the Python standard for structured logging. Outputs JSON in production (machine-parseable) and colored human-readable text in development (developer-friendly).

2. **Create a logging setup module** — configure structlog once at application startup. All modules then use `structlog.get_logger()` to get a logger instance.

3. **Configure output format by environment**:
   - Development: colored console output with timestamps, log levels, and context fields
   - Production: JSON lines (one JSON object per log entry). This is parseable by log aggregators (Loki, ELK, CloudWatch).

4. **Redirect stdlib logging through structlog** — third-party libraries (FastAPI, SQLAlchemy, uvicorn) use Python's built-in `logging` module. Configure it to flow through structlog for consistent formatting.

5. **Add context to every log entry** — use `structlog.contextvars` to automatically include request_id, user_id, and session_id in every log message within a request lifecycle. Set these in middleware once, and every log entry in that request automatically includes them.

### What To Log

Define a consistent set of log events across the application. Each event should have a descriptive name and relevant fields:

**Request lifecycle:**
- Every HTTP request: method, path, status code, duration in milliseconds
- WebSocket connections: user_id, session_id, connect/disconnect events, connection duration

**Agent operations:**
- Chat requests: user_id, model requested, session_id, message length
- Chat responses: model used, response length, number of tool calls, total latency
- Tool executions: tool name, execution duration, success/failure
- Model fallbacks: which model failed, which model took over, failure reason
- Auto-fix attempts: which error triggered it, attempt number, success/failure

**Authentication:**
- Successful logins: user_id, IP address
- Failed login attempts: email attempted, IP address, failure reason (DO NOT log passwords)
- Token refreshes: user_id
- Rate limit hits: user_id, IP address, endpoint, current limit

**System events:**
- Application startup/shutdown
- Database connection pool status
- Ollama connectivity changes
- Backup completion/failure

### Best Practices

- **Log at the right level**:
  - `DEBUG` — detailed internal state (disabled in production)
  - `INFO` — normal operations (request handled, tool executed, session created)
  - `WARNING` — something unexpected but handled (rate limited, model fallback, corrupt session recovered)
  - `ERROR` — something failed and needs attention (tool execution error, database connection failure)
  - `CRITICAL` — system is unusable (all models down, database unreachable)

- **Never log sensitive data** — no passwords, no JWT tokens, no file contents, no user messages (unless you have explicit consent and data handling policies). Log metadata about operations, not the data itself.

- **Include enough context to diagnose** — every error log should answer: what happened, where (which tool/endpoint), for whom (user_id), and what was the input (sanitized).

- **Use consistent field names** — always `user_id` not sometimes `userId` and sometimes `user`. Always `duration_ms` not sometimes `elapsed` and sometimes `time`.

- **Configure log rotation** — Docker containers write logs to `/var/lib/docker/containers/`. Configure the Docker logging driver to limit log file size (e.g., max 50MB, keep 3 files). Without this, logs will fill your disk.

---

## 7.2 Metrics with Prometheus

### Why This Matters

Logs tell you what happened. Metrics tell you how the system is performing over time. "Are we getting slower?" "How many requests per second?" "Which tools are used most?" — these questions need metrics, not grep.

### What To Do

1. **Install Prometheus client libraries** — `prometheus-fastapi-instrumentator` auto-instruments all HTTP endpoints. `prometheus-client` lets you define custom metrics.

2. **Enable auto-instrumentation** — the instrumentator automatically records request count, latency histograms, and response sizes for every endpoint. Attach it to the FastAPI app at startup. Expose metrics at `/metrics` endpoint.

3. **Define custom metrics** for CodeCrafter-specific concerns:

   **Counters (things that go up):**
   - Chat requests by model and status (success/error)
   - Tool executions by tool name and outcome
   - Model fallback events by source and target model
   - Authentication events by type (login/register/refresh/failure)
   - Rate limit rejections

   **Histograms (distribution of values):**
   - Chat request latency by model — use custom buckets tuned for agent response times (0.5s, 1s, 2s, 5s, 10s, 30s, 60s, 120s). Default Prometheus buckets max at 10s which misses slow agent turns.
   - Tool execution latency by tool name
   
   **Gauges (values that go up and down):**
   - Active WebSocket connections
   - Active chat sessions
   - Workspace disk usage per user (optional, can be expensive to compute frequently)

4. **Add Prometheus to Docker Compose** — run a Prometheus container that scrapes the `/metrics` endpoint from the API container every 15 seconds.

5. **Configure Prometheus** — create a `prometheus.yml` config file that defines scrape targets. Include the API service and optionally a node-exporter for host system metrics (CPU, memory, disk).

### Best Practices

- **Exclude health and metrics endpoints from instrumentation** — these are called frequently by monitoring tools and would skew your latency and request count metrics.

- **Use labels judiciously** — labels create separate time series. `model` and `status` are fine. Don't use `user_id` as a label — it creates one time series per user, which doesn't scale and provides minimal value (use logs for per-user debugging).

- **Histogram bucket boundaries matter** — for chat latency, default Prometheus buckets (up to 10s) are too small. Agent turns regularly take 30-60 seconds. Adjust buckets to capture the actual latency distribution.

- **Instrument at the right layer** — record metrics in the API layer (routes/middleware), not in the agent core. The agent should remain transport-agnostic.

---

## 7.3 Dashboards with Grafana

### What To Do

1. **Add Grafana to Docker Compose** — standard Grafana image with a persistent volume for dashboard storage. Expose on port 3000 (internal only, not through nginx — use SSH tunneling or restrict via firewall).

2. **Connect Grafana to Prometheus** — add Prometheus as a data source in Grafana's UI. URL: `http://prometheus:9090` (container-to-container networking).

3. **Build a CodeCrafter dashboard** with these panels:

   **Overview row:**
   - Request rate (requests per minute, last 1 hour)
   - Error rate (percentage of failed requests)
   - P50 / P95 / P99 latency (how slow are we?)
   - Active WebSocket connections

   **Agent row:**
   - Tool usage distribution (bar chart: which tools are used most)
   - Tool latency by name (heatmap or multi-line graph)
   - Model fallback frequency (spike = Ollama issues)
   - Agent steps per turn (histogram: how many tool calls per user message)

   **Infrastructure row:**
   - CPU usage (from node-exporter)
   - Memory usage per container
   - Disk usage
   - Network I/O

   **Auth row:**
   - Login success/failure rate
   - Rate limit rejections
   - Active sessions count

### Best Practices

- **Set appropriate time ranges** — overview panels show last 1 hour, infrastructure shows last 24 hours.
- **Add annotations** — mark deployments on graphs so you can correlate releases with behavior changes.
- **Don't expose Grafana publicly** — access via SSH tunnel (`ssh -L 3000:localhost:3000 deploy@server`) or restrict via nginx with basic auth.
- **Export dashboard JSON** — commit your dashboard configuration to the repo so it's reproducible.

---

## 7.4 Error Tracking with Sentry

### Why Sentry (Not Just Logs)

Logs capture everything. Sentry captures exceptions with full context: stack trace, request data, user info, breadcrumbs (what happened before the error). Sentry also deduplicates, groups, and alerts — turning 1000 identical errors into one issue with a count.

### What To Do

1. **Install `sentry-sdk` with FastAPI integration** — Sentry's SDK auto-captures unhandled exceptions, request context, and SQLAlchemy queries.

2. **Initialize at startup** — configure with:
   - DSN (from Sentry dashboard — add to `.env`)
   - Environment tag (development/staging/production)
   - Release tag (app version)
   - Traces sample rate: 10% in production (full tracing is expensive)
   - Send default PII: **false** (don't send user emails/IPs to Sentry)

3. **Filter sensitive data** — add a `before_send` hook that strips Authorization headers, JWT tokens, and any user content from error reports before they leave your server.

4. **Add breadcrumbs** — manually add breadcrumbs at key points (session loaded, tool started, model selected). When an error occurs, Sentry shows the breadcrumb trail leading up to it.

### Best Practices

- **Don't send user messages to Sentry** — chat content is sensitive. Log enough context to debug (message length, session_id) without the actual content.
- **Set alert rules** — Sentry can alert on new issues, regressions (resolved issues that reappear), and error frequency spikes.
- **Use Sentry's performance monitoring** — it tracks transaction durations and can identify slow endpoints without manual instrumentation.

---

## 7.5 Request Tracing

### What To Do

1. **Generate a unique request ID for every request** — create this in middleware. Check for `X-Request-ID` header first (allows clients to set their own for end-to-end tracing). Generate a UUID if not provided.

2. **Bind request ID to log context** — using structlog's context variables, every log entry within the request automatically includes the request ID.

3. **Return request ID in response headers** — add `X-Request-ID` to every response. When a user reports "I got an error," they can provide the request ID, and you can grep your logs for the entire request lifecycle.

4. **Add request timing** — measure total request duration in middleware. Log it on every response. This gives you latency visibility without metrics infrastructure.

### Best Practices

- **Include request ID in error responses** — when returning a 500 error, include the request ID in the response body. The user can reference it in bug reports.
- **Propagate to downstream services** — if CodeCrafter calls external APIs in the future, pass the request ID as a header for distributed tracing.

---

## 7.6 Security Hardening Checklist

This is a comprehensive checklist. Work through it systematically after the application is deployed.

### API Security
- [ ] All endpoints except `/health`, `/ready`, `/auth/*` require JWT authentication
- [ ] Auth endpoints rate limited to 5 requests/minute per IP (brute force protection)
- [ ] Chat endpoints rate limited to 30 requests/minute per user
- [ ] Input validation: message max 10KB, file max 5MB, filename max 255 chars
- [ ] SQL injection prevented (SQLAlchemy parameterized queries — verify no raw SQL)
- [ ] XSS prevented (React auto-escapes output + CSP headers block inline scripts)
- [ ] CSRF protection via SameSite cookie attribute + strict CORS origins
- [ ] Passwords hashed with bcrypt, cost factor 12
- [ ] JWT tokens expire after 60 minutes
- [ ] Failed auth attempts don't reveal whether email exists ("Invalid credentials" for both)
- [ ] Error responses don't include stack traces in production

### Sandbox Security
- [ ] Each user workspace isolated at `workspaces/{uuid}/`
- [ ] Path traversal checks on ALL file operations (read, write, edit, delete, run)
- [ ] Command blocklist enforced for `run_command` (existing patterns in `run_command.py`)
- [ ] Execution timeouts: 30s for code, 60s for commands (prevent infinite loops)
- [ ] Workspace size limit: 50MB per user
- [ ] File count limit: 500 files per workspace
- [ ] No symlink following (symlinks could escape the sandbox)

### Infrastructure Security
- [ ] All containers run as non-root users
- [ ] No secrets in Docker images (verify with `docker history`)
- [ ] `.env` file permissions: `chmod 600`
- [ ] TLS 1.2+ only, strong cipher suites
- [ ] Security headers set by nginx (CSP, HSTS, X-Frame-Options, etc.)
- [ ] Firewall allows only ports 22, 80, 443
- [ ] SSH: key auth only, root login disabled
- [ ] Docker images scanned for CVEs (use `docker scout cves` or Trivy)
- [ ] Dependency audit: `uv run pip-audit` to check for known vulnerabilities

### Data Protection
- [ ] User passwords never logged
- [ ] JWT tokens never logged in full
- [ ] Chat messages not sent to third-party services (Sentry, analytics) without consent
- [ ] Backups encrypted if stored off-site
- [ ] Database accessible only from Docker network, not from public internet

---

## 7.7 Alerting

### What To Set Up

Define alert rules in Prometheus that fire when things go wrong:

1. **High error rate** — if more than 10% of chat requests fail over a 5-minute window, something is broken. Severity: critical.

2. **High latency** — if P95 chat latency exceeds 30 seconds for 5 minutes, the models may be overloaded or Ollama is struggling. Severity: warning.

3. **All models failing** — if more than 5 model fallbacks occur in 10 minutes, all models in the chain may be down. Severity: critical.

4. **High memory usage** — if any container exceeds 90% of its memory limit for 5 minutes, it's at risk of OOM kill. Severity: warning.

5. **Disk space low** — if disk usage exceeds 85%, backups and logs may fail. Severity: warning.

6. **Health check failing** — if `/health` returns non-200 for 2 minutes, the API is down. Severity: critical.

### How To Route Alerts

- **Prometheus AlertManager** — receives alerts from Prometheus, deduplicates, and routes to notification channels.
- **Notification channels** — Discord webhook, Slack webhook, email, or PagerDuty depending on your setup.
- **Alert fatigue prevention** — don't alert on everything. Only alert on conditions that require human action. Use dashboards for informational monitoring.

### Best Practices

- **Test every alert** — intentionally trigger each alert condition and verify the notification arrives. An alert you've never seen fire is an alert you can't trust.
- **Include runbook links** — each alert should link to a document explaining: what does this mean, what should I check, how do I fix it.
- **Escalation** — critical alerts should notify immediately (push notification). Warnings can wait for daily review.

---

## 7.8 Performance Optimization

### Identify Before Optimizing

Use the metrics and logs from this phase to identify actual bottlenecks before optimizing. Common areas:

1. **API response caching** — cache model list, workspace tree, and other read-heavy endpoints in Redis. Set short TTLs (30-60 seconds) to balance freshness vs. performance.

2. **Database connection pooling** — SQLAlchemy async pool should be sized at 20 connections with 10 max overflow. Monitor pool exhaustion in logs.

3. **Gzip compression** — configure nginx to compress text, JSON, CSS, JS, and SVG responses. Typical 60-80% size reduction on text content.

4. **Frontend code splitting** — React.lazy() for page-level splitting. Users downloading the landing page shouldn't also download the chat interface code.

5. **Static asset caching** — nginx serves frontend assets with 30-day cache and `immutable` flag. Vite hashes filenames, so cache invalidation happens automatically on new builds.

6. **WebSocket keep-alive** — send ping frames every 30 seconds. Prevents nginx and intermediary proxies from closing idle connections.

7. **Ollama model preloading** — on application startup, send a dummy request to Ollama to load the model into memory. First real user request gets fast response instead of waiting for model load.

8. **Database indexes** — ensure indexes exist on: `users.email`, `chat_sessions.user_id`, `chat_sessions.updated_at`. Missing indexes cause full table scans as data grows.

### Best Practices

- **Measure, don't guess** — use Prometheus metrics to identify what's actually slow before spending time optimizing.
- **Set performance budgets** — P95 chat latency should be under 30 seconds. P95 REST API latency (non-chat) should be under 200ms. Lighthouse score > 90.
- **Load test before launch** — use `wrk`, `k6`, or `locust` to simulate concurrent users and find breaking points.

---

## Phase 7 Final Checklist

- [ ] Structured JSON logs in production, colored console in development
- [ ] Request IDs in every log entry and response header
- [ ] Prometheus `/metrics` endpoint serving custom metrics
- [ ] Grafana dashboard with request rate, latency, error rate, tool usage panels
- [ ] Sentry capturing unhandled exceptions with sanitized context
- [ ] All security checklist items verified and documented
- [ ] Alert rules configured and tested for: error rate, latency, fallbacks, memory, disk
- [ ] Log rotation configured (Docker logging driver limits)
- [ ] Can diagnose any production issue from logs + metrics alone (no SSH required for diagnosis)
- [ ] Performance baseline established and documented
