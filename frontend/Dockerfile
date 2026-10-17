# =============================================================================
# VERITAS — Next.js Frontend (Production)
# =============================================================================
# Multi-stage build: deps → build → runtime (standalone output)
# Usage:
#   docker build -f Dockerfile.frontend -t veritas-frontend ./frontend
#   docker run -p 3000:3000 veritas-frontend
# =============================================================================

# --- Stage 1: Install dependencies ---
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --production=false


# --- Stage 2: Build the production bundle ---
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Backend API URL for the rewrite proxy (resolved at build time)
ARG BACKEND_API_URL=http://backend:8000
ENV BACKEND_API_URL=${BACKEND_API_URL}

# Next.js standalone output for minimal Docker image
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# --- Stage 3: Production runtime ---
FROM node:20-alpine AS runner

WORKDIR /app

# Security: run as non-root
RUN addgroup --system --gid 1001 nextjs && \
    adduser --system --uid 1001 nextjs

# Copy only what's needed for standalone runtime
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nextjs /app/.next/static ./.next/static

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME="0.0.0.0"

EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:${PORT}/ || exit 1

USER nextjs

CMD ["node", "server.js"]
