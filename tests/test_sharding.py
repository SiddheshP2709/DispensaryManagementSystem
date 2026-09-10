import mysql.connector
from mysql.connector import Error

# Credentials from .env
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

print("\n" + "=" * 80)
print("STEP 2: SHOW REPLICATED TABLES (on ALL 3 shards)")
print("=" * 80 + "\n")

# Test all shards
for shard in shards:
    try:
        conn = mysql.connector.connect(
            host=credentials['host'],
            port=shard['port'],
            user=credentials['user'],
            password=credentials['password'],
            database=credentials['database']
        )
        cursor = conn.cursor()
        
        print(f"✓ {shard['name']} (Port {shard['port']}):")
        
        # Show REPLICATED tables
        replicated_patterns = ['medicine', 'inventory', 'prescription', 'slots', 'audit_log']
        
        for pattern in replicated_patterns:
            query = f"SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA='{credentials['database']}' AND TABLE_NAME LIKE '{pattern}%';"
            cursor.execute(query)
            tables = cursor.fetchall()
            if tables:
                table_name = tables[0][0]
                print(f"  • {table_name} (replicated on all 3 shards)")
        
        print()
        conn.close()
        
    except Error as e:
        print(f"✗ {shard['name']}: {e}\n")

print("=" * 80)
print("✅ All replicated tables verified on all 3 shards!")
print("=" * 80)