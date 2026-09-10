# System Architecture & Technical Design

The **Dispensary Management System (DMS)** is designed as a high-throughput, distributed, and fault-tolerant healthcare management platform. It combines an **enterprise-grade full-stack web service** with a **custom-engineered ACID storage and transaction engine**.

---

## 🏗️ High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                             Client Layer (Browser / REST API)                   │
│         - Web Dashboard (HTML5 / Modern CSS / Vanilla JS)                       │
│         - Automated API Consumers / Mobile Clients / Stress Test Agents         │
└────────────────────────────────────────┬────────────────────────────────────────┘
                                         │  HTTPS / JSON Payloads
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
│  - MD5 Hash Routing (O(1))           │  │  - In-Memory / On-Disk B+ Tree       │
│  - Scatter-Gather Aggregator         │  │  - Write-Ahead Logging (WAL)         │
│  - Cross-Shard Conflict Engine       │  │  - ARIES-Style Crash Recovery        │
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

## 🧩 Architectural Modules

### 1. Presentation & API Layer (`app/`)
- **Web Interface**: Lightweight, responsive single-page dashboard for administrators, doctors, patients, and staff.
- **RESTful Endpoints**: Standardized JSON APIs with predictable HTTP status codes (200, 201, 400, 401, 403, 404, 409, 500).
- **Authentication & RBAC**: JWT and session-based authentication enforcing strict role boundaries (`Admin`, `Doctor`, `Patient`, `Staff`).
- **Audit Logging Subsystem**: Structured log generation recording state mutations, login attempts, appointment bookings, and inventory updates.

### 2. Distributed Sharding Subsystem (`app/sharding.py` & `app/sharded_db.py`)
- **Deterministic Partitioning**: Partitions high-cardinality entities (Patients, Appointments, Doctors, Members) across $N$ physical MySQL nodes using consistent MD5 hashing:
  $$\text{Shard ID} = \text{MD5}(\text{Member ID}) \pmod N$$
- **Query Router & Scatter-Gather Engine**: Routes point queries directly to the target shard with zero cross-talk, and broadcasts multi-shard aggregation queries in parallel.
- **Replication of Static Reference Tables**: Medicine inventories and lookup catalogs are replicated across all shards to eliminate distributed cross-shard joins.

### 3. Custom Storage Engine & ACID Subsystem (`core_engine/`)
- **B+ Tree Indexing Engine**: High fan-out balanced tree structure providing logarithmic point searches ($O(\log N)$) and linked-leaf sequential range scanning.
- **Write-Ahead Logging (WAL)**: Append-only log recording transaction operations prior to buffer mutations to ensure atomicity and durability.
- **ARIES-Style Crash Recovery**: Multi-phase recovery (Analysis, Redo, Undo) to guarantee that uncommitted transactions are rolled back following an abrupt system failure.
- **Strict 2PL Transaction Manager**: Concurrency control preventing dirty reads, non-repeatable reads, and phantom records.

---

## 🔐 Security & Role-Based Access Control (RBAC)

| Role | Permissions |
|------|-------------|
| **Admin** | Full system access: add/remove members, assign doctor schedules, view system-wide audit logs, manage inventory. |
| **Doctor** | View assigned patient appointments, write prescriptions, manage personal availability slots. |
| **Patient** | View personal medical history, book appointments, check assigned doctor details, view prescriptions. |
| **Staff / Pharmacist** | Update medicine inventory stock, dispense prescribed medicines, view stock alerts. |

---

## ⚡ Concurrency & Transaction Management

1. **Unique Constraint Checks**: Multi-shard conflict detection prevents double booking of doctor slots across concurrent client threads.
2. **Atomic Rollback on Failure**: Multi-step operations (e.g. member creation spanning local auth tables and remote shard patient tables) execute with automatic compensating rollbacks upon partial network/database failure.
3. **Structured Audit Trail**: All mutating actions are committed to an append-only audit trail table for regulatory compliance and tracing.
