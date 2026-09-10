# Custom B+ Tree Storage & ACID Transaction Engine

## 🔬 Overview

As part of the database systems implementation, we engineered a **custom Relational Storage & ACID Transaction Engine in Python from scratch**. This engine demonstrates low-level database kernel concepts including balanced tree indexing, write-ahead logging (WAL), crash recovery algorithms, and strict concurrency control.

---

## 🌲 B+ Tree Indexing Subsystem (`core_engine/bplustree.py`)

A B+ Tree of configurable order $M$ serves as the primary indexed storage mechanism for tabular data.

### Structural Properties
- **Balanced Multilevel Hierarchy**: All leaf nodes reside at the exact same depth ($O(\log_M N)$ height).
- **High Fan-Out**: Non-leaf index nodes store up to $M - 1$ search keys and $M$ child pointers.
- **Linked Leaf Chain**: Leaf nodes store the actual record payloads and maintain bidirectional pointers (`prev_leaf` and `next_leaf`) to enable rapid range scanning.
- **Dynamic Node Splitting & Merging**: Proactively balances upon reaching overflow capacity ($\ge M$ keys).

```
                      ┌───────────────┐
                      │    [ 50 ]     │  (Root Index Node)
                      └───┬───────┬───┘
                          │       │
              ┌───────────┘       └───────────┐
              ▼                               ▼
      ┌───────────────┐               ┌───────────────┐
      │  [ 20 , 35 ]  │               │  [ 65 , 80 ]  │  (Internal Nodes)
      └──┬───┬───┬────┘               └──┬───┬───┬────┘
         │   │   │                       │   │   │
   ┌─────┘   │   └─────┐           ┌─────┘   │   └─────┐
   ▼         ▼         ▼           ▼         ▼         ▼
┌─────┐   ┌─────┐   ┌─────┐     ┌─────┐   ┌─────┐   ┌─────┐
│10,15│──►│22,28│──►│38,45│────►│52,60│──►│70,75│──►│85,95│ (Leaf Nodes: Data)
└─────┘   └─────┘   └─────┘     └─────┘   └─────┘   └─────┘
```

### Search Time Complexity Comparison
- **Point Search**: $O(\log N)$ via B+ Tree vs $O(N)$ via Linear Scan.
- **Range Query**: $O(\log N + K)$ (where $K$ is the number of qualifying items in the range) by locating the starting leaf and traversing sequential pointers.

---

## 📜 Write-Ahead Logging (WAL) Subsystem (`core_engine/wal.py`)

To satisfy the **Durability** and **Atomicity** criteria of ACID:
1. **Append-Only Serialization**: Every mutating action (`BEGIN`, `INSERT`, `UPDATE`, `DELETE`, `COMMIT`, `ROLLBACK`) is serialized to an on-disk append-only log file before modifying the in-memory tree buffer.
2. **Before-Image Logging**: For `UPDATE` and `DELETE` operations, the log records the exact previous state of the row to enable deterministic rollback.

```json
{"lsn": 101, "txn_id": 1, "op": "BEGIN", "table": null, "key": null, "before": null, "after": null}
{"lsn": 102, "txn_id": 1, "op": "INSERT", "table": "employees", "key": 42, "before": null, "after": {"name": "Alice", "role": "Doctor"}}
{"lsn": 103, "txn_id": 1, "op": "COMMIT", "table": null, "key": null, "before": null, "after": null}
```

---

## 🛡️ ARIES-Style Crash Recovery Protocol (`core_engine/recovery.py`)

If the DBMS process terminates unexpectedly (e.g., power loss or kill signal), `recovery.recover()` executes on startup:

```
[Crash Occurs] ──► System Restart
                         │
                         ▼
             ┌───────────────────────┐
             │    1. Analysis Phase  │  Scans WAL to identify Active (Incomplete),
             │                       │  Committed, and Aborted transactions.
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │     2. Redo Phase     │  Replays all logged operations to restore
             │                       │  the exact state prior to crash.
             └───────────┬───────────┘
                         │
                         ▼
             ┌───────────────────────┐
             │     3. Undo Phase     │  Reverses operations of all active uncommitted
             │                       │  transactions in reverse LSN order.
             └───────────────────────┘
```

---

## 🔒 Transaction Manager & Concurrency Control (`core_engine/transaction_manager.py`)

- **Strict 2-Phase Locking (2PL)**: Acquires shared read locks and exclusive write locks during transaction execution and holds write locks until `COMMIT` or `ROLLBACK`.
- **Durability Snapshots**: Upon transaction commit, the database state is checkpointed to persistent storage (`db_snapshot.json`).
- **Comprehensive Validation**: Tested against 6 rigorous ACID scenarios:
  1. Full rollback reverts all inserts/updates.
  2. Partial failure mid-transaction handles exceptions cleanly.
  3. Consistency validation prevents invalid table modifications.
  4. Durability test confirms committed records survive restarts.
  5. Crash recovery test verifies that uncommitted in-flight operations are undone.
  6. Isolation test guarantees that aborted transactions do not leak dirty state to concurrent transactions.
