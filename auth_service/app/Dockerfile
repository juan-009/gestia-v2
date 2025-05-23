# Stage 1: Builder stage for installing dependencies with Poetry
FROM python:3.11-slim as builder

WORKDIR /opt/app

# Install Poetry
RUN pip install poetry

# Copy only files necessary for dependency installation
COPY pyproject.toml poetry.lock* ./
# poetry.lock* handles cases where poetry.lock might not exist initially

# Install dependencies - no-dev for production, no-root as we copy app code later
# Create a virtual environment within the image
RUN poetry config virtualenvs.in-project true && poetry install --no-dev --no-interaction --no-ansi

# Stage 2: Runtime stage
FROM python:3.11-slim

WORKDIR /opt/auth_service

# Set environment variables for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/app/.venv ./.venv

# Activate the virtual environment by adding its bin to PATH
ENV PATH="/opt/auth_service/.venv/bin:$PATH"

# Copy the application source code
# Ensure this path matches your project structure
COPY ./app ./app
# We'll create app/main.py later. For now, this sets up the structure.

EXPOSE 8000

# Command to run the application
# This assumes app/main.py will exist and contain 'app = FastAPI()'
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
