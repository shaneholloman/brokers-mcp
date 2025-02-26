# Use a Python base image (version can be adjusted)
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

# Set the working directory
WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-install-workspace --no-dev

COPY . /app
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT [ ]

# Make the startup script executable
RUN chmod +x run_all_services.sh

# Expose the ports used by the services (optional but good practice)
EXPOSE 8001
EXPOSE 8002
EXPOSE 8003

# Set the default command to run your script
CMD ["./run_all_services.sh"]
 