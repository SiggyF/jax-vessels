# Common Base
FROM ubuntu:24.04 AS base
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /app

# Install system dependencies (Common)
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg2 \
    lsb-release \
    software-properties-common \
    sudo \
    git \
    libgl1 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Stage 2: OpenFOAM Environment
FROM base AS openfoam
WORKDIR /app

# Add OpenFOAM Repo
RUN curl -s https://dl.openfoam.com/add-debian-repo.sh | bash

# Install OpenFOAM
RUN apt-get update && apt-get install -y openfoam2406-default && rm -rf /var/lib/apt/lists/*

# Source OpenFOAM
RUN echo "source /usr/lib/openfoam/openfoam2406/etc/bashrc" >> /etc/bash.bashrc

# Copy Scripts (OpenFOAM specific wrappers)
COPY scripts/run_analysis.sh /usr/local/bin/run-analysis
RUN chmod +x /usr/local/bin/run-analysis
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# User Setup (OpenFOAM often requires root for some tasks, or user switching)
# Keeping standard setup for simulation
RUN chown -R 1000:1000 /app
USER 1000:1000
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["run-analysis"]

# Stage 3: Python Environment (Analysis)
FROM base AS python-env
WORKDIR /app

# Python specific deps
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Setup User
RUN chown -R 1000:1000 /app
USER 1000:1000

# Install uv (user local)
ENV UV_INSTALL_DIR="/home/ubuntu/.local/bin"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/ubuntu/.local/bin:$PATH"
ENV UV_PROJECT_ENVIRONMENT="/app/.venv"
ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="/app/.venv/bin:$PATH"

# Copy Project Definitions
COPY --chown=1000:1000 pyproject.toml uv.lock ./
COPY --chown=1000:1000 src ./src
COPY --chown=1000:1000 templates ./templates
COPY --chown=1000:1000 examples ./examples
COPY --chown=1000:1000 README.md ./

# Install Python Dependencies
RUN uv sync --frozen

# Default command
CMD ["uv", "run", "python"]
