FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

# System deps: git (aider, copilot), curl/jq (AI CLI bootstrapping),
#              ssh-client (git push/pull from container)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    jq \
    openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer & project manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install Python dependencies with uv (layer-cached — only re-runs when requirements.txt changes)
COPY requirements.txt /tmp/requirements.txt
RUN uv pip install --no-cache-dir -r /tmp/requirements.txt

# Install aider-chat globally so it's available out of the box
# (pinned version for reproducibility; update as needed)
RUN uv pip install --no-cache-dir aider-chat==0.74.2

# Create non-root user (VS Code devcontainers expect 'vscode')
RUN useradd -m -s /bin/bash vscode \
    && mkdir -p /home/vscode/.config \
    && chown -R vscode:vscode /home/vscode

WORKDIR /workspaces/rune_master
USER vscode
