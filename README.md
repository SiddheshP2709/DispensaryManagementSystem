<div align="center">

# Dispensary Management System (DMS)
### Distributed Database Sharding, Custom Storage Engine, and Full-Stack Web Application

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.0-black.svg)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-orange.svg)](https://www.mysql.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

<p align="center">
  <a href="#system-architecture">Architecture</a> •
  <a href="#implemented-components">Components</a> •
  <a href="#custom-acid-storage-engine">Storage Engine</a> •
  <a href="#distributed-database-sharding">Sharding</a> •
  <a href="#benchmarks-and-performance">Benchmarks</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#interview-discussion-topics">Interview Topics</a>
</p>

---

</div>

## Project Overview

The Dispensary Management System (DMS) is a database project that covers relational modeling, full-stack application development, distributed database sharding, and custom storage engine internals.

The repository contains two main subsystems:
1. **Web Application and Distributed Database**: A Flask REST API connected to a 3-node horizontally sharded MySQL cluster using deterministic hash routing, scatter-gather query aggregation, role-based access control (RBAC), and concurrency management.
2. **Custom Storage Engine**: An in-memory/disk-backed storage engine implemented in Python featuring a B+ Tree index, Write-Ahead Logging (WAL), ARIES-style crash recovery, and two-phase locking (2PL) transaction management.

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

## Implemented Components

### 1. Distributed Database Sharding
- **Hash-Based Routing**: Partitions patient, doctor, and appointment records across 3 MySQL nodes using `MD5(member_id) % 3`.
- **Abstraction Layer (`ShardedDBLayer`)**: Handles single-shard routing for point queries and scatter-gather execution for multi-shard aggregate queries.
- **Replicated Tables**: Static reference tables (such as medicine inventory and appointment slots) are replicated across nodes to enable local joins.
- **Migration Script**: `migrate_shards.py` partitions existing data into the shard schema and verifies row count consistency.

### 2. Custom Storage and Transaction Engine
- **B+ Tree Index**: Balanced tree implementation providing logarithmic search ($O(\log N)$) and linked leaf nodes for range scans.
- **Write-Ahead Logging (WAL)**: Append-only log recording operation state before in-memory mutations.
- **Crash Recovery**: ARIES-style recovery with Analysis, Redo, and Undo phases to reverse uncommitted transactions upon reboot.
- **Two-Phase Locking (2PL)**: Concurrency manager using read/write locks to prevent race conditions and dirty reads.

### 3. Application and Relational Design
- **Role-Based Access Control (RBAC)**: Role permissions for Admin, Doctor, Patient, and Staff roles.
- **Audit Log System**: Records operations and state modifications with timestamps.
- **Database Schema (3NF)**: Relational schema including constraints, foreign keys, and indexes.

---

## Benchmarks and Performance

### 1. Custom B+ Tree vs Sequential Scan ($N = 10,000$ Records)
| Search Type | B+ Tree Index ($O(\log N)$) | Sequential Scan ($O(N)$) | Observed Speedup |
|---|---|---|---|
| **Point Lookup** | **1.72 µs** | **24.77 µs** | **14.3x** |
| **Range Scan** | Leaf pointer traversal | Full array traversal | - |

<p align="center">
  <img src="benchmarks/results/benchmark_results.png" width="45%" alt="B+ Tree vs Linear Scan Benchmark" />
  <img src="benchmarks/results/query_performance.png" width="45%" alt="Query Optimization Latency" />
</p>

### 2. Sharded Cluster Scaling (Locust Load Test)
| Metric | Single Database Instance | 3-Node Sharded Cluster |
|---|---|---|
| **Sustained Throughput** | ~1,000 req/sec | ~3,000 req/sec |
| **Point Query Latency** | 50 – 100 ms | 15 – 25 ms |
| **Fault Tolerance** | Single failure point | Survives single node failure with partial availability |

---

## Project Structure

```
dispensary-management-system/
├── README.md                          # Main project documentation
├── LICENSE                            # MIT License
├── requirements.txt                   # Dependencies
├── .env.example                       # Environment configuration template
├── .gitignore                         # Git ignore rules
├── run.py                             # CLI runner
│
├── app/                               # Web Application and REST API (Flask)
│   ├── main.py                        # Application entry point
│   ├── config.py                      # Configuration loader
│   ├── auth.py                        # Authentication and RBAC
│   ├── db.py                          # Database connection handling
│   ├── sharded_db.py                  # Sharded database abstraction layer
│   ├── sharding.py                    # Hash routing functions
│   ├── logger.py                      # Audit logging
│   ├── validators.py                  # Request validators
│   ├── routes/                        # REST API routes
│   │   ├── auth_routes.py             # Authentication endpoints
│   │   ├── admin_routes.py            # Admin operations
│   │   ├── appointment_routes.py      # Scheduling and conflict checks
│   │   ├── doctor_routes.py           # Doctor profiles
│   │   ├── medicine_routes.py         # Inventory and prescriptions
│   │   ├── member_routes.py           # Member data
│   │   └── patient_routes.py          # Patient medical history
│   └── templates/                     # Web UI
│       └── index.html                 # Main interface
│
├── core_engine/                       # Custom Storage and ACID Engine
│   ├── bplustree.py                   # B+ Tree index
│   ├── bruteforce.py                  # Sequential scan baseline
│   ├── table.py                       # Table abstraction
│   ├── db_manager.py                  # Database manager
│   ├── wal.py                         # Write-Ahead Logging
│   ├── recovery.py                    # Crash recovery implementation
│   └── transaction_manager.py         # 2PL Transaction Manager
│
├── database/                          # SQL Schemas and Design
│   ├── schema.sql                     # Relational schema DDL
│   ├── indexing_strategy.sql          # Index definitions and query plans
│   ├── seed_data.sql                  # Initial seed data
│   └── diagrams/                      # System diagrams
│       ├── er_diagram.png             # Entity-Relationship diagram
│       └── uml_diagram.png            # UML diagram
│
├── distributed/                       # Sharding Utilities
│   ├── migrate_shards.py              # Shard data migration
│   ├── shard_tables.py                # Sharded table setup
│   ├── query_router.py                # Query router
│   ├── range_query_executor.py        # Distributed range queries
│   └── trade_off_analyzer.py          # Trade-off evaluation
│
├── tests/                             # Test Suite
│   ├── test_acid_engine.py            # ACID compliance tests (6 tests)
│   ├── test_concurrency.py            # Concurrent booking tests
│   ├── test_rollback_failure.py       # Rollback tests
│   ├── test_sharding.py               # Shard routing tests
│   ├── test_api.py                    # API integration tests
│   ├── test_appointments.py           # Appointment tests
│   ├── test_medicines.py              # Inventory tests
│   └── test_doctors.py                # Doctor lookup tests
│
├── benchmarks/                        # Performance and Load Testing
│   ├── locustfile.py                  # Locust load test scenarios
│   ├── locust_report.html             # HTML load test report
│   ├── results/                       # Performance metrics and plots
│   └── seed_test_data.py              # Data generator
│
└── docs/                              # Technical Documentation
    ├── ARCHITECTURE.md                # Architecture overview
    ├── HYBRID_SHARDING.md             # Sharding documentation
    ├── STORAGE_ENGINE.md              # Storage engine documentation
    └── API_REFERENCE.md               # API endpoint specification
```

---

## Quick Start

### 1. Environment Setup
```bash
git clone https://github.com/your-username/dispensary-management-system.git
cd dispensary-management-system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your MySQL credentials
```

### 3. Run Custom Storage Engine Tests
To run the storage engine test suite:
```bash
python run.py test-acid
```
```
[PASS]  Atomicity - full rollback                    PASS
[PASS]  Atomicity - partial failure                  PASS
[PASS]  Consistency - invalid table access           PASS
[PASS]  Durability - snapshot restore                PASS
[PASS]  Durability - WAL crash recovery              PASS
[PASS]  Isolation - rolled-back TXN                  PASS

All 6 ACID tests PASSED.
```

### 4. Run Search Performance Benchmark
```bash
python run.py benchmark
```

### 5. Start Web Server
```bash
python run.py server
```
The application will run at `http://localhost:5000`.

---
---

## License

This project is licensed under the [MIT License](LICENSE).
