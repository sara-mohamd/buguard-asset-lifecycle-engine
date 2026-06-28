# Asset Management System

The deterministic system of record (SoR) within the DarkAtlas Attack Surface Monitoring platform, responsible for maintaining a continuous, high-fidelity inventory of public-facing digital assets.

## Language

**Asset**:
A tracked digital entity belonging to the organization's public-facing footprint.
*Avoid*: Target, resource, host

**Domain**:
The root-level DNS structure (apex domain) representing the organization's administrative ownership.
*Avoid*: Apex, root domain

**Subdomain**:
A hostname positioned as a child node within the DNS hierarchy under an apex domain.
*Avoid*: Host, FQDN

**IP Address**:
A logical network layer interface (IPv4 or IPv6) hosting organizational services.
*Avoid*: Node, server

**Service**:
An exposed application-layer network socket defined by a port number, transport protocol, and service banner.
*Avoid*: Port, socket, daemon

**Certificate**:
A cryptographic public-key certificate (X.509) proving identity and securing communication channels.
*Avoid*: TLS cert, SSL cert

**Technology**:
A software application, server, programming framework, middleware, or library running on a subdomain or service.
*Avoid*: App, stack, dependency

**Relationships Graph**:
A directed graph representation linking assets together (e.g., Subdomain → Domain, Certificate → Domain).
*Avoid*: Network map, topology

**Idempotent Ingestion**:
The deterministic process of inserting or updating assets without creating duplicates, using the combination of type and value as a unique composite key. Metadata is deep-merged using a "Latest Wins" strategy, and the origins are appended to a `seen_by` array within the metadata to track all sources that have discovered the asset.
*Avoid*: Import, sync

**State**:
The lifecycle position of an asset: Active (currently discoverable), Stale (not recently seen), or Archived (permanently retired).
*Avoid*: Status, health

**Tenant**:
A distinct organizational boundary that owns a segregated subset of assets. All assets and relationships are strictly isolated at the row level by their Tenant ID.
*Avoid*: Client, Organization, Workspace

**Role**:
The authorization level attached to an API Key defining its allowed actions within a Tenant. (e.g., `admin`, `scanner`, `viewer`).
*Avoid*: Permissions, Access Level

**Re-sighted (Tag)**:
A system tag applied to an `Archived` asset when it is discovered again during an import. The asset remains `Archived` and its `last_seen` timestamp is updated, allowing admins to filter and review these anomalies without accidentally re-activating permanently retired assets.

**parent-stale (Tag)**:
A system tag appended to dependent child assets (e.g., Services running on an IP) when their parent asset transitions to the `Stale` or `Archived` state. We use tagging instead of cascading the state downwards to preserve the child's independent lifecycle while providing a breadcrumb trail for verification.
