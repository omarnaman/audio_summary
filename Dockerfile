# Use an official Python runtime as a parent image
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set the working directory in the container
WORKDIR /app


# Sync uv requirements
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev

# Copy the rest of the application's code into the container
COPY . .

# Make port 5000 available to the world outside this container
EXPOSE 5000

# Run app.py when the container launches
CMD ["uv", "run", "app.py"]
