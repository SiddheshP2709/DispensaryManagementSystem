#!/usr/bin/env python3
"""
Seed test medicines into sharded database
Run: python seed_medicines.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import get_shard_settings
from app.sharding import get_shard_connection, get_shard_table_name, NUM_SHARDS


def seed_medicines():
    """Add test medicines to Shard 0 (replicated across all shards)."""
    
    test_medicines = [
        ('Aspirin', 'Bayer', 100, 'Painkiller', 500, '2024-01-01', '2026-12-31'),
        ('Ibuprofen', 'Advil', 150, 'Painkiller', 300, '2024-02-01', '2026-11-30'),
        ('Amoxicillin', 'GlaxoSmithKline', 200, 'Antibiotic', 250, '2024-03-01', '2026-09-30'),
        ('Vitamin C', 'Nature Made', 50, 'Supplement', 1000, '2024-01-15', '2027-01-15'),
        ('Paracetamol', 'Calpol', 120, 'Painkiller', 600, '2024-02-15', '2026-10-15'),
        ('Metformin', 'Generics', 180, 'Diabetes', 400, '2024-04-01', '2026-08-01'),
        ('Lisinopril', 'Generics', 220, 'Blood Pressure', 350, '2024-03-15', '2026-09-15'),
        ('Atorvastatin', 'Pfizer', 250, 'Cholesterol', 200, '2024-05-01', '2026-07-01'),
        ('Omeprazole', 'AstraZeneca', 140, 'Acid Reflux', 450, '2024-02-20', '2026-11-20'),
        ('Cetirizine', 'UCB', 80, 'Allergy', 800, '2024-03-10', '2026-12-10'),
    ]
    
    shard_config = get_shard_settings()
    shard_user = shard_config["user"]
    shard_password = shard_config["password"]
    shard_db = shard_config["database"]
    
    print("=" * 60)
    print("Seeding Test Medicines")
    print("=" * 60)
    
    # Add to Shard 0 (replicated, so all shards get it)
    try:
        conn = get_shard_connection(0, shard_user, shard_password, shard_db)
        cursor = conn.cursor()
        
        for med in test_medicines:
            medicine_name, manufacturer, price, category, quantity, mfg_date, exp_date = med
            
            cursor.execute(f"""
                INSERT INTO {get_shard_table_name('medicine', 0)}
                (medicine_name, manufacturer, price, category, manufacturing_date, expiry_date)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (medicine_name, manufacturer, price, category, mfg_date, exp_date))
            
            print(f"  ✅ Added: {medicine_name}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Successfully seeded 10 medicines!")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error seeding medicines: {str(e)}")
        return False
    
    return True


if __name__ == '__main__':
    seed_medicines()
