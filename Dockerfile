# Switch to a standard Ubuntu base
FROM ubuntu:24.04

# Avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

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

# Source OpenFOAM environment for all interactive shells
RUN echo "source /usr/lib/openfoam/openfoam2406/etc/bashrc" >> /etc/bash.bashrc

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

# Copy entrypoint script (while still root)
COPY scripts/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Change ownership of the app directory to the ubuntu user
RUN chown -R ubuntu:ubuntu /app

# Switch to the non-root 'ubuntu' user (UID 1000)
USER ubuntu

# Reset entrypoint to use the script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
# Default command: run the python tool help via the wrapper
CMD ["run-analysis", "openfoam-run", "--help"]
