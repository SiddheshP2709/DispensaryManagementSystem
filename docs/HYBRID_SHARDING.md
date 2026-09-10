# Distributed Database Sharding and Partitioning Architecture

## Overview

To evaluate horizontal scalability and avoid a single database bottleneck, this project implements a distributed sharded database architecture partitioned across 3 MySQL server instances.

---

## Sharding Strategy and Key Selection

### 1. Shard Key: `member_id`
The `member_id` was chosen as the primary partitioning key for the following reasons:
- **Cardinality**: Provides a distinct identifier for patients, doctors, and staff members across the dataset.
- **Query Alignment**: The majority of queries in the application (such as patient records, doctor consultations, and appointment lookups) filter by `member_id`.
- **Stability**: A member's identifier remains unchanged after creation, avoiding cross-shard record moves.

### 2. Hash-Based Routing
The system uses MD5 hashing with modulo arithmetic to assign records across $N$ shards:

$$\text{Shard ID} = \text{MD5}(\text{member\_id}) \pmod 3$$

```python
import hashlib

def get_shard_id(member_id: int, num_shards: int = 3) -> int:
    hash_obj = hashlib.md5(str(member_id).encode())
    return int(hash_obj.hexdigest(), 16) % num_shards
```

**Characteristics**:
- **Deterministic**: The same `member_id` always routes to the same shard without needing a centralized lookup table.
- **Even Distribution**: Distributes records uniformly across available nodes.

---

## Partitioning Model

```
┌───────────────────────────────────────────────────────────────────────────┐
│                           Partitioning Topology                           │
├─────────────────────────────────────┬─────────────────────────────────────┤
│      Sharded Entity Tables          │     Replicated Reference Tables     │
│   (Partitioned across Shards 0,1,2) │        (Replicated on all nodes)    │
├─────────────────────────────────────┼─────────────────────────────────────┤
│  - shard_{i}_member                 │  - medicine                         │
│  - shard_{i}_patient                │  - inventory                        │
│  - shard_{i}_doctor                 │  - slots                            │
│  - shard_{i}_appointment            │  - audit_log                        │
│  - shard_{i}_prescription           │                                     │
└─────────────────────────────────────┴─────────────────────────────────────┘
```

Tables containing frequent entity updates (members, patients, doctors, appointments) are partitioned by shard key. Reference tables with relatively static data (medicines, slots) are replicated across all nodes so that queries can execute local joins without cross-network table joins.

---

## Query Execution Patterns

### 1. Single-Shard Point Queries
When a query specifies `member_id`, the `ShardedDBLayer` routes the query directly to the target shard:
```
Client Request: GET /member/7
   │
   ▼
Hash Calculation: MD5("7") % 3 = 1
   │
   ▼
Target Node: Shard 1 (Port 3308)
   │
   ▼
SQL Execution: SELECT * FROM shard_1_member WHERE member_id = 7;
```

### 2. Multi-Shard Scatter-Gather Queries
When querying data across non-partitioned fields (such as listing all doctors or fetching global appointment summaries), the application executes queries across all shards and aggregates the results:
```
Client Request: GET /all-doctors
   │
   ├──────► Query Shard 0 ──► [Doctor A, Doctor B]
   ├──────► Query Shard 1 ──► [Doctor C]
   └──────► Query Shard 2 ──► [Doctor D, Doctor E]
   │
   ▼
Aggregator Combines Results -> [Doctor A, B, C, D, E]
```

---

## System Trade-offs and Characteristics

| Aspect | Single Node Database | 3-Node Sharded Architecture |
|---|---|---|
| **Write Distribution** | Handled by single server | Distributed across 3 nodes |
| **Routing Mechanism** | Direct connection | Hash-based routing via application layer |
| **Availability on Node Failure** | Full outage on failure | Remaining 2 nodes remain accessible |
| **Consistency** | ACID transactions across all tables | ACID within a single shard; aggregate views combine multi-shard data |
| **System Classification** | CA | AP |

### Migration and Verification
The data migration script (`migrate_shards.py`) reads records from the source database, evaluates the hash for each record, inserts records into their corresponding shard tables, and verifies that the total record counts match before completing.
