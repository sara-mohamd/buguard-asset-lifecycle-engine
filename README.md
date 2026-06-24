# Buguard Asset Management System

## Project Overview
A high-performance, asynchronous FastAPI service backed by PostgreSQL designed for the tracking and lifecycle management of cybersecurity network assets. The system architecture models the infrastructure as a highly-queryable directed graph, enabling complex dependency tracking and vulnerability mapping.

## Current Implementation Progress
* **Infrastructure & Database Scaffold**: Asynchronous SQLAlchemy 2.0 configuration with Alembic migrations and robust connection pooling.
* **Configuration Management**: Type-safe, environment-based setup utilizing Pydantic `BaseSettings`.
* **Asset Core Models**: Implementation of the polymorphic `Asset` model and strict Pydantic validation schemas leveraging discriminated unions.
* **Idempotent Bulk Ingestion Engine**: A high-speed, fault-tolerant batch processing endpoint (`POST /import`) capable of handling partial failures without rejecting entire payloads.

## Engineering & Architectural Decisions

### Data Modeling: Polymorphism over Discrete Tables
We implemented a single polymorphic `assets` table combined with a single self-referencing `asset_relationships` junction table (Adjacency List).
* **The "Why"**: Rather than maintaining dozens of discrete junction tables for every possible combination of asset types (e.g., Domain-to-IP, IP-to-Service), an adjacency list structure allows for deep, recursive graph traversals. This heavily optimizes single-query neighbor fetching and entirely prevents the need for complex, expensive `UNION` operations when mapping attack surfaces.

### High-Performance Ingestion: SQLAlchemy Core Batching
The batch ingestion engine (`bulk_import_assets`) entirely avoids SQLAlchemy ORM state tracking inside its loop, relying instead on lightweight column selection and SQLAlchemy Core batch execution.
* **The "Why"**: Instantiating thousands of tracked ORM objects causes severe memory bloat and results in the N+1 problem (where SQLAlchemy emits individual row-by-row `UPDATE` statements). By mapping primitive columns into a lookup dictionary and executing bulk `insert(Asset)` and `update(Asset)` mappings, we execute high-performance batched database roundtrips, eliminating memory exhaustion and connection pool choking.
* 📊 **[View Architecture Deep-Dive & Flowchart](docs/architecture/bulk_import_optimization.html)**

### Application-Layer Deep Merge: Python over PL/pgSQL
The recursive JSONB metadata deep-merging and tag set-unions are executed purely in Python memory prior to database insertion, rather than relying on native PL/pgSQL.
* **The "Why"**: Handling these operations at the application layer provides granular programmatic control and trivial unit testing. Crucially, it ensures isolated, record-level fault tolerance—if a specific payload merge fails, it is trapped by the API's partial failure mechanism, whereas database-level triggers could result in opaque transaction rollbacks affecting the entire batch.

## Authentication
Write operations and ingestion endpoints are secured via **Stateless Machine-to-Machine (M2M) Static API Key verification**. Scanners and upstream automation authenticate by passing a static token via the custom `X-API-Key` header, allowing for zero-latency verification without the overhead of session management.
