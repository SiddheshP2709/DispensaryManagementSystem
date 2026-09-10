import mysql.connector
import hashlib
from mysql.connector import Error

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

patient_id = 1
md5_hash = hashlib.md5(str(patient_id).encode()).hexdigest()
shard_id = int(md5_hash, 16) % 3

print('\n' + '=' * 90)
print('PART 2: QUERY ROUTING TO CORRECT SHARD')
print('=' * 90)
print(f'Patient ID: {patient_id} is on SHARD {shard_id}')

try:
    shard = shards[shard_id]
    conn = mysql.connector.connect(host=credentials['host'], port=shard['port'], user=credentials['user'], password=credentials['password'], database=credentials['database'])
    cursor = conn.cursor()
    cursor.execute(f'SELECT member_id, name FROM shard_{shard_id}_member WHERE member_id = {patient_id}')
    member = cursor.fetchone()
    if member:
        print(f'Found patient: {member[1]} on ' + shard['name'])
        query = f'SELECT a.appointment_id, a.appointment_date, m_d.name FROM shard_{shard_id}_appointment a JOIN shard_{shard_id}_doctor d ON a.doctor_id = d.doctor_id JOIN shard_{shard_id}_member m_d ON d.member_id = m_d.member_id WHERE a.patient_member_id = {patient_id}'
        cursor.execute(query)
        for appt in cursor.fetchall():
            print(f' - Appointment {appt[0]}: {appt[1]} with Dr. {appt[2]}')
    conn.close()
except Error as e:
    print(f'Error: {e}')

print('\n' + '=' * 90)
print('OTHER SHARDS UNAFFECTED')
