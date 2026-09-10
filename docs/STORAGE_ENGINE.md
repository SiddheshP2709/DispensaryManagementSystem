# Custom B+ Tree Storage and ACID Transaction Engine

## Overview

As part of the database systems coursework, we implemented a custom storage and transaction engine in Python. The engine implements core database kernel mechanisms, including balanced tree indexing, write-ahead logging (WAL), crash recovery, and transaction concurrency management.

---

## B+ Tree Indexing Subsystem (`core_engine/bplustree.py`)

A B+ Tree of configurable order $M$ serves as the indexing mechanism for table data.

### Structural Properties
- **Balanced Multilevel Hierarchy**: All leaf nodes are maintained at the same tree depth ($O(\log_M N)$).
- **Fan-Out**: Non-leaf nodes store up to $M - 1$ search keys and $M$ child pointers.
- **Linked Leaf Nodes**: Leaf nodes store the actual key-value records and maintain forward and backward pointers (`next_leaf`, `prev_leaf`) to support range scans.
- **Node Splitting and Merging**: Splits nodes upon reaching capacity ($\ge M$ keys) and rebalances during deletions.

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

### Search Time Complexity
- **Point Search**: $O(\log N)$ via B+ Tree index vs $O(N)$ via linear scan.
- **Range Query**: $O(\log N + K)$, where $K$ is the number of records returned within the range bounds.

---

## Write-Ahead Logging (WAL) Subsystem (`core_engine/wal.py`)

To support transaction durability and rollback:
1. **Append-Only Log**: Mutating operations (`BEGIN`, `INSERT`, `UPDATE`, `DELETE`, `COMMIT`, `ROLLBACK`) are written to an on-disk log file before applying updates to in-memory tables.
2. **Before-Image Logging**: For `UPDATE` and `DELETE` operations, the log stores the prior state of the row to enable rollback execution.

```json
{"lsn": 101, "txn_id": 1, "op": "BEGIN", "table": null, "key": null, "before": null, "after": null}
{"lsn": 102, "txn_id": 1, "op": "INSERT", "table": "employees", "key": 42, "before": null, "after": {"name": "Alice", "role": "Doctor"}}
{"lsn": 103, "txn_id": 1, "op": "COMMIT", "table": null, "key": null, "before": null, "after": null}
```

---

## Crash Recovery Protocol (`core_engine/recovery.py`)

If the application terminates unexpectedly, `recovery.recover()` executes on startup to restore consistency:

```
[System Termination] ──► Startup Recovery
                              │
                              ▼
                  ┌───────────────────────┐
                  │    1. Analysis Phase  │  Scans WAL to identify Active (Incomplete),
                  │                       │  Committed, and Aborted transactions.
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │     2. Redo Phase     │  Replays logged operations to reconstruct
                  │                       │  state prior to shutdown.
                  └───────────┬───────────┘
                              │
                              ▼
                  ┌───────────────────────┐
                  │     3. Undo Phase     │  Reverses operations of all uncommitted
                  │                       │  transactions in reverse LSN order.
                  └───────────────────────┘
```

---

## Transaction Manager and Concurrency Control (`core_engine/transaction_manager.py`)

- **Two-Phase Locking (2PL)**: Manages shared read locks and exclusive write locks during transaction execution and releases locks upon commit or rollback.
- **State Checkpointing**: Upon commit, the current state can be checkpointed to persistent storage (`db_snapshot.json`).
- **Validation Test Suite**: Evaluated across 6 test cases:
  1. Full rollback reverts all inserts and updates.
  2. Partial failure mid-transaction handles exceptions.
  3. Invalid table access is rejected without side effects.
  4. Committed data persists across simulated restarts.
  5. Incomplete transactions are reversed during WAL crash recovery.
  6. Aborted transactions do not affect committed transactions.
