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
The deterministic process of inserting or updating assets without creating duplicates, using the combination of type and value as a unique composite key.
*Avoid*: Import, sync

**State**:
The lifecycle position of an asset: Active (currently discoverable), Stale (not recently seen), or Archived (permanently retired).
*Avoid*: Status, health
