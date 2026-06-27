# Functional Specification and System Scope: Attack Surface Monitoring Asset Management System

## 1. System Core Objective & Functional Domain

The Asset Management System serves as the authoritative, deterministic system of record (SoR) within an Attack Surface Monitoring (ASM) platform. Its primary objective is to maintain a continuous, high-fidelity inventory of an organization's public-facing digital footprint. By aggregating, tracking, and contextualizing internet-facing assets, the system provides security operations teams with visibility into their external boundary and exposure vulnerabilities.

The system's operational scope is bounded by the ingestion and management of six specific digital asset entities:
1. **Domains**: The root-level Domain Name System (DNS) structures (apex domains) representing the organization's administrative ownership.
2. **Subdomains**: Hostnames positioned as child nodes within the DNS hierarchy under an apex domain.
3. **IP Addresses**: Logical network layer interfaces (supporting both IPv4 and IPv6 protocols) hosting organizational services.
4. **Services**: Exposed application-layer network sockets defined by a port number, transport protocol (TCP or UDP), and service banner.
5. **Certificates**: Cryptographic public-key certificates (X.509) proving identity and securing communication channels for domains or subdomains.
6. **Technologies**: The software applications, application servers, programming frameworks, middleware, and libraries running on subdomains or network services.

The functional domain of this module is dedicated to the deterministic processing, state preservation, structural dependency mapping, and queryable retrieval of these entities. It provides the foundation for vulnerability mapping, exposure identification, and asset tracking, without implementing scanning routines or live discovery processes.

---

## 2. Mandatory Core Behaviors & Scope (The "Must-Haves")

This section defines the precise behavioral rules, state transitions, graph relationships, and data ingestion strategies that the backend application must satisfy.

### 2.1 Asset Lifecycle Engine

The asset lifecycle is governed by a state machine that tracks the status of each asset over time. 

#### 2.1.1 State Space
Let the set of permissible asset states be defined as $S = \{ \text{Active}, \text{Stale}, \text{Archived} \}$.
- **Active**: The asset is verified as currently discoverable, reachable, or actively associated with the organization's infrastructure.
- **Stale**: The asset was previously active but has not been detected in recent discovery cycles, or it has been explicitly flagged as potentially decommissioned.
- **Archived**: The asset has been permanently retired or marked as out-of-scope for active monitoring. Archived assets are preserved for historical auditability and forensic compliance but are excluded from active operational views.

#### 2.1.2 State Transitions
The system must enforce the following state transition rules:
1. **Asset Initialization**:
   Upon first ingestion of an asset, the system instantiates the record with the state set to **Active**. The system initializes the `first_seen` and `last_seen` timestamps to the ingestion transaction time $T_{\text{ingest}}$.
2. **Asset Re-sighting**:
   If an asset in the **Active** state is observed in subsequent ingestion batches, the system updates its `last_seen` timestamp to the current transaction time $T_{\text{sight}}$, while preserving the original `first_seen` timestamp.
3. **Staleness Transition**:
   An active asset transitions to the **Stale** state through two mechanisms:
   - *Deterministic Discovery Absence*: A discovery process indicates the asset is no longer reachable or registered.
   - *Administrative Action*: An authorized administrative request triggers the transition to represent decommissioned infrastructure.
4. **Re-activation (Sighting of Stale Asset)**:
   If an asset currently in the **Stale** state is re-sighted in a subsequent ingestion batch, the system must automatically transition the asset state back to **Active**. The `last_seen` timestamp is updated to the current ingestion timestamp $T_{\text{sight}}$, while the original `first_seen` value is preserved to maintain historical continuity.
5. **Archiving Transition**:
   An asset can transition from **Active** or **Stale** to **Archived** via explicit administrative action. 
6. **Archived Lifecycle Constraints**:
   The **Archived** state is designed to represent historical records. The system must restrict standard queries from retrieving archived records by default. If a scan or import re-sights an archived asset, the system must prevent silent state updates and either require administrative approval for re-activation or raise an event notification, depending on configuration, to avoid corrupting historical scopes.

---

### 2.2 The Asset Relationship Network

The system must model the asset landscape as a directed graph $G = (V, E)$, where $V$ represents the set of asset nodes and $E$ represents the set of directed edges representing dependencies or associations.

#### 2.2.1 Conceptual Edge Mappings
The relationship graph must support the following edge patterns:
1. **Subdomain-to-Domain Relationship ($e \in E : \text{subdomain} \rightarrow \text{domain}$)**:
   Establishes hierarchical DNS structures. Every subdomain must reference its parent domain.
2. **Service-to-IP Relationship ($e \in E : \text{service} \rightarrow \text{ip\_address}$)**:
   Links logical network sockets to their physical or virtual hosting interface.
3. **Resolution Relationship ($e \in E : \text{ip\_address} \leftrightarrow \text{subdomain}$)**:
   Represents DNS resolution. This is a bidirectional mapping where a subdomain resolves to an IP address, and an IP address maps to associated hostnames.
4. **Cryptographic Coverage ($e \in E : \text{certificate} \rightarrow \text{domain/subdomain}$)**:
   Links cryptographic TLS certificates to the specific domain or subdomain names they secure.
5. **Application Deployment ($e \in E : \text{technology} \rightarrow \text{subdomain/service}$)**:
   Associates identified software stacks (operating systems, web servers, database engines, libraries) with the subdomain (web level) or service (socket level) where they are deployed.

#### 2.2.2 Structural Integrity and Graph Constraints
- **High Fan-In/Fan-Out Support**: The system must handle complex topologies, such as a single IP address serving hundreds of subdomains (virtual hosting), or a single certificate covering multiple subdomains.
- **Referential Integrity**: Edges must only connect valid, existing nodes. The system must prevent dangling edges. If an asset is deleted, all incoming and outgoing relationship edges associated with that node must be removed from the graph.
- **State Propagation**: If a parent asset (e.g., an IP address) transitions to a `Stale` state, the relationship network should optionally support state propagation rules to tag dependent child assets (e.g., services hosted on that IP) for verification, while preserving the structural relationship topology.

---

### 2.3 Idempotent Data Ingestion & Merging Strategy

The ingestion engine must be fully idempotent, ensuring that duplicate processing of identical or overlapping data streams does not corrupt the system of record.

#### 2.3.1 Uniqueness Identification
An asset is uniquely identified by a composite key comprising its `type` and its `canonical value` (e.g., `type = 'subdomain', value = 'api.example.com'`). The system must use this identity to determine whether an incoming record is new or already exists in the registry.

#### 2.3.2 Ingestion Upsert Behavior
For each record in an incoming batch:
1. **Identity Check**:
   Evaluate whether the `type` and `value` match an existing asset.
2. **Creation Path**:
   If no match is found, instantiate a new asset record. Initialize `first_seen` and `last_seen` to the current transaction time. Populate metadata and tags from the incoming record.
3. **Deduplication & Update Path (Existing Assets)**:
   If a match is found:
   - **Timestamp Modification**: Update the `last_seen` timestamp of the existing asset to the current ingestion time.
   - **State Restoration**: If the existing asset has a state of `Stale`, transition the state back to `Active`.
   - **Tag Integration**: Merge incoming tags with existing tags using a set union operation ($\text{Tags}_{\text{final}} = \text{Tags}_{\text{existing}} \cup \text{Tags}_{\text{incoming}}$) to ensure that the tags collection contains only unique values and that historical tags are never deleted during ingestion.
   - **Metadata Synthesis (Merging Strategy)**: Merge the incoming JSON metadata object with the existing metadata object. The merging strategy must follow a deterministic key-value override protocol:
     - For non-overlapping keys: The new keys are added to the metadata object.
     - For overlapping keys: The incoming value overrides the existing value, ensuring that the latest scan metadata is preserved.
     - For nested metadata (e.g., certificate details or service banners): The system must perform a deep merge to preserve nested keys unless they are explicitly superseded by newer structured structures.

---

### 2.4 Fault Tolerance & Ingestion Resilience

Ingesting real-world asset data requires high tolerance for malformed, corrupted, or incomplete payloads.

#### 2.4.1 Execution Isolation
- **Non-blocking Fault Handling**: When processing a bulk dataset, the system must isolate processing failures to the individual record level.
- **Partial Commit Strategy**: If a record fails validation (e.g., invalid format, missing critical properties), the system must skip the execution of that specific record, log the validation failure, and proceed with processing the remaining records in the batch.
- **Transactional Atomicity at Record Level**: The ingestion engine must ensure that a failure in one record does not rollback or disrupt the commits of valid records within the same batch.
- **Failure Auditing**: The ingestion response must provide a detailed execution report specifying:
  - Total records analyzed.
  - Count of successful creations.
  - Count of successful updates.
  - Count of rejected records, accompanied by specific semantic error descriptors for each rejected entry.

---

## 3. Operational Guardrails & Security Posture

This section defines the security constraints, validation rigor, and verification mechanisms required to protect system integrity.

### 3.1 Write Access Controls

- **Mandatory Authentication**: All state-modifying operations (write, update, delete, bulk import, relationship association) must be strictly authenticated.
- **Cryptographic Verification**: Write requests must present a cryptographically verified token (e.g., JSON Web Token with secure signature verification) or a highly secure, randomly generated API Key transmitted via a secure header.
- **Stateless Verification**: The backend must validate the presence and integrity of these credentials before executing any business logic. Unauthenticated or malformed requests must immediately terminate with a standardized error code, preventing any backend execution pathways from touching the database layer.

### 3.2 Input Verification, Validation Strictness, and Predictable Errors

- **Format Verification**: The system must enforce strict parsing of all input values against structural standards:
  - *Domains & Subdomains*: Must conform to FQDN standards (RFC 1035).
  - *IP Addresses*: Must be valid IPv4 or IPv6 representations (RFC 791 and RFC 2460).
  - *Services*: Ports must be integers in the range $[1, 65535]$, protocols must be restricted to standard layers (e.g., TCP, UDP), and banners must be clean text.
  - *Certificates*: Subject alternative names (SANs) and common names (CN) must match FQDN formats, and validity timestamps (issue and expiry dates) must follow ISO-8601 formatting.
- **State & Enum Validation**: Inputs for fields such as `type` and `status` must match the defined enums strictly. Invalid strings must be rejected.
- **Structured Error Responses**: When validation fails, the backend must return a consistent, structured payload containing:
  - An application-specific error code.
  - A field-level mapping indicating exactly which parameter failed validation and the constraint violated.
  - System-level details, internal execution pathways, and raw database errors must be suppressed to prevent information leakage to potential adversaries.

### 3.3 Automated Verification & Testing Suite Scope

The system must be verified by a robust suite of automated unit and integration tests. The scope of this suite must cover:
1. **Idempotency and Merging Tests**:
   - Verify that sequential imports of the exact same asset payload result in a single asset record.
   - Verify that updating an asset modifies its `last_seen` timestamp while retaining the original `first_seen` value.
   - Assert that tag lists are merged correctly (no duplicate tags, union of existing and new tags).
   - Assert that metadata dictionaries merge correctly (new keys added, existing keys updated with latest values).
2. **Lifecycle Transitions**:
   - Verify that new assets start in the `Active` state.
   - Verify that stale assets transition to `Active` automatically when re-sighted in an import batch.
   - Assert that archiving an asset behaves deterministically and excludes it from standard retrieval scopes.
3. **Graph Relationship Resolution**:
   - Validate that adding a relationship creates a valid connection between two existing assets.
   - Validate that retrieving an asset with its relationships correctly builds the adjacent graph structure (first-degree neighbors).
   - Assert that deleting a node cascades the removal of associated relationship edges, verifying that no dangling relationships exist.
4. **Pagination and Filtration Tests**:
   - Validate that listing operations return paginated results with predefined limit/offset boundaries.
   - Verify that filters (such as type, status, tag membership, and substring matching on canonical values) return mathematically correct subsets.
5. **Fault Tolerance and Resilience Tests**:
   - Simulate a bulk import batch containing a mix of valid and syntactically malformed records.
   - Assert that all valid assets are successfully created or updated, while malformed records are rejected and logged, without triggering a transaction-wide rollback or runtime crash.
