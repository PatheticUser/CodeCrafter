# Deploying CodeCrafter on Oracle Cloud (Always Free ARM64) behind Caddy

Self-contained, production deployment for an **Ubuntu 24.04 LTS ARM64 (Ampere A1)** VM on
Oracle Cloud Infrastructure. This replaces the previous Google Cloud Run setup
(`cloudbuild.yaml` is obsolete for this deployment and can be deleted).

```
Internet ──80/443──▶ caddy (auto TLS, WS/SSE) ──backend bridge net──▶ app:8000 (FastAPI)
```

## Files in this deployment

| File | Purpose |
|---|---|
| `Dockerfile` | Multi-arch image (linux/amd64 + linux/arm64/aarch64), uv-locked deps, non-root |
| `docker-compose.yml` | `app` + `caddy` services, healthchecks, log rotation, `restart: unless-stopped`, dedicated bridge network |
| `.env.production` | All runtime keys (copy from `.env.production` template, fill in real values) |
| `Caddyfile` | Auto-TLS site → `app:8000` with WebSocket upgrade headers + SSE flushing |

Internal port **8000 is never published on the host** — only Caddy binds
public ports (80/tcp, 443/tcp+udp).

The app is **stateless**: config comes only from `.env.production` env vars,
session state is per-request in memory, and workspace files live exclusively on
the external named volume `codecrafter-workspace` — never on the container
filesystem — so containers can be destroyed, updated, and redeployed without
data loss.

---

## 1. ARM64 compatibility audit (verified, not assumed)

Checked against `uv.lock` — the build has **no x86-only artifacts**:

- **Base images**: `ghcr.io/astral-sh/uv:0.5-python3.11-bookworm-slim`,
  `python:3.11-slim-bookworm`, `caddy:2` all publish `arm64/v8` manifests —
  no QEMU/emulation needed when building natively on the Ampere A1.
- **Pure-Python deps** (arch-independent): `fastapi`, `openai`,
  `pydantic-settings`, `requests`, `rich`, `sse-starlette`, `uvicorn`,
  `python-docx`.
- **Only compiled wheel**: `pygame` resolves to
  `pygame-2.6.1-cp311-cp311-manylinux_2_17_aarch64.manylinux2014_aarch64.whl`
  (SDL is bundled inside the wheel — no system audio libs required).
- **PyTorch / C/C++ extensions / audio libraries / VAD / TTS runtime**:
  **not present in this repository** — nothing to cross-compile for aarch64.
  If such dependencies are added later, install them in the `deps` stage of
  the `Dockerfile` with `--platform=$BUILDPLATFORM` awareness and verify
  `uv pip compile --python-platform linux_aarch64`.
- Native build on the VM produces `linux/arm64` automatically; confirm with
  `docker compose exec app uname -m` → `aarch64`.

---

## 2. OCI VCN security list (layer 1 — cloud firewall)

Console: **Networking → Virtual Cloud Networks → *your VCN* → Security Lists →
Default Security List → Add Ingress Rules**:

| Type | Protocol | Source | Destination | Purpose |
|---|---|---|---|---|
| Ingress | TCP 80 | `0.0.0.0/0` | — | HTTP + ACME challenge |
| Ingress | TCP 443 | `0.0.0.0/0` | — | HTTPS |
| Ingress | UDP 443 | `0.0.0.0/0` | — | HTTP/3 (QUIC), optional |
| Ingress | ICMP 3,4 | `0.0.0.0/0` | — | Path MTU discovery (recommended) |
| Ingress | TCP 22 | `<your-ip>/32` | — | SSH — restrict to your IP, never `0.0.0.0/0` |

Do **not** open 8000 at the VCN layer. If you use a Network Security Group
instead, apply the same rules to the subnet NIC.

Equivalent via OCI CLI (adjust the OCID):

```bash
oci network security-list update \
  --security-list-id <vcn-security-list-ocid> \
  --ingress-security-rules \
    '[{"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":80,"max":80}}},
      {"protocol":"6","source":"0.0.0.0/0","tcpOptions":{"destinationPortRange":{"min":443,"max":443}}},
      {"protocol":"17","source":"0.0.0.0/0","udpOptions":{"destinationPortRange":{"min":443,"max":443}}}]'
```

---

## 3. Host firewall on Ubuntu (layer 2 — ufw)

**Keep your SSH session open while doing this** (new rules applied before
`enable`, so you won't be locked out):

```bash
sudo apt-get update && sudo apt-get install -y ufw

sudo ufw default deny incoming
sudo ufw default allow outgoing

sudo ufw allow OpenSSH                  # MUST come before `ufw enable`
sudo ufw allow 80/tcp                   # HTTP + Let's Encrypt HTTP-01
sudo ufw allow 443/tcp                  # HTTPS
sudo ufw allow 443/udp                  # HTTP/3 (QUIC)

sudo ufw --force enable
sudo ufw status verbose                 # verify: Status: active, rules listed
```

### Alternative: raw iptables (use instead of ufw, not both)

```bash
sudo apt-get install -y iptables-persistent

# -I INPUT 1 inserts at the TOP, ahead of any DROP/REJECT rules
sudo iptables  -I INPUT 1 -p tcp --dport 80  -j ACCEPT
sudo iptables  -I INPUT 1 -p tcp --dport 443 -j ACCEPT
sudo iptables  -I INPUT 1 -p udp --dport 443 -j ACCEPT

# IPv6 equivalents (OCI enables IPv6 on some subnets)
sudo ip6tables -I INPUT 1 -p tcp --dport 80  -j ACCEPT
sudo ip6tables -I INPUT 1 -p tcp --dport 443 -j ACCEPT
sudo ip6tables -I INPUT 1 -p udp --dport 443 -j ACCEPT

sudo netfilter-persistent save           # persists across reboots
# (equivalent: sudo sh -c 'iptables-save  > /etc/iptables/rules.v4')
sudo iptables -L INPUT -n --line-numbers | head -20   # verify ordering
```

**Docker + ufw note:** Docker publishes containers through the `DOCKER` chain,
*bypassing* ufw. This is safe here because **only Caddy publishes ports** (80/443
which ufw allows anyway) and the **app container publishes nothing** — port
8000 is unreachable even from the host:

```bash
ss -tlnp | grep 8000     # → no results (nothing listens on host:8000)
```

---

## 4. Install Docker (arm64 supported by official repos)

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER"         # re-login for group membership
docker version --format '{{.Server.Os}}/{{.Server.Arch}}'
# → linux/arm64
```

---

## 5. Deploy

```bash
git clone <your-repo> /opt/codecrafter && cd /opt/codecrafter

# Fill in real values (GOOGLE_API_KEY, API_TOKEN, CORS_ORIGINS, CADDY_SITE, …)
nano .env.production
chmod 600 .env.production

# DNS: point yourdomain.example A record → VM public IP first (for TLS).

docker compose --env-file .env.production up -d --build
```

Caddy obtains/renews the Let's Encrypt certificate automatically on first
start (HTTP-01 on port 80). Certificates persist in the
`codecrafter-caddy-data` volume.

---

## 6. Verify the deployment

### Containers and healthchecks (`docker ps`)

```bash
docker compose ps
# or:
docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Expected:

```
NAMES                STATUS                    PORTS
codecrafter-caddy    Up X minutes (healthy)    0.0.0.0:80->80/tcp, 0.0.0.0:443->80/tcp...
codecrafter-app      Up X minutes (healthy)    8000/tcp        ← no host mapping
```

`(healthy)` comes from the compose healthchecks:

```bash
docker inspect --format '{{.State.Health.Status}}' codecrafter-app    # healthy
docker inspect --format '{{.State.Health.Status}}' codecrafter-caddy  # healthy
docker inspect --format '{{range .State.Health.Log}}{{.ExitCode}} {{.Output}}{{end}}' codecrafter-app
```

Confirm the image is really arm64:

```bash
docker compose exec app uname -m        # → aarch64
docker compose exec app python -c "import platform; print(platform.machine())"  # → aarch64
```

### Health endpoints

```bash
# 1) Directly inside the app container (bypasses proxy):
docker compose exec app curl -fsS http://127.0.0.1:8000/healthz
#    {"status":"ok","version":"3.0.0"}

docker compose exec app curl -i http://127.0.0.1:8000/readyz
#    HTTP/1.1 200 {"status":"ready"}       (503 → GOOGLE_API_KEY missing)

# 2) Through Caddy from the host:
curl -fsS -H 'Host: yourdomain.example' http://127.0.0.1/healthz   # pre-TLS / HTTP-only IP mode
curl -fsS https://yourdomain.example/healthz                        # TLS path (real domain)
curl -fsS https://yourdomain.example/readyz

# 3) From the internet (another machine):
curl -fsS https://yourdomain.example/healthz
curl -sS -o /dev/null -w 'docs → %{http_code}\n' https://yourdomain.example/docs
```

### API + streaming (SSE) smoke test

```bash
# Blocking turn (401/403 → API_TOKEN misconfigured; 422/200 → routing works):
curl -i -X POST https://yourdomain.example/v1/chat \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"list files"}]}'

# SSE streaming — must emit incremental `data: {...}` lines, then `data: [DONE]`:
curl -N -X POST https://yourdomain.example/v1/chat/stream \
  -H 'Authorization: Bearer YOUR_API_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"messages":[{"role":"user","content":"hello"}]}'
```

### Logs

```bash
docker compose logs -f --tail=100 app caddy
ls -lh /var/lib/docker/containers/*/*-json.log   # capped at 10 MB × 5 files per service
```

---

## 7. Day-2 operations

```bash
# Update after git pull:
docker compose --env-file .env.production up -d --build

# Restart / stop:
docker compose --env-file .env.production restart
docker compose --env-file .env.production down

# Back up TLS certs + workspace/sessions:
docker run --rm -v codecrafter-caddy-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/caddy-data-$(date +%F).tgz -C /data .
docker run --rm -v codecrafter-workspace:/ws -v codecrafter-sessions:/ss -v "$PWD":/backup alpine \
  sh -c 'tar czf /backup/codecrafter-state-$(date +%F).tgz -C / ws ss'

# Low-disk cleanup (Ampere A1 boot volume is 47 GB by default):
docker system df
docker compose --env-file .env.production down --rmi local   # old build layers
```

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| Caddy `502` | `docker compose logs caddy` — app not healthy yet; wait for `service_healthy` or check `app` logs |
| `/readyz` → 503 | `GOOGLE_API_KEY` missing/empty in `.env.production` |
| TLS cert failure | DNS A record must point at the VM IP **before** first start; check ports 80/443 reachable: `curl -v http://yourdomain.example/` |
| `caddy` stuck unhealthy | `docker compose exec caddy wget -qO- http://127.0.0.1:2019/config/` |
| Port conflict on 80/443 | `sudo ss -tlnp | grep -E ':80|:443'` — stop apache/nginx if present |
| SSH lockout after firewall change | OCI console → instance → Console Connection (serial), then `sudo ufw disable` |
