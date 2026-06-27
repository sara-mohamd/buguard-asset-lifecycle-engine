<div align="center">

# 🛡️ Buguard Asset Lifecycle Engine

**A high-performance Attack Surface Monitoring (ASM) asset management system**

Built with Python · FastAPI · PostgreSQL · SQLAlchemy 2.0 (Async) · Docker

[![Track](https://img.shields.io/badge/Track-Backend%20Engineering-blue?style=for-the-badge)]()
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi&logoColor=white)]()
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)]()

</div>

---

## Table of Contents

- [Project Overview](#project-overview)
- [Implemented Features](#implemented-features)
- [Tech Stack & Architecture](#tech-stack--architecture)
- [The Asset Domain Model](#the-asset-domain-model)
- [API Reference](#api-reference)
- [Bulk Import Optimization](#bulk-import-optimization--architecture-deep-dive)
- [Setup & Run Instructions](#setup--run-instructions)
- [Environment Variables](#environment-variables)
- [Running Tests](#running-tests)
- [Design Decisions & Rationale](#design-decisions--rationale)
- [Assumptions](#assumptions)
- [Remaining Work & Future Scope](#remaining-work--future-scope)

---

## Project Overview

This system is the **Asset Management module** at the heart of [Buguard's](https://buguard.com/) **DarkAtlas** Attack Surface Monitoring platform. It serves as the authoritative **system of record (SoR)** that ingests discovered assets from automated scanners, removes duplicates, tracks each asset's lifecycle, models relationships as a directed graph, and exposes everything through a queryable REST API.

The module handles six core entity types — **domains, subdomains, IP addresses, services, certificates, and technologies** — and provides:

- **Idempotent bulk ingestion** with fault-tolerant partial-failure handling
- **Deduplication** via composite key matching (`type` + `value`)
- **Lifecycle state management** (Active → Stale → Archived, with automatic re-activation)
- **Directed relationship graph** modeling asset dependencies
- **Advanced filtering, sorting, and pagination** for inventory browsing
- **API key authentication** on all write operations
- **Strict input validation** with structured, field-level error responses

> **Note:** This project focuses on modeling, storing, and working with asset data. It does not include live scanners or integration with the DarkAtlas platform.

---

## Implemented Features

The following capabilities have been fully built, tested, and merged — each mapped to a closed GitHub issue:

| Feature | Issue | Status |
|---|---|---|
| **Infrastructure & Database Scaffold** — Docker Compose, async SQLAlchemy 2.0, Alembic migrations, health check | [#2](https://github.com/sara-mohamd/buguard-asset-lifecycle-engine/issues/2) | ✅ Done |
| **Asset Data Model & Basic CRUD** — Polymorphic `assets` table, discriminated-union Pydantic schemas, `POST` / `GET` endpoints | [#3](https://github.com/sara-mohamd/buguard-asset-lifecycle-engine/issues/3) | ✅ Done |
| **Idempotent Bulk Ingestion & State Engine** — `POST /import` with dedup, deep-merge metadata, tag union, stale→active re-activation, partial failure isolation | [#4](https://github.com/sara-mohamd/buguard-asset-lifecycle-engine/issues/4) | ✅ Done |
| **Asset Listing, Filtering & Pagination** — `GET /assets` with limit/offset, filter by type, status, tag, value substring | [#5](https://github.com/sara-mohamd/buguard-asset-lifecycle-engine/issues/5) | ✅ Done |
| **Relationships Directed Graph** — `asset_relationships` table, create relationship endpoint, first-degree neighbor traversal | [#6](https://github.com/sara-mohamd/buguard-asset-lifecycle-engine/issues/6) | ✅ Done |
| **API Key Authentication** — Stateless M2M `X-API-Key` verification on all write endpoints | [#7](https://github.com/sara-mohamd/buguard-asset-lifecycle-engine/issues/7) | ✅ Done |

---

## Tech Stack & Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Client / Scanner                  │
│               (X-API-Key Authentication)             │
└────────────────────────┬────────────────────────────┘
                         │  HTTP/JSON
                         ▼
┌─────────────────────────────────────────────────────┐
│              FastAPI Application (Async)              │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │  Endpoints   │  │  Pydantic    │  │  API Key   │  │
│  │  (v1 Router) │  │  Validation  │  │  Auth      │  │
│  └──────┬──────┘  └──────┬───────┘  └────────────┘  │
│         │                │                           │
│  ┌──────▼────────────────▼──────────────────────┐   │
│  │         Service Layer (Business Logic)         │   │
│  │  • Bulk import engine (Fetch-Map-Segregate)   │   │
│  │  • Deep merge & tag union                     │   │
│  │  • Lifecycle state machine                    │   │
│  │  • Graph neighbor resolution                  │   │
│  └──────────────────────┬───────────────────────┘   │
│                         │  SQLAlchemy 2.0 (Async)    │
└─────────────────────────┼───────────────────────────┘
                          ▼
┌─────────────────────────────────────────────────────┐
│         PostgreSQL 15 (Docker Container)             │
│  ┌───────────┐    ┌──────────────────────┐          │
│  │  assets   │    │  asset_relationships │          │
│  │  (JSONB,  │◄──►│  (directed edges,    │          │
│  │   ARRAY)  │    │   CASCADE deletes)   │          │
│  └───────────┘    └──────────────────────┘          │
└─────────────────────────────────────────────────────┘
```

| Layer | Technology | Rationale |
|---|---|---|
| **Framework** | FastAPI | High-performance async, auto-generated OpenAPI/Swagger, built-in Pydantic validation |
| **ORM** | SQLAlchemy 2.0 (async) | Granular control over PostgreSQL-specific features (JSONB, ARRAY); rejected SQLModel for complex query needs |
| **Database** | PostgreSQL 15 | Native `JSONB` for deep metadata merging, `ARRAY` for tag collections, robust indexing |
| **Migrations** | Alembic | Version-controlled schema evolution |
| **Validation** | Pydantic v2 + Discriminated Unions | Type-safe, per-asset-type validation with automatic routing |
| **Auth** | Stateless API Key (`X-API-Key` header) | Zero-latency M2M verification for scanner ingestion |
| **Config** | Pydantic `BaseSettings` | Type-safe, environment-based configuration with `.env` support |
| **Testing** | pytest + httpx (AsyncClient) | Tests at the HTTP API boundary against real PostgreSQL — no mocking |
| **Containerization** | Docker + Docker Compose | One-command orchestration of API + PostgreSQL |

---

## The Asset Domain Model

### Entity Types

The system tracks six asset entity types representing an organization's public-facing digital footprint:

| Type | Example Value | Description |
|---|---|---|
| `domain` | `example.com` | Apex DNS domains (FQDN-validated) |
| `subdomain` | `api.example.com` | Child hostnames under a domain (FQDN-validated) |
| `ip_address` | `203.0.113.10` | Network interfaces (IPv4 & IPv6 validated) |
| `service` | `443/tcp` | Exposed network sockets (port `1-65535` + `tcp`/`udp`) |
| `certificate` | `CN=api.example.com` | X.509 TLS certificates (CN FQDN-validated, ISO-8601 expiry) |
| `technology` | `nginx/1.21` | Software stacks deployed on subdomains/services |

### Asset Schema

Every asset captures the following fields:

| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Unique, stable identifier (auto-generated) |
| `type` | `enum` | One of the six entity types above |
| `value` | `string` | Canonical value for the asset |
| `status` | `enum` | `active` · `stale` · `archived` |
| `first_seen` | `datetime` | Set once on creation, never modified |
| `last_seen` | `datetime` | Updated on every re-sighting |
| `source` | `string` | Origin: `import`, `scan`, `manual` |
| `tags` | `list<string>` | Free-form labels for filtering and grouping |
| `metadata` | `JSONB` | Type-specific fields (cert issuer/expiry, service banner, tech version, etc.) |

**Composite Uniqueness:** An asset is uniquely identified by `(type, value)`, enforced at the database level via a `UNIQUE` constraint.

### Lifecycle State Machine

```mermaid
stateDiagram-v2
    [*] --> Active : Asset first ingested
    Active --> Stale : Admin action or discovery absence
    Stale --> Active : Re-sighted in import batch
    Active --> Archived : Admin action
    Stale --> Archived : Admin action
    Archived --> [*] : Historical record preserved
```

- **Active** → Verified and currently discoverable
- **Stale** → Previously active, not detected in recent cycles
- **Archived** → Permanently retired, preserved for historical audit

### Relationship Graph

The asset landscape is modeled as a **directed graph** `G = (V, E)` where assets are nodes and relationships are directed edges:

```mermaid
graph LR
    D[Domain - example.com] --> S1[Subdomain - api.example.com]
    D --> S2[Subdomain - mail.example.com]
    S1 --> IP1[IP Address - 203.0.113.10]
    IP1 --> SVC[Service - 443 tcp]
    CERT[Certificate - CN api.example.com] --> S1
    TECH[Technology - nginx 1.21] --> SVC
```

**Supported edge patterns:**

| Edge | Direction | Example |
|---|---|---|
| Subdomain → Domain | Hierarchical DNS | `api.example.com` → `example.com` |
| Service → IP Address | Socket hosting | `443/tcp` → `203.0.113.10` |
| IP Address ↔ Subdomain | DNS resolution | Bidirectional resolution mapping |
| Certificate → Domain/Subdomain | TLS coverage | `CN=api.example.com` → `api.example.com` |
| Technology → Subdomain/Service | App deployment | `nginx/1.21` → `443/tcp` |

---

## API Reference

> **Interactive Docs:** The root route (`/`) redirects to Swagger UI. Also available at `/docs` (Swagger) and `/redoc` (ReDoc).

### Assets

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/api/v1/assets/` | — | List assets with pagination & filtering |
| `POST` | `/api/v1/assets/` | 🔑 | Create a single asset |
| `GET` | `/api/v1/assets/{id}` | — | Retrieve asset by UUID |
| `GET` | `/api/v1/assets/{id}/relationships` | — | Asset + first-degree graph neighbors |
| `POST` | `/api/v1/assets/import` | 🔑 | Idempotent bulk ingestion |

### Relationships

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/v1/relationships/` | 🔑 | Create a directed edge between two assets |

### Health

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Database connectivity check |

### Query Parameters (`GET /api/v1/assets/`)

| Param | Type | Description |
|---|---|---|
| `limit` | `int` (1–1000) | Items per page (default: 100) |
| `offset` | `int` (≥ 0) | Pagination offset |
| `type` | `string` | Exact match on asset type |
| `status` | `string` | Exact match on status |
| `tag` | `string` | Array membership match |
| `value` | `string` | Case-insensitive substring match |

### Authentication

All write operations (`POST` on assets, import, and relationships) require a valid `X-API-Key` header:

```bash
curl -X POST http://localhost:8000/api/v1/assets/ \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_secure_api_key_here" \
  -d '{"type": "domain", "value": "example.com"}'
```

Requests without a valid key receive `401 Unauthorized` with a structured error response.

### Import Response Format

The bulk import endpoint returns a detailed execution report:

```json
{
  "total_analyzed": 100,
  "successful_creates": 60,
  "successful_updates": 38,
  "rejected_records": [
    {
      "index": 42,
      "record": { "type": "ip_address", "value": "not-valid" },
      "errors": [
        { "type": "value_error", "loc": ["value"], "msg": "value is not a valid IPv4 or IPv6 address" }
      ]
    }
  ]
}
```

---

## Bulk Import Optimization — Architecture Deep-Dive

The ingestion engine uses a **Fetch-Map-Segregate-Execute** pipeline that bypasses SQLAlchemy ORM state tracking entirely, using lightweight **SQLAlchemy Core** operations for maximum throughput.

### The Problem

Traditional ORM-based ingestion for batches of 1,000+ assets suffers from:
- **Memory Bloat:** Loading thousands of ORM state-tracking objects into RAM
- **N+1 Update Problem:** The DB session emits an individual `UPDATE` for every modified row on commit

### The Solution

```mermaid
graph TD
    A[Incoming Payload - 1000 Assets] --> B{1. Core Fetch}
    B -->|select id, type, value| C[(PostgreSQL DB)]
    C -->|Returns 400 Existing Records| D[2. Dictionary Mapping]
    D --> E[In-Memory Loop]
    E --> F{Exists in DB?}
    F -->|Yes - 400 records| G[3a. Update Path]
    G -->|Deep Merge JSON + Union Tags + Stale to Active| I[update_data List]
    F -->|No - 600 records| H[3b. Insert Path]
    H -->|Generate UUIDs + Set first_seen| J[insert_data List]
    I --> K[4. Batch Execute]
    J --> K
    K -->|execute insert| C
    K -->|execute update| C
```

### Execution Stages

| Stage | Operation | Details |
|---|---|---|
| **1. Lightweight Fetch** | `select(Asset.id, Asset.type, Asset.value...)` | Bulk fetch using `OR` clause of composite keys — primitive columns only, no ORM instantiation |
| **2. Dictionary Mapping** | `{(type, value): record}` | O(1) lookup eliminates per-record DB queries |
| **3. In-Memory Merge** | Deep merge + tag union | Recursive `deep_merge_dicts()` preserves nested JSON; set union prevents duplicate tags; stale assets automatically transition to active |
| **4. Batch Execute** | `insert(Asset)` / `update(Asset)` | Two DB round-trips total — O(1) write operations regardless of batch size |

**Result:** The writing phase achieves constant-time database queries regardless of batch size, eliminating memory exhaustion and connection pool choking.

### Why Application-Layer Merging (Not PL/pgSQL)

The recursive JSONB metadata deep-merge and tag set-unions execute purely in Python, not via database triggers:

- **Granular control:** Programmatic merge logic with trivial unit testing
- **Record-level fault tolerance:** If a merge fails, it's trapped by the partial-failure mechanism — database triggers would cause opaque transaction rollbacks affecting the entire batch

---

## Setup & Run Instructions

### Option 1: Docker Compose (Recommended)

Starts the full stack (API + PostgreSQL) with a single command:

```bash
# 1. Clone the repository
git clone https://github.com/sara-mohamd/buguard-asset-lifecycle-engine.git
cd buguard-asset-lifecycle-engine

# 2. Configure environment
cp .env.example .env
# Edit .env and set a secure API_KEY

# 3. Start everything
docker compose up --build
```

The API will be available at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

> **Note:** Alembic migrations run automatically when the `api` container starts. The `db` container includes a health check — the API waits until PostgreSQL is ready.

### Option 2: Local Development

For development with hot-reload:

```bash
# 1. Clone and enter the repository
git clone https://github.com/sara-mohamd/buguard-asset-lifecycle-engine.git
cd buguard-asset-lifecycle-engine

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — ensure DATABASE_URL points to your local PostgreSQL

# 5. Start PostgreSQL via Docker (database only)
docker compose up -d db

# 6. Run database migrations
alembic upgrade head

# 7. Start the development server with hot-reload
PYTHONPATH=. fastapi dev src/main.py
```

---

## Environment Variables

Managed via `.env` file (see `.env.example`):

| Variable | Required | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL async connection string | `postgresql+asyncpg://user:password@localhost:5432/asset_db` |
| `API_KEY` | ✅ | Static token for write-operation authentication | `your_secure_api_key_here` |
| `ENVIRONMENT` | — | Runtime environment | `development` / `production` |
| `LOG_LEVEL` | — | Logging verbosity | `INFO` / `DEBUG` |

> **⚠️ Security:** Never commit real API keys. The `.env` file is gitignored; only `.env.example` is tracked.

---

## Running Tests

Tests run at the **HTTP API boundary** against a real PostgreSQL database — no mocking. This ensures implementation details (like SQLAlchemy logic) can change without breaking tests.

```bash
# Ensure PostgreSQL is running and .env is configured
docker compose up -d db

# Run the full test suite
PYTHONPATH=. pytest -v
```

### Test Coverage

| Test File | Covers |
|---|---|
| `test_assets.py` | CRUD operations, duplicate detection (`409`), validation errors (`422`), pagination, filtering by type/status/tag/value |
| `test_import.py` | Idempotent imports, tag union, metadata deep-merge, stale→active re-activation, partial failure (valid + malformed records in same batch) |
| `test_relationships.py` | Graph edge creation, invalid asset references (`404`), bidirectional neighbor traversal (outbound + inbound) |
| `test_auth.py` | Missing API key (`401`), invalid key (`401`), valid key across all write endpoints |

---

## Design Decisions & Rationale

### 1. Single Polymorphic Table (over Discrete Tables)

A single `assets` table with a `type` discriminator, combined with a self-referencing `asset_relationships` junction table (adjacency list pattern).

**Why:** Maintaining dozens of discrete junction tables for every combination of asset types (Domain-to-IP, IP-to-Service, etc.) would require complex, expensive `UNION` operations. The adjacency list enables deep, recursive graph traversals with single-query neighbor fetching.

### 2. Discriminated Union Validation (Pydantic)

Instead of a single flat schema, each asset type has its own Pydantic model (e.g., `DomainAsset`, `ServiceAsset`, `IpAddressAsset`), composed via a discriminated union on the `type` field.

**Why:** This enables per-type validation rules — FQDN validation for domains/subdomains, IPv4/IPv6 parsing for IPs, port range + protocol enforcement for services, CN + ISO-8601 expiry for certificates — while keeping a single `AssetCreate` type for the API layer.

### 3. SQLAlchemy Core for Bulk Operations (over ORM)

The bulk import engine bypasses the ORM entirely, using `select()`, `insert()`, and `update()` from SQLAlchemy Core.

**Why:** ORM instantiation of 1,000+ objects causes memory bloat and the N+1 update problem. Core operations achieve O(1) database roundtrips for the write phase. See the [Bulk Import Optimization](#bulk-import-optimization--architecture-deep-dive) section for the full architecture.

### 4. Application-Layer Merge (over PL/pgSQL Triggers)

Deep JSON merging and tag unions execute in Python memory before database insertion.

**Why:** Granular programmatic control, trivial unit testing, and — critically — record-level fault isolation. Database triggers would cause opaque transaction rollbacks affecting entire batches.

### 5. Stateless API Key Authentication (over JWT)

A static `API_KEY` verified via the `X-API-Key` header, validated against an environment variable.

**Why:** The primary client is an automated scanner (machine-to-machine). A static key provides zero-latency verification without session management overhead. JWT issuance flows are out of scope for M2M ingestion.

### 6. HTTP-Boundary Testing (over Unit Mocking)

All tests use `httpx.AsyncClient` against the real FastAPI app with a real PostgreSQL database.

**Why:** Testing at the highest seam means implementation details (SQLAlchemy queries, service layer refactors) can change freely without breaking tests. The application is treated as a black box.

---

## Assumptions

1. **Authentication Model:** The API uses a single static `API_KEY` (machine-to-machine) rather than a multi-user JWT system, assuming the primary client is an automated scanner.

2. **Data Merge Strategy:** When conflicting data arrives for an existing asset, the **newer metadata takes precedence** via a key-value override protocol. For nested structures, a recursive deep merge preserves non-overlapping keys at all levels.

3. **Soft Deletion / Lifecycle:** Assets are tracked via `status` (active, stale, archived) and are never permanently deleted, assuming historical visibility is critical for security auditing.

4. **Composite Identity:** An asset's unique identity is its `(type, value)` pair, not any external ID from the incoming payload.

5. **Tag Normalization:** Tags are lowercased, stripped of whitespace, and deduplicated on ingestion to ensure consistent filtering.

6. **Single-Batch Dedup:** If the same asset appears multiple times within a single import batch, only the last occurrence is processed.

7. **Read Access:** Read operations (`GET`) are unauthenticated, assuming the API sits behind a network boundary. Only write operations require the API key.

---

## Remaining Work & Future Scope

The following items from the [Functional Specification](docs/Functional_Specification_and_System_Scope.md) are **not yet implemented** and represent planned next steps:

### Asset Update & Delete Endpoints

- `PUT /api/v1/assets/{id}` — Update an existing asset's fields
- `DELETE /api/v1/assets/{id}` — Soft-delete (archive) or hard-delete an asset
- Cascading relationship cleanup on asset deletion (remove all inbound/outbound edges to prevent dangling references)

### Archived Asset Handling on Re-Import

Per §2.1.2.6 of the functional spec: when a scan re-sights an **archived** asset, the system should **not** silently re-activate it. Instead, it should either require admin approval or raise a notification. Currently, the import engine does not special-case archived assets during re-sighting.

### Incoming Data Scenarios Not Yet Handled

The functional spec defines several ingestion scenarios that require additional implementation:

| Scenario | Spec Reference | Current State |
|---|---|---|
| **Archived asset re-sighting** — prevent silent state updates on archived records | §2.1.2 (Rule 6) | ⬜ Not implemented — archived assets are treated like stale assets |
| **State propagation on graph** — when a parent IP transitions to stale, optionally tag dependent child services for verification | §2.2.2 (Structural Integrity) | ⬜ Not implemented |
| **Sorting parameter** — allow clients to specify sort field and direction | §2 (Listing) | ⬜ Only `first_seen DESC` is used; no client-configurable sorting |
| **Conflicting source handling** — merge strategy documentation when the same asset arrives from different sources simultaneously | §2.3.2 | ⬜ Source field is stored but not factored into merge precedence |

### Input Validation Gaps

Per §3.2 of the functional spec, the following validation strictness items are partially addressed:

| Validation | Status |
|---|---|
| FQDN format for domains/subdomains (RFC 1035) | ✅ Implemented via regex |
| IPv4/IPv6 validation (RFC 791 / RFC 2460) | ✅ Implemented via Pydantic `IPvAnyAddress` |
| Service port range (1–65535) + TCP/UDP protocol | ✅ Implemented via model validator |
| Certificate CN FQDN + ISO-8601 expiry dates | ✅ Implemented via model validator |
| Service banner sanitization (clean text) | ⬜ Not yet enforced |
| Certificate SAN validation | ⬜ Not yet enforced |

### Operational & Bonus Features

- **Multi-tenant isolation** — organization-scoped asset segregation (bonus)
- **Role-based access control (RBAC)** — beyond single API key (bonus)
- **Asset relationship graph visualization** — visual UI for the graph (bonus)
- **CI pipeline** — GitHub Actions running tests on push (bonus)
- **Caching & rate limiting** — performance guardrails (bonus)
- **LangChain integration** — one Track B AI feature as a bonus (bonus)

---

<div align="center">

**Built for the Buguard Internship Acceptance Task — Backend Engineering Track**

</div>
