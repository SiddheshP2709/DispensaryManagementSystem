#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from app.sharded_db import ShardedDBLayer
from app.config import get_shard_settings

settings = get_shard_settings()
db = ShardedDBLayer(settings['user'], settings['password'], settings['database'])

# Test getting appointments with doctor names
from app.sharding import NUM_SHARDS, get_shard_connection, get_shard_table_name

appointments = []
for shard_id in range(NUM_SHARDS):
    try:
        conn = get_shard_connection(shard_id, settings['user'], settings['password'], settings['database'])
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"""
            SELECT 
                a.appointment_id, a.appointment_date, a.appointment_time,
                a.doctor_id, a.patient_id, a.slot_id,
                p.member_id as patient_member_id,
                pm.name as patient_name
            FROM {get_shard_table_name('appointment', shard_id)} a
            LEFT JOIN {get_shard_table_name('patient', shard_id)} p ON a.patient_id = p.patient_id
            LEFT JOIN {get_shard_table_name('member', shard_id)} pm ON p.member_id = pm.member_id
            LIMIT 1
        """)
        shard_appointments = cursor.fetchall()
        appointments.extend(shard_appointments)
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error from shard {shard_id}: {e}")

print(f'Retrieved {len(appointments)} appointments')
if appointments:
    appt = appointments[0]
    print(f'Sample appointment:')
    print(f'  appointment_id={appt.get("appointment_id")}')
    print(f'  doctor_id={appt.get("doctor_id")}')
    print(f'  patient_id={appt.get("patient_id")}')
    print(f'  patient_name={appt.get("patient_name")}')
    print(f'  appointment_date={appt.get("appointment_date")}')
    print(f'  appointment_time={appt.get("appointment_time")}')
