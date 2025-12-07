# Base on the official ESI OpenFOAM image
FROM opencfd/openfoam-default:2406

# Switch to root to install system dependencies
USER root

# Install Python and basic build tools
# uv is used for project management
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-venv \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Set Up Environment
ENV PATH="/root/.cargo/bin:$PATH"

# Create a work directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY templates ./templates
COPY examples ./examples
COPY README.md ./

# Install project dependencies
RUN uv sync --frozen

# Copy and setup entrypoint script
COPY scripts/docker-entrypoint.sh /usr/local/bin/run-analysis
RUN chmod +x /usr/local/bin/run-analysis

# Default command
ENTRYPOINT ["/usr/local/bin/run-analysis"]
CMD ["--help"]
