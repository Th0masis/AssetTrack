# ─── Builder stage ─────────────────────────────────────────────────────────────
FROM python:3.11-alpine AS builder

WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ─── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.11-alpine AS runtime

# Non-root user with fixed UID 1000 (matches typical host user)
RUN addgroup -g 1000 -S appgroup && adduser -u 1000 -S appuser -G appgroup

WORKDIR /app

# Install runtime deps + fonty s českou diakritikou pro PDF štítky
RUN apk add --no-cache libffi ttf-dejavu

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY --chown=appuser:appgroup . .

# Create data directory and make entrypoint executable
RUN mkdir -p /app/data && chown appuser:appgroup /app/data && chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:8000/health || exit 1

CMD ["/bin/sh", "/app/entrypoint.sh"]
