#!/usr/bin/env python3
from app.sharded_db import ShardedDBLayer
from app.config import get_shard_settings

settings = get_shard_settings()
db = ShardedDBLayer(settings['user'], settings['password'], settings['database'])
meds = db.get_all_medicines()
print(f'Got {len(meds)} medicines')
if meds:
    med = meds[0]
    print(f'Sample medicine: id={med.get("medicine_id")}, name={med.get("medicine_name")}, quantity={med.get("quantity")}, expiry={med.get("expiry_date")}')
    print(f'Keys: {list(med.keys())}')
