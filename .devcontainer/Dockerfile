# =============================================================================
# RuneMaster DevContainer Dockerfile
# Multi-stage build for optimized image size and build performance
# =============================================================================

# Stage 1: Builder stage for compiling dependencies
FROM python:3.12-slim-bookworm AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer & project manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set uv cache location for better layer caching
ENV UV_CACHE_DIR=/tmp/uv-cache

# Copy requirements first for better layer caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN uv pip install --no-cache-dir --prefix /install -r /tmp/requirements.txt

# Install aider-chat globally (pinned version for reproducibility)
RUN uv pip install --no-cache-dir --prefix /install aider-chat==0.74.2

# =============================================================================
# Stage 2: Final runtime image
FROM python:3.12-slim-bookworm AS runtime

ENV DEBIAN_FRONTEND=noninteractive

# System deps: git (aider, copilot), curl/jq (AI CLI bootstrapping),
#              ssh-client (git push/pull from container)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    jq \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Copy uv from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy installed Python packages from builder stage
COPY --from=builder /install /usr/local

# Create non-root user (VS Code devcontainers expect 'vscode')
RUN useradd -m -s /bin/bash vscode \
    && mkdir -p /home/vscode/.config \
    && chown -R vscode:vscode /home/vscode

WORKDIR /workspaces/rune_master
USER vscode
