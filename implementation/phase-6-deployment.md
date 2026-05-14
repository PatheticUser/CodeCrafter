# Phase 6 — Deployment

> **Effort:** ~2 days · **Dependencies:** Phase 4, 5  
> **Goal:** Get CodeCrafter live on a production server with TLS, DNS, automated backups, and zero-downtime update capability.

---

## 6.1 Infrastructure Selection

### Decision Framework

Choose based on budget, scale needs, and operational experience:

**Budget MVP (recommended to start):**
- Hetzner CX22 or DigitalOcean Droplet — 2 vCPU, 4GB RAM, ~$5-12/month
- Plenty for a single-user or small-team deployment
- Full control, learn the ops fundamentals

**Managed ease:**
- Railway or Render — git-push deploys, managed databases, auto-TLS
- Higher cost, less control, faster time-to-live
- Good if you want to focus on product, not infrastructure

**Scale-ready:**
- AWS ECS/Fargate or GCP Cloud Run — container orchestration, auto-scaling
- Significantly more complex and expensive
- Only worth it when you need horizontal scaling

### What To Provision

Regardless of provider, you need:
- A VPS/instance with Docker and Docker Compose installed
- A domain name pointed at the server's IP
- SSH access with key-based authentication (no passwords)

---

## 6.2 Server Initial Setup

### What To Do

1. **SSH into server as root** — initial setup only, then disable root access.

2. **Create a dedicated deploy user**:
   - Non-root user with Docker group membership (can run `docker` commands without `sudo`)
   - SSH key authentication only
   - Home directory for the application
   - No password — SSH keys only

3. **Install Docker and Docker Compose plugin**:
   - Use the official Docker install script
   - Enable Docker systemd service (starts on boot)
   - Verify with `docker run hello-world`

4. **Configure firewall**:
   - Allow SSH (port 22)
   - Allow HTTP (port 80) — needed for Let's Encrypt and HTTP→HTTPS redirect
   - Allow HTTPS (port 443)
   - Block everything else — postgres, redis, ollama should NEVER be exposed to the internet
   - Enable the firewall

5. **Harden SSH**:
   - Disable root login (`PermitRootLogin no`)
   - Disable password authentication (`PasswordAuthentication no`)
   - Restart SSH service
   - **Test that you can still SSH in with your key before closing the current session!**

6. **Create application directory**:
   - `/opt/codecrafter/` owned by the deploy user
   - Clone the repository or set up for git pull deployments

### Best Practices

- **Test SSH access before disabling root** — locking yourself out of a server is not fun. Keep your root session open while testing the deploy user.
- **Use fail2ban** — install it to automatically ban IPs with too many failed SSH attempts.
- **Set up unattended-upgrades** — automatic security patches for the OS. Critical for long-running servers.
- **Use a swap file** — even with 4GB RAM, a 2GB swap prevents OOM kills during peak load.

---

## 6.3 TLS Certificate Setup

### What To Do

1. **Install Certbot** — the standard tool for free Let's Encrypt TLS certificates.

2. **Point DNS first** — the domain must resolve to your server IP before Certbot can verify it. Set up the A record and wait for propagation (usually minutes, sometimes hours).

3. **Run Certbot** — use the nginx plugin which automatically configures nginx. This handles certificate issuance and nginx config updates.

4. **Configure auto-renewal** — Certbot certificates expire every 90 days. Set up a cron job to renew every day at 3 AM (it only renews when within 30 days of expiry). After renewal, restart nginx to pick up new certs.

5. **Update nginx config** for production:
   - HTTP (port 80) redirects all traffic to HTTPS (301 permanent redirect)
   - HTTPS (port 443) serves the application with strong TLS settings
   - TLS protocols: only TLSv1.2 and TLSv1.3 (disable older versions)
   - Strong cipher suites (ECDHE-based)
   - HSTS header with 2-year max-age
   - OCSP stapling for faster TLS handshakes

### Best Practices

- **Test with SSL Labs** — after setup, run your domain through ssllabs.com/ssltest. Target A+ rating. Fix any warnings.
- **Add a CAA DNS record** — `CAA 0 issue "letsencrypt.org"` restricts which CAs can issue certificates for your domain. Prevents unauthorized cert issuance.
- **Monitor certificate expiry** — set up an alert (cron + script, or external service like UptimeRobot) that warns you 14 days before expiry. Auto-renewal usually works, but failures happen.

---

## 6.4 DNS Configuration

### What To Set Up

At your domain registrar or DNS provider:

1. **A record** — `codecrafter.yourdomain.com` → server IP address. TTL: 300 seconds (5 min) initially, increase to 3600 once stable.

2. **CNAME record** — `www.codecrafter.yourdomain.com` → `codecrafter.yourdomain.com`. Redirects www to non-www.

3. **CAA record** — `codecrafter.yourdomain.com` → `0 issue "letsencrypt.org"`. Restricts certificate issuance.

### Best Practices

- **Low TTL during setup** — 300 seconds lets you fix mistakes quickly. Increase to 3600+ once DNS is stable.
- **Test propagation** — use `dig codecrafter.yourdomain.com` or an online tool to verify DNS resolves correctly before running Certbot.

---

## 6.5 Production Environment Configuration

### What To Do

1. **Create `.env.prod` on the server** — this file lives at `/opt/codecrafter/.env` and is NEVER committed to git. Contains all production secrets:
   - `ENVIRONMENT=production`
   - `DEBUG=false`
   - Database URL with strong password
   - Redis URL
   - JWT secret (generated with `openssl rand -hex 32`)
   - Frontend URL (your public HTTPS URL)
   - Rate limiting values (tighter than dev)

2. **Generate all secrets fresh**:
   - JWT secret: `openssl rand -hex 32`
   - Postgres password: `openssl rand -base64 24`
   - Any other keys: unique, random, long

3. **Restrict file permissions** — `chmod 600 .env` so only the owner can read it.

### Best Practices

- **Never reuse dev secrets in production** — generate new values for every environment.
- **Rotate secrets periodically** — JWT secrets should be rotated quarterly. Database passwords less frequently.
- **Document which secrets exist** — the `.env.example` in the repo should list every variable with placeholder values and descriptions.
- **Consider a secrets manager** — for larger deployments, HashiCorp Vault or cloud-native solutions (AWS Secrets Manager) are more secure than `.env` files.

---

## 6.6 Backup Strategy

### What To Back Up

1. **PostgreSQL database** — the most critical data (users, sessions, chat history)
2. **User workspaces** — files created by users through the agent
3. **Ollama models** — optional, these can be re-downloaded but it saves time

### What NOT To Back Up
- Redis data (ephemeral cache, rate limiting state — reconstructed automatically)
- Docker images (pulled from registry)
- Application code (lives in git)

### How To Back Up

1. **Database**: Use `pg_dump` from inside the postgres container, output to a compressed dump file on the host. Run daily at 2 AM via cron.

2. **Workspaces**: Tar and compress the workspaces directory. Run daily after the DB backup.

3. **Retention**: Keep 30 days of backups. Delete older ones automatically. This balances storage cost vs. recovery options.

4. **Off-site storage**: Copy backups to a different server, S3 bucket, or similar. Local backups don't help if the server's disk fails.

### Restore Procedure

Document and TEST this before you need it:

1. **Database**: `pg_restore` with `--clean --if-exists` flags into the postgres container
2. **Workspaces**: Extract tar archive to the workspace volume mount point
3. **Verify**: Run health checks, test login, verify recent sessions exist

### Best Practices

- **Test restores regularly** — a backup you've never tested is not a backup. Do a full restore to a test environment monthly.
- **Encrypt backups** — if backing up to off-site storage, encrypt with `gpg` or `age`. Backups contain user data and hashed passwords.
- **Monitor backup jobs** — the backup script should log success/failure. Alert on failure. A silently failing backup cron job is worse than no backups (false sense of security).
- **Database backups should be consistent** — `pg_dump` creates a consistent snapshot. Never backup by copying raw postgres data files while the database is running.

---

## 6.7 Deploy Process

### Manual Deploy (First Time)

1. SSH into server as deploy user
2. Clone the repository: `git clone ... /opt/codecrafter`
3. Copy `.env.prod` to `/opt/codecrafter/.env`
4. Build and start: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d`
5. Run initial database migration
6. Verify health: `curl https://codecrafter.yourdomain.com/health`

### Automated Deploy (Subsequent)

The CI/CD pipeline (Phase 5) handles this, but the script should:

1. Pull latest code (`git pull`)
2. Pull latest Docker images (`docker compose pull`)
3. Run database migrations
4. Restart containers with new images (`docker compose up -d --remove-orphans`)
5. Wait for health checks to pass
6. Clean up old images (`docker image prune -f`)

### Rollback

If a deploy breaks things:
1. Identify the last working commit SHA
2. Pull that specific image tag: `docker compose pull image:specific-sha`
3. Restart with the old images
4. Rollback database migration if needed: `alembic downgrade -1`
5. Investigate the issue on a non-production environment

### Best Practices

- **Deploy during low-traffic periods** — if you have usage patterns, deploy during off-hours.
- **Watch logs after deploy** — `docker compose logs -f api` for the first few minutes after deploying. Catch issues early.
- **Canary deploys** — if running multiple API replicas, update one first, verify it works, then update the rest.
- **Keep the last 3 image tags** — don't prune too aggressively. You need rollback targets.

---

## 6.8 Resource Management

### What To Configure

Set resource limits in the production compose override:

- **API container**: 1GB memory limit, 1 CPU. Reservation: 256MB. Run 2 replicas.
- **PostgreSQL**: 512MB memory limit. Reservation: 128MB.
- **Redis**: 256MB memory limit. Reservation: 64MB.
- **Ollama**: 4GB+ memory depending on model size. This is the heaviest container. On a 4GB VPS, you may need to run Ollama on a separate machine or use cloud-hosted inference.
- **Nginx**: minimal — 128MB is plenty.

### Best Practices

- **Total container memory < host RAM** — leave 500MB-1GB for the OS, Docker daemon, and buffers. Overcommitting leads to OOM kills.
- **Monitor disk space** — Docker images, logs, and postgres data accumulate. Set up log rotation (`docker compose logs` are stored in `/var/lib/docker/containers/`). Clean old images regularly.
- **Set ulimits** — limit open file descriptors per container to prevent resource exhaustion from buggy code.

---

## Phase 6 Final Checklist

- [ ] App accessible at `https://codecrafter.yourdomain.com`
- [ ] HTTP requests redirect to HTTPS (301)
- [ ] SSL Labs test returns A+ rating
- [ ] Health check returns 200 from public URL
- [ ] Daily database backup runs and completes successfully
- [ ] Backup restore has been tested at least once
- [ ] Deploy script runs with minimal downtime
- [ ] Firewall blocks all non-essential ports
- [ ] SSH uses key auth only, root login disabled
- [ ] Resource limits prevent single container from exhausting host
- [ ] All secrets generated fresh, not reused from dev
- [ ] `.env` file permissions restricted to owner only
- [ ] Log rotation configured for Docker container logs
