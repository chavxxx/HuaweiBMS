# Multi-stage production build for Huawei EMS B1 Battery Manager
# Stage 1: Build React 19 Frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# Stage 2: Python 3.12 Native Serial & Web Service
FROM python:3.12-slim-bookworm AS production
WORKDIR /app

# Install system dependencies for serial & compilation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY data/ ./data/

# Copy built frontend assets from stage 1
COPY --from=frontend-builder /build/dist ./frontend/dist

# Expose Web and WebSocket port
EXPOSE 8000

ENV PYTHONPATH=/app/backend
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Start unified production server
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
