# System Architecture and Technical Design

The Dispensary Management System (DMS) is a relational database project that includes a full-stack web application, a distributed database sharding layer, and an independent custom-built storage and transaction engine.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             Client Layer (Browser / REST API)                   │
│         - Web Dashboard (HTML / CSS / JavaScript)                               │
│         - Automated API Clients / Test Scripts                                  │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │  HTTP / JSON Payloads
                                         ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           Application Server (Flask 3.0)                        │
│  ┌───────────────────────────┐ ┌───────────────────────────┐ ┌────────────────┐ │
│  │   Auth & RBAC Middleware  │ │ Input Validators & Schema │ │  Audit Logger  │ │
│  └─────────────┬─────────────┘ └─────────────┬─────────────┘ └────────┬───────┘ │
│                │                             │                        │         │
│  ┌─────────────▼─────────────────────────────▼────────────────────────▼───────┐ │
│  │                            Modular Route Handlers                          │ │
│  │   /api/auth  •  /api/member  •  /api/patient  •  /api/doctor  •  /api/admin│ │
│  └─────────────────────────────────────┬──────────────────────────────────────┘ │
└────────────────────────────────────────┼────────────────────────────────────────┘
                                         │
                    ┌────────────────────┴────────────────────┐
                    │                                         │
                    ▼                                         ▼
┌──────────────────────────────────────┐  ┌──────────────────────────────────────┐
│       Distributed Sharding Layer     │  │     Custom ACID Storage Engine       │
│  - MD5 Hash Routing                  │  │  - In-Memory / Disk-Backed B+ Tree   │
│  - Scatter-Gather Aggregator         │  │  - Write-Ahead Logging (WAL)         │
│  - Cross-Shard Conflict Handling     │  │  - ARIES-Style Crash Recovery        │
│  - Connection Pooling (3 Shards)     │  │  - 2-Phase Locking (2PL) Txn Manager │
└──────────────────┬───────────────────┘  └──────────────────────────────────────┘
                   │
    ┌──────────────┼──────────────┐
    ▼              ▼              ▼
┌────────┐    ┌────────┐    ┌────────┐
│Shard 0 │    │Shard 1 │    │Shard 2 │
│ (3307) │    │ (3308) │    │ (3309) │
└────────┘    └────────┘    └────────┘
```

---

## Architectural Modules

### 1. Presentation and API Layer (`app/`)
- **Web Interface**: Single-page user interface for administrators, doctors, and patients.
- **RESTful Endpoints**: JSON APIs with HTTP status codes (200, 201, 400, 401, 403, 404, 409, 500).
- **Authentication and RBAC**: Token-based and session-based authentication enforcing role permissions (`Admin`, `Doctor`, `Patient`, `Staff`).
- **Audit Logging**: Log records tracking state mutations, login events, appointments, and inventory updates.

### 2. Distributed Sharding Subsystem (`app/sharding.py` and `app/sharded_db.py`)
- **Deterministic Partitioning**: Partitions entity records (Patients, Appointments, Doctors, Members) across $N$ MySQL nodes using hash-based routing:
  $$\text{Shard ID} = \text{MD5}(\text{Member ID}) \pmod N$$
- **Query Router and Scatter-Gather Aggregator**: Routes point queries directly to the target shard and executes multi-shard queries across all nodes before combining results.
- **Replicated Tables**: Static and catalog tables (such as medicine inventory and time slot metadata) are replicated on all shards to avoid cross-shard network joins.

### 3. Custom Storage Engine (`core_engine/`)
- **B+ Tree Indexing Engine**: Balanced tree implementation providing logarithmic search complexity ($O(\log N)$) and linked leaf nodes for range scans.
- **Write-Ahead Logging (WAL)**: Append-only log that writes operation records before modifying the in-memory data structures.
- **Crash Recovery**: Three-phase recovery algorithm (Analysis, Redo, Undo) to undo uncommitted transactions after a crash.
- **Transaction Manager**: Concurrency control using two-phase locking to maintain transaction isolation.

---

## Security and Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **Admin** | Manage members and staff, view audit logs, update inventory, manage appointments. |
| **Doctor** | View assigned appointments, manage consultation slots, create prescriptions. |
| **Patient** | View medical history, schedule appointments, view assigned doctor information. |
| **Staff / Pharmacist** | Update medicine inventory stock levels, view stock alerts. |

---

## Concurrency and Transaction Management

1. **Conflict Detection**: Slot and schedule checks prevent duplicate appointment bookings across concurrent requests.
2. **Failure Handling**: Multi-table operations incorporate rollback logic if one of the write operations fails during execution.
3. **Audit Trail**: Mutating operations write an entry to an audit table to maintain a history of actions.
