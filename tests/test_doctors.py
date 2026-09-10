#!/usr/bin/env python3
import sys
sys.path.insert(0, '.')
from app.sharded_db import ShardedDBLayer
from app.config import get_shard_settings

settings = get_shard_settings()
db = ShardedDBLayer(settings['user'], settings['password'], settings['database'])
doctors = db.get_all_doctors()
print(f'Retrieved {len(doctors)} doctors')
if doctors:
    doc = doctors[0]
    print(f'Sample doctor: doctor_id={doc.get("doctor_id")}, doctor_name={doc.get("doctor_name")}, specialization={doc.get("specialization")}')
    print(f'Keys in doctor: {list(doc.keys())}')

