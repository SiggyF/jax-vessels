# Switch to a standard Ubuntu base
FROM ubuntu:22.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Run as root by default to avoid permission complexity
USER root

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg2 \
    lsb-release \
    software-properties-common \
    python3-pip \
    python3-venv \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Add OpenFOAM repository (using dl.openfoam.com)
RUN curl -s https://dl.openfoam.com/add-debian-repo.sh | bash
# Install OpenFOAM (v2406)
RUN apt-get update && apt-get install -y openfoam2406-default && rm -rf /var/lib/apt/lists/*

# Install uv (system-wide)
ENV UV_INSTALL_DIR="/usr/local/bin"
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup Work Directory
WORKDIR /app

# Setup venv in a standard location
ENV UV_PROJECT_ENVIRONMENT="/app/.venv"
ENV VIRTUAL_ENV="/app/.venv"
ENV PATH="/app/.venv/bin:$PATH"

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY templates ./templates
COPY examples ./examples
COPY README.md ./

# Install python dependencies
RUN uv sync --frozen

# Copy runner script
COPY scripts/run_analysis.sh /usr/local/bin/run-analysis
RUN chmod +x /usr/local/bin/run-analysis

# Reset entrypoint to be safe
ENTRYPOINT []
# Default command: run the python tool help via the wrapper
CMD ["run-analysis", "openfoam-run", "--help"]
