# 1. Configuration Management Strategy

Date: 2026-06-23

## Status

Accepted

## Context

As the Asset Management System grows to ingest Domains and Assets, configuration will become increasingly complex (e.g., database connection strings, logging levels, environment profiles). Historically, using `os.getenv` directly in modules (like `database.py`) leads to shallow modules, hidden dependencies, and makes the system difficult to test under different configurations since it tightly couples the code to the OS environment.

We need a structured way to load, validate, and access configuration across the application.

## Decision

We will use `pydantic-settings` to implement a centralized Settings Management Adapter. 
- **Validation**: Settings will be strictly typed and validated on startup.
- **Access**: The settings object will be instantiated and accessed via FastAPI Dependency Injection (`Depends(get_settings)` with `@lru_cache`).
- **Source of Truth**: Local development will load overrides from a `.env` file, while production will rely on OS environment variables.
- **Baseline Scope**: We establish `DATABASE_URL`, `ENVIRONMENT` (dev/prod), and `LOG_LEVEL` as the initial baseline settings.

## Consequences

- **Positive**: High test locality; tests can easily inject mock settings using FastAPI's `app.dependency_overrides`.
- **Positive**: Fail-fast behavior on startup if critical environment variables are missing or incorrectly formatted.
- **Negative**: Adds a minor boilerplate overhead for injecting settings into routers and dependencies.
