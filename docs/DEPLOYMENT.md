# VERITAS — Production Deployment Guide

This guide details the steps required to deploy the **VERITAS Enterprise AI Governance & NIST AI RMF Platform** into production environments.

---

## 1. Architecture Overview

VERITAS is composed of two primary application tiers and an optional reverse proxy:

```
                          [ Client Browser / Auditor ]
                                       │
                                       ▼
                       [ Nginx Reverse Proxy (Port 80/443) ]
                                ┌──────┴──────┐
             Path: /api/*       │             │       Path: /*
                                ▼             ▼
     [ FastAPI Backend (Port 8000) ]       [ Next.js Frontend (Port 3000) ]
        • Gunicorn + Uvicorn Workers          • Next.js Standalone Node Server
        • LangGraph Audit Checkpointer        • Static & SSR React 18 UI
        • Statistical & Permutation Engines   • Internal API Proxy Rewrites
                                │
                                ▼
                   [ Persistent Local Storage ]
                      outputs/api_data/veritas_runs.sqlite
                      outputs/api_data/checkpoints.sqlite
```

---

## 2. Prerequisites

- **Docker Engine**: Version 24.0+ and **Docker Compose** v2.20+
- **Host OS**: Linux (Ubuntu 22.04 LTS / Debian 12 / RHEL 9 recommended), macOS, or Windows Server with WSL2
- **Memory**: 4 GB RAM minimum (8 GB recommended for large dataset permutation tests)
- **CPU**: 2+ vCPUs recommended
- **Disk**: 10 GB free space for Docker images and audit database logs

---

## 3. Quick Start: Docker Compose Deployment

The fastest and most robust way to deploy VERITAS is via the included `docker-compose.yml`.

### Step 1: Clone the repository and configure environment
```bash
git clone https://github.com/Emperor2004/VERITAS.git
cd VERITAS

# Create your production environment file
cp .env.example .env
```

Edit `.env` to configure your LLM provider and ports:
```ini
# Optional: Set your LLM provider (Ollama or Gemini)
VERITAS_LLM_PROVIDER=gemini
GOOGLE_API_KEY=AIzaSy...your_actual_key

# Optional: Custom domain / CORS settings
VERITAS_CORS_ORIGINS=http://localhost:3000,https://audit.yourorganization.com
```

### Step 2: Build and launch containers
```bash
# Build production images and start services in the background
docker compose up --build -d
```

### Step 3: Verify container health
```bash
# Check service status and health checks
docker compose ps

# View unified application logs
docker compose logs -f
```

Both containers have native health checks configured:
- Backend: `GET /api/health`
- Frontend: `GET /`

Open **`http://localhost:3000`** in your browser.

---

## 4. Production Hardening & Configuration

### Environment Variables Reference

| Variable | Default | Description |
|---|---|---|
| `PORT` | `8000` (backend) / `3000` (frontend) | Port for the HTTP server process |
| `WORKERS` | `2` | Number of Gunicorn Uvicorn workers for API concurrency |
| `VERITAS_DB_PATH` | `/app/outputs/api_data/veritas_runs.sqlite` | SQLite database file for audit runs |
| `VERITAS_CHECKPOINT_DB_PATH` | `/app/outputs/api_data/checkpoints.sqlite` | LangGraph human-in-the-loop checkpoint store |
| `VERITAS_CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated list of permitted CORS origins |
| `VERITAS_LLM_PROVIDER` | `""` | `gemini` or `ollama`. If omitted, runs in deterministic audit mode |
| `GOOGLE_API_KEY` | `""` | Google Gemini API key (if `gemini` provider chosen) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama service URL (if `ollama` provider chosen) |

---

## 5. HTTPS Reverse Proxy with Nginx & Let's Encrypt

For secure enterprise deployment, run Nginx as a reverse proxy with TLS/SSL termination:

1. Copy `nginx/nginx.conf` to `/etc/nginx/sites-available/veritas.conf`
2. Update the `server_name` directive with your company domain (e.g., `audit.company.com`).
3. Obtain a free SSL certificate with Let's Encrypt Certbot:
   ```bash
   sudo apt install certbot python3-certbot-nginx
   sudo certbot --nginx -d audit.company.com
   ```
4. Verify Nginx configuration and reload:
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

---

## 6. Backup & Disaster Recovery

Audit runs and LangGraph state checkpoints are stored in SQLite inside the Docker named volume `veritas-data` (or directory `./outputs/api_data`).

### Automated Daily Backup Script
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/veritas"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Safe hot-backup using SQLite backup API
docker exec veritas-backend sqlite3 /app/outputs/api_data/veritas_runs.sqlite \
  ".backup '$BACKUP_DIR/veritas_runs_$TIMESTAMP.sqlite'"

docker exec veritas-backend sqlite3 /app/outputs/api_data/checkpoints.sqlite \
  ".backup '$BACKUP_DIR/checkpoints_$TIMESTAMP.sqlite'"

# Compress and purge backups older than 30 days
tar -czf "$BACKUP_DIR/veritas_backup_$TIMESTAMP.tar.gz" -C "$BACKUP_DIR" \
  "veritas_runs_$TIMESTAMP.sqlite" "checkpoints_$TIMESTAMP.sqlite"
rm "$BACKUP_DIR"/*.sqlite
find "$BACKUP_DIR" -type f -mtime +30 -name "veritas_backup_*.tar.gz" -delete
```

---

## 7. Continuous Integration & Delivery (CI/CD)

The repository includes a ready-to-use GitHub Actions workflow at [`.github/workflows/ci.yml`](file:///d:/Studies/semester7/B%20Tech%20Project/VERITAS/.github/workflows/ci.yml):

- **Backend Matrix Testing**: Runs `pytest tests/` across Python 3.10, 3.11, and 3.12 with JUnit XML and coverage artifacts.
- **Frontend Type & Build Verification**: Runs TypeScript compilation check (`tsc --noEmit`) and Next.js production build (`npm run build`).
- **Docker Validation**: Uses Buildx and GitHub caching to verify that `Dockerfile.backend` and `frontend/Dockerfile` build with zero errors on every push and pull request.
