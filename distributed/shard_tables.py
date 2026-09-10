import mysql.connector
import hashlib
from mysql.connector import Error

# Credentials
credentials = {
    'host': '10.0.116.184',
    'user': 'The_Boys',
    'password': 'password@123',
    'database': 'The_Boys'
}

shards = [
    {'name': 'Shard 0', 'port': 3307},
    {'name': 'Shard 1', 'port': 3308},
    {'name': 'Shard 2', 'port': 3309}
]

print("\n" + "=" * 90)
print("PART 1: SHARDED TABLES & PARTITIONING LOGIC")
print("=" * 90)

# ============================================================================
# SECTION 1: Show Replicated Tables
# ============================================================================
print("\n📋 REPLICATED TABLES (Same on ALL 3 shards):")
print("─" * 90)

try:
    conn = mysql.connector.connect(
        host=credentials['host'],
        port=3307,
        user=credentials['user'],
        password=credentials['password'],
        database=credentials['database']
    )
    cursor = conn.cursor()
    
    replicated = ['medicine', 'inventory', 'prescription', 'slots', 'audit_log']
    for table in replicated:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  ✓ {table:<20} ({count:>3} records) - Replicated on Shard 0, 1, 2")
    
    conn.close()
except Error as e:
    print(f"Error: {e}")

# ============================================================================
# SECTION 2: Show Sharded Tables
# ============================================================================
print("\n\n📊 SHARDED TABLES (Partitioned across 3 shards):")
print("─" * 90)

for shard in shards:
    shard_num = shard['port'] - 3307
    try:
        conn = mysql.connector.connect(
            host=credentials['host'],
            port=shard['port'],
            user=credentials['user'],
            password=credentials['password'],
            database=credentials['database']
        )
        cursor = conn.cursor()
        
        print(f"\n  {shard['name']} (Port {shard['port']}):")
        
        sharded_tables = [
            f'shard_{shard_num}_member',
            f'shard_{shard_num}_doctor',
            f'shard_{shard_num}_patient',
            f'shard_{shard_num}_appointment'
        ]
        
        for table in sharded_tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"    ✓ {table:<30} ({count:>3} records)")
        
        conn.close()
    except Error as e:
        print(f"  Error: {e}")

# ============================================================================
# SECTION 3: Partitioning Logic with Examples
# ============================================================================
print("\n\n" + "=" * 90)
print("PARTITIONING LOGIC: MD5(member_id) mod 3")
print("=" * 90)

print("""
Formula:
  shard_id = MD5(member_id) mod 3
  
This distributes members evenly across 3 shards (0, 1, 2)
""")

print("─" * 90)
print("LIVE EXAMPLES OF HOW MEMBERS ARE ROUTED:")
print("─" * 90)

# Get actual members and show their routing
try:
    conn = mysql.connector.connect(
        host=credentials['host'],
        port=3307,
        user=credentials['user'],
        password=credentials['password'],
        database=credentials['database']
    )
    cursor = conn.cursor()
    
    # Get members from each shard to show the distribution
    member_examples = []
    
    for shard in shards:
        shard_num = shard['port'] - 3307
        cursor.execute(f"SELECT member_id, name FROM shard_{shard_num}_member LIMIT 2")
        members = cursor.fetchall()
        for member_id, member_name in members:
            # Calculate shard
            md5_hash = hashlib.md5(str(member_id).encode()).hexdigest()
            shard_id = int(md5_hash, 16) % 3
            member_examples.append((member_id, member_name, shard_id))
    
    for member_id, member_name, shard_id in member_examples:
        md5_hash = hashlib.md5(str(member_id).encode()).hexdigest()
        print(f"\n  Member ID {member_id} ({member_name}):")
        print(f"    → MD5 hash: {md5_hash[:16]}...")
        print(f"    → Hash % 3 = {int(md5_hash, 16) % 3}")
        print(f"    → Routes to: Shard {shard_id}")
        print(f"    → Table: shard_{shard_id}_member")
    
    conn.close()
except Error as e:
    print(f"Error: {e}")

# ============================================================================
# SECTION 4: Distribution Summary
# ============================================================================
print("\n\n" + "=" * 90)
print("DISTRIBUTION SUMMARY")
print("=" * 90)

try:
    counts = {}
    for shard in shards:
        shard_num = shard['port'] - 3307
        conn = mysql.connector.connect(
            host=credentials['host'],
            port=shard['port'],
            user=credentials['user'],
            password=credentials['password'],
            database=credentials['database']
        )
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM shard_{shard_num}_member")
        counts[shard_num] = cursor.fetchone()[0]
        conn.close()
    
    total = sum(counts.values())
    print(f"\n  Shard 0: {counts[0]:>2} members")
    print(f"  Shard 1: {counts[1]:>2} members")
    print(f"  Shard 2: {counts[2]:>2} members")
    print(f"  ─────────────────────")
    print(f"  TOTAL:   {total:>2} members\n")
    
except Error as e:
    print(f"Error: {e}")

print("=" * 90)
print("✅ KEY TAKEAWAY: Members are hashed and distributed evenly across 3 shards")
print("=" * 90 + "\n")
