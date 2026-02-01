# Dockerfile for tau2-bench Green Agent (Hospitality Domain)
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including curl for healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management
RUN pip install uv

# Copy the entire tau2-bench project
COPY . /app/

# Install the main tau2 package
RUN pip install -e .

# Install agentify_tau_bench dependencies
WORKDIR /app/src/experiments/agentify_tau_bench
RUN uv sync

# Set environment variables
ENV PYTHONPATH=/app/src:/app/src/experiments/agentify_tau_bench/src
ENV TAU2_DATA_DIR=/app/data

# Expose ports for green and white agents
EXPOSE 9001 9002

# Environment variables for agent configuration
ENV ROLE=green
ENV HOST=0.0.0.0
ENV AGENT_PORT=9001
ENV AGENT_URL=http://localhost:9001

# Use ENTRYPOINT so docker-compose command becomes arguments
ENTRYPOINT ["uv", "run", "tau-bench-agent", "green"]
CMD []
