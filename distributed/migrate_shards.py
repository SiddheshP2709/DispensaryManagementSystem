#!/usr/bin/env python3
"""
Migration script for Assignment 4 - Sharding Implementation
This script initializes sharded tables on all 3 remote shards and migrates data.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from sharding import (
    create_sharded_schema, 
    migrate_data_to_shards, 
    verify_sharding,
    get_shard_connection
)
from app.config import get_db_settings, get_shard_settings
import mysql.connector

def main():
    print("=" * 60)
    print("Assignment 4: Sharding Migration Script")
    print("=" * 60)
    
    # Get source database settings
    db_settings = get_db_settings()
    
    print("\n[1] Connecting to source database...")
    try:
        source_conn = mysql.connector.connect(
            host=db_settings["host"],
            user=db_settings["user"],
            password=db_settings["password"],
            database=db_settings["database"]
        )
        print(f"✓ Connected to {db_settings['host']}:{db_settings['database']}")
    except Exception as e:
        print(f"✗ Failed to connect to source: {str(e)}")
        return
    
    # Get shard credentials from .env file
    print("\n[2] Initializing remote shards...")
    print("   Shards: 10.0.116.184:3307, :3308, :3309")
    
    # Get shard-specific credentials from config (SHARD_DB_USER, SHARD_DB_PASSWORD)
    shard_config = get_shard_settings()
    shard_username = shard_config["user"]          # The_Boys (from SHARD_DB_USER)
    shard_password = shard_config["password"]      # password@123 (from SHARD_DB_PASSWORD)
    shard_database = shard_config["database"]      # The_Boys (from SHARD_DB_NAME)
    
    print(f"   Username: {shard_username}")
    print(f"   Database: {shard_database}")
    
    # Test connections to all shards
    print("\n[3] Testing connections to all shards...")
    for shard_id in range(3):
        try:
            test_conn = get_shard_connection(shard_id, shard_username, shard_password, shard_database)
            cursor = test_conn.cursor()
            cursor.execute("SELECT @@hostname")
            hostname = cursor.fetchone()[0]
            print(f"   ✓ Shard {shard_id}: {hostname}")
            cursor.close()
            test_conn.close()
        except Exception as e:
            print(f"   ✗ Shard {shard_id}: {str(e)}")
            print(f"   ERROR: Cannot proceed without all shards!")
            source_conn.close()
            return
    
    # Create sharded schema
    print("\n[4] Creating sharded schema on all shards...")
    try:
        create_sharded_schema(shard_username, shard_password, shard_database)
    except Exception as e:
        print(f"✗ Error creating schema: {str(e)}")
        source_conn.close()
        return
    
    # Migrate data
    print("\n[5] Migrating data from source to shards...")
    try:
        migrate_data_to_shards(source_conn, shard_username, shard_password, shard_database)
    except Exception as e:
        print(f"✗ Error during migration: {str(e)}")
        source_conn.close()
        return
    
    # Verify sharding
    print("\n[6] Verifying data distribution...")
    stats = verify_sharding(shard_username, shard_password, shard_database)
    
    print("\nData Distribution Across Shards:")
    print("-" * 60)
    total_by_table = {}
    for shard_label, counts in sorted(stats.items()):
        print(f"\n{shard_label}:")
        for table, count in counts.items():
            print(f"  {table:20} : {count:3} records")
            if table not in total_by_table:
                total_by_table[table] = 0
            total_by_table[table] += count
    
    print("\n" + "-" * 60)
    print("Total Records per Table:")
    for table, total in sorted(total_by_table.items()):
        print(f"  {table:20} : {total:3} records")
    
    print("\n" + "=" * 60)
    print("✓ Sharding Migration Completed Successfully!")
    print("=" * 60)
    
    source_conn.close()

if __name__ == "__main__":
    main()
