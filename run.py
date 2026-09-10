#!/usr/bin/env python3
"""
Dispensary Management System (DMS) & Distributed Engine
=========================================================
Unified CLI runner for web server, storage engine benchmarks,
ACID test suite, shard migrations, and system diagnostics.
"""

import sys
import os
import argparse
import subprocess

# Ensure repository root is on Python path
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


BANNER = r"""
================================================================================
  ____  _                                              ____            _                 
 |  _ \(_)___ _ __   ___ _ __  ___  __ _ _ __ _   _   / ___| _   _ ___| |_ ___ _ __ ___  
 | | | | / __| '_ \ / _ \ '_ \/ __|/ _` | '__| | | |  \___ \| | | / __| __/ _ \ '_ ` _ \ 
 | |_| | \__ \ |_) |  __/ | | \__ \ (_| | |  | |_| |   ___) | |_| \__ \ ||  __/ | | | | |
 |____/|_|___/ .__/ \___|_| |_|___/\__,_|_|   \__, |  |____/ \__, |___/\__\___|_| |_| |_|
             |_|                              |___/          |___/                       
  Distributed Storage Engine, Sharding Layer & Full-Stack Medical Dispensary System
================================================================================
"""


def start_server(host="0.0.0.0", port=5000, debug=True):
    """Start the Flask REST API & Web Dashboard."""
    print(BANNER)
    print(f"[*] Starting Dispensary Web Application on http://{host}:{port} ...")
    os.chdir(os.path.join(REPO_ROOT, "app"))
    from app.main import app
    app.run(host=host, port=port, debug=debug)


def run_acid_tests():
    """Run the 6 ACID verification tests on the custom B+ Tree / WAL engine."""
    print(BANNER)
    print("[*] Running Custom Storage Engine ACID Compliance & Crash Recovery Tests...")
    test_script = os.path.join(REPO_ROOT, "tests", "test_acid_engine.py")
    result = subprocess.run([sys.executable, test_script], cwd=REPO_ROOT)
    sys.exit(result.returncode)


def run_all_tests():
    """Run full test suite (ACID engine, concurrency, failure/rollback, API)."""
    print(BANNER)
    print("[*] Running Complete Dispensary Management System Test Suite...")
    test_dir = os.path.join(REPO_ROOT, "tests")
    tests = [
        ("ACID Engine & Crash Recovery", "test_acid_engine.py"),
        ("Concurrency & Race Condition Control", "test_concurrency.py"),
        ("Failure & Rollback Mechanics", "test_rollback_failure.py"),
        ("Distributed Sharding & Routing", "test_sharding.py"),
    ]
    
    overall_status = True
    for title, test_file in tests:
        path = os.path.join(test_dir, test_file)
        if os.path.exists(path):
            print(f"\n--- Running: {title} ({test_file}) ---")
            res = subprocess.run([sys.executable, path], cwd=REPO_ROOT)
            if res.returncode != 0:
                overall_status = False
    
    print("\n" + "=" * 80)
    if overall_status:
        print("[SUCCESS] All test suites passed successfully!")
    else:
        print("[WARNING] One or more tests reported failures or missing DB connections.")
    print("=" * 80)


def run_shard_migration():
    """Execute horizontal sharding data migration."""
    print(BANNER)
    print("[*] Executing Distributed Shard Migration...")
    script = os.path.join(REPO_ROOT, "distributed", "migrate_shards.py")
    result = subprocess.run([sys.executable, script], cwd=REPO_ROOT)
    sys.exit(result.returncode)


def run_bplustree_benchmark():
    """Run B+ Tree vs Sequential Scan benchmark."""
    print(BANNER)
    print("[*] Executing B+ Tree vs Linear Scan Search Benchmark...")
    import time
    from core_engine.bplustree import BPlusTree
    from core_engine.bruteforce import BruteForceDB

    N = 10000
    print(f"[*] Generating {N:,} records...")
    bpt = BPlusTree(order=16)
    bf = BruteForceDB()
    
    for i in range(1, N + 1):
        rec = {"id": i, "name": f"Patient_{i}", "age": 20 + (i % 60)}
        bpt.insert(i, rec)
        bf.insert(i)

    # Point Lookup Benchmark
    target_keys = [1, N // 4, N // 2, (3 * N) // 4, N]
    print(f"\n[*] Benchmarking Point Lookups for keys: {target_keys}")
    
    # B+ Tree Lookup
    t0 = time.perf_counter()
    for _ in range(100):
        for k in target_keys:
            _ = bpt.search(k)
    t_bpt = (time.perf_counter() - t0) / 500 * 1e6

    # Linear Scan Lookup
    t0 = time.perf_counter()
    for _ in range(100):
        for k in target_keys:
            _ = bf.search(k)
    t_bf = (time.perf_counter() - t0) / 500 * 1e6

    print(f"  - B+ Tree Avg Lookup Time : {t_bpt:.3f} microseconds  [O(log N)]")
    print(f"  - Linear Scan Avg Lookup   : {t_bf:.3f} microseconds  [O(N)]")
    print(f"  -> Speedup: {t_bf / max(t_bpt, 0.001):.1f}x faster with B+ Tree Indexing!")


def main():
    parser = argparse.ArgumentParser(
        description="Dispensary Management System - Unified CLI Controller",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available sub-commands")
    
    # Server command
    server_parser = subparsers.add_parser("server", help="Start the Flask Web & API Server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Binding host (default: 0.0.0.0)")
    server_parser.add_argument("--port", type=int, default=5000, help="Port (default: 5000)")
    server_parser.add_argument("--no-debug", dest="debug", action="store_false", help="Disable debug mode")
    
    # Tests commands
    subparsers.add_parser("test-acid", help="Run 6 ACID validation & crash recovery tests on custom engine")
    subparsers.add_parser("test-all", help="Run all unit, integration, and distributed tests")
    
    # Migration command
    subparsers.add_parser("migrate-shards", help="Execute horizontal database sharding migration")
    
    # Benchmark command
    subparsers.add_parser("benchmark", help="Run B+ Tree vs Sequential Scan benchmark")

    args = parser.parse_args()
    
    if args.command == "server":
        start_server(host=args.host, port=args.port, debug=args.debug)
    elif args.command == "test-acid":
        run_acid_tests()
    elif args.command == "test-all":
        run_all_tests()
    elif args.command == "migrate-shards":
        run_shard_migration()
    elif args.command == "benchmark":
        run_bplustree_benchmark()
    else:
        print(BANNER)
        parser.print_help()


if __name__ == "__main__":
    main()
