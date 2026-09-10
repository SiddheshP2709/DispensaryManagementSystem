"""
Sharding module for distributed database management.

Strategy: Hash-based sharding using member_id
Shards: 3 shards (0, 1, 2) distributed across 10.0.116.184:3307, :3308, :3309

Shard Key: member_id
Partition Function: shard_id = hash(member_id) % num_shards
"""

import mysql.connector
from mysql.connector import Error
import hashlib
import json

# Shard configuration
SHARD_CONFIG = {
    0: {"host": "10.0.116.184", "port": 3307},
    1: {"host": "10.0.116.184", "port": 3308},
    2: {"host": "10.0.116.184", "port": 3309},
}

NUM_SHARDS = 3


def get_shard_id(member_id):
    """
    Calculate shard ID using hash-based partitioning.
    
    Args:
        member_id: The member ID to hash
        
    Returns:
        Shard ID (0, 1, or 2)
    """
    hash_value = int(hashlib.md5(str(member_id).encode()).hexdigest(), 16)
    return hash_value % NUM_SHARDS


def get_shard_connection(shard_id, username, password, database):
    """
    Get a connection to a specific shard.
    
    Args:
        shard_id: Shard number (0, 1, 2)
        username: MySQL username
        password: MySQL password
        database: Database name
        
    Returns:
        MySQL connection object
    """
    if shard_id not in SHARD_CONFIG:
        raise ValueError(f"Invalid shard_id: {shard_id}")
    
    config = SHARD_CONFIG[shard_id]
    try:
        conn = mysql.connector.connect(
            host=config["host"],
            port=config["port"],
            user=username,
            password=password,
            database=database
        )
        return conn
    except Error as e:
        raise Exception(f"Failed to connect to shard {shard_id}: {str(e)}")


def get_shard_table_name(base_name, shard_id):
    """
    Generate sharded table name.
    
    Args:
        base_name: Original table name (e.g., 'member')
        shard_id: Shard number
        
    Returns:
        Sharded table name (e.g., 'shard_0_member')
    """
    return f"shard_{shard_id}_{base_name}"


def create_sharded_schema(username, password, database):
    """
    Create schema on all shards with sharded table names.
    
    Args:
        username: MySQL username
        password: MySQL password
        database: Database name
    """
    # Table creation DDL for each shard
    for shard_id in range(NUM_SHARDS):
        conn = get_shard_connection(shard_id, username, password, database)
        cursor = conn.cursor()
        
        try:
            # Create member table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('member', shard_id)} (
                    member_id INT NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    age INT NOT NULL,
                    email VARCHAR(150) NOT NULL,
                    contact_no VARCHAR(15) NOT NULL,
                    image VARCHAR(500) NOT NULL,
                    member_type VARCHAR(50) NOT NULL,
                    PRIMARY KEY (member_id),
                    UNIQUE KEY email (email),
                    CHECK (age > 0)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create users table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('users', shard_id)} (
                    user_id INT NOT NULL AUTO_INCREMENT,
                    member_id INT,
                    username VARCHAR(100),
                    password_hash VARCHAR(255),
                    role VARCHAR(20),
                    PRIMARY KEY (user_id),
                    UNIQUE KEY username (username),
                    KEY member_id (member_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create doctor table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('doctor', shard_id)} (
                    doctor_id INT NOT NULL AUTO_INCREMENT,
                    specialization VARCHAR(100) NOT NULL,
                    qualification VARCHAR(100) NOT NULL,
                    consultation_fee INT NOT NULL,
                    salary INT NOT NULL,
                    shift VARCHAR(50) NOT NULL,
                    member_id INT NOT NULL,
                    PRIMARY KEY (doctor_id),
                    UNIQUE KEY member_id (member_id),
                    CHECK (consultation_fee >= 0),
                    CHECK (salary >= 0)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create patient table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('patient', shard_id)} (
                    patient_id INT NOT NULL AUTO_INCREMENT,
                    blood_group VARCHAR(5) NOT NULL,
                    gender VARCHAR(10) NOT NULL,
                    address VARCHAR(255) NOT NULL,
                    member_id INT NOT NULL,
                    PRIMARY KEY (patient_id),
                    UNIQUE KEY member_id (member_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create nonmedicalstaff table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('nonmedicalstaff', shard_id)} (
                    staff_id INT NOT NULL AUTO_INCREMENT,
                    role VARCHAR(100) NOT NULL,
                    salary INT NOT NULL,
                    shift VARCHAR(50) NOT NULL,
                    member_id INT NOT NULL,
                    PRIMARY KEY (staff_id),
                    UNIQUE KEY member_id (member_id),
                    CHECK (salary >= 0)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create medicine table (not sharded by member_id, replicated across shards)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('medicine', shard_id)} (
                    medicine_id INT NOT NULL AUTO_INCREMENT,
                    medicine_name VARCHAR(150) NOT NULL,
                    manufacturer VARCHAR(150) NOT NULL,
                    price INT NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    PRIMARY KEY (medicine_id),
                    CHECK (price >= 0)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create slots table (replicated, for cross-shard appointment routing)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('slots', shard_id)} (
                    slot_id INT NOT NULL AUTO_INCREMENT,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'Available',
                    doctor_id INT NOT NULL,
                    PRIMARY KEY (slot_id),
                    CHECK (end_time > start_time)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create appointment table (sharded by patient's member_id)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('appointment', shard_id)} (
                    appointment_id INT NOT NULL AUTO_INCREMENT,
                    appointment_date DATE NOT NULL,
                    appointment_time TIME NOT NULL,
                    doctor_id INT NOT NULL,
                    patient_id INT NOT NULL,
                    slot_id INT NOT NULL,
                    patient_member_id INT NOT NULL,
                    PRIMARY KEY (appointment_id),
                    UNIQUE KEY uq_appointment_doctor_date_slot (doctor_id, appointment_date, slot_id),
                    UNIQUE KEY uq_appointment_doctor_date_time (doctor_id, appointment_date, appointment_time),
                    KEY idx_patient_member_id (patient_member_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create inventory table (replicated)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('inventory', shard_id)} (
                    inventory_id INT NOT NULL AUTO_INCREMENT,
                    manufacturing_date DATE NOT NULL,
                    expiry_date DATE NOT NULL,
                    quantity INT NOT NULL,
                    medicine_id INT NOT NULL,
                    PRIMARY KEY (inventory_id),
                    KEY medicine_id (medicine_id),
                    CHECK (quantity >= 0),
                    CHECK (expiry_date > manufacturing_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create prescription table (replicated)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('prescription', shard_id)} (
                    prescription_id INT NOT NULL AUTO_INCREMENT,
                    appointment_id INT NOT NULL,
                    PRIMARY KEY (prescription_id),
                    UNIQUE KEY appointment_id (appointment_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create prescription_details table (replicated)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('prescription_details', shard_id)} (
                    prescription_id INT NOT NULL,
                    medicine_id INT NOT NULL,
                    dosage VARCHAR(100) NOT NULL,
                    duration INT NOT NULL,
                    PRIMARY KEY (prescription_id, medicine_id),
                    KEY medicine_id (medicine_id),
                    CHECK (duration > 0)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create member_group_mapping table
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('member_group_mapping', shard_id)} (
                    mapping_id INT NOT NULL AUTO_INCREMENT,
                    member_id INT NOT NULL,
                    group_name VARCHAR(100) NOT NULL,
                    assigned_role VARCHAR(50) NOT NULL,
                    PRIMARY KEY (mapping_id),
                    KEY idx_mgm_member_id (member_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            # Create audit_log table (replicated)
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {get_shard_table_name('audit_log', shard_id)} (
                    audit_id INT NOT NULL AUTO_INCREMENT,
                    username VARCHAR(100) NOT NULL,
                    action VARCHAR(255) NOT NULL,
                    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (audit_id),
                    KEY idx_audit_created_at (created_at)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci
            """)
            
            conn.commit()
            print(f"✓ Schema created on shard {shard_id}")
            
        except Error as e:
            print(f"✗ Error creating schema on shard {shard_id}: {str(e)}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()


def migrate_data_to_shards(source_conn, username, password, database):
    """
    Migrate data from source database to sharded tables.
    
    Args:
        source_conn: Connection to source database
        username: MySQL username for shards
        password: MySQL password for shards
        database: Database name
    """
    source_cursor = source_conn.cursor(dictionary=True)
    
    try:
        # Migrate member data
        source_cursor.execute("SELECT * FROM member")
        members = source_cursor.fetchall()
        
        for member in members:
            shard_id = get_shard_id(member['member_id'])
            shard_conn = get_shard_connection(shard_id, username, password, database)
            shard_cursor = shard_conn.cursor()
            
            try:
                shard_cursor.execute(f"""
                    INSERT INTO {get_shard_table_name('member', shard_id)} 
                    (member_id, name, age, email, contact_no, image, member_type)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    member['member_id'], member['name'], member['age'],
                    member['email'], member['contact_no'], member['image'],
                    member['member_type']
                ))
                shard_conn.commit()
            except Error as e:
                print(f"Warning: Could not insert member {member['member_id']}: {str(e)}")
                shard_conn.rollback()
            finally:
                shard_cursor.close()
                shard_conn.close()
        
        # Migrate users data
        source_cursor.execute("SELECT * FROM users")
        users = source_cursor.fetchall()
        
        for user in users:
            shard_id = get_shard_id(user['member_id']) if user['member_id'] else 0
            shard_conn = get_shard_connection(shard_id, username, password, database)
            shard_cursor = shard_conn.cursor()
            
            try:
                shard_cursor.execute(f"""
                    INSERT INTO {get_shard_table_name('users', shard_id)} 
                    (user_id, member_id, username, password_hash, role)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user['user_id'], user['member_id'], user['username'], 
                      user['password_hash'], user['role']))
                shard_conn.commit()
            except Error as e:
                print(f"Warning: Could not insert user {user['user_id']}: {str(e)}")
                shard_conn.rollback()
            finally:
                shard_cursor.close()
                shard_conn.close()
        
        # Migrate doctor data
        source_cursor.execute("SELECT * FROM doctor")
        doctors = source_cursor.fetchall()
        
        for doctor in doctors:
            shard_id = get_shard_id(doctor['member_id'])
            shard_conn = get_shard_connection(shard_id, username, password, database)
            shard_cursor = shard_conn.cursor()
            
            try:
                shard_cursor.execute(f"""
                    INSERT INTO {get_shard_table_name('doctor', shard_id)} 
                    (doctor_id, specialization, qualification, consultation_fee, salary, shift, member_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (doctor['doctor_id'], doctor['specialization'], doctor['qualification'],
                      doctor['consultation_fee'], doctor['salary'], doctor['shift'], doctor['member_id']))
                shard_conn.commit()
            except Error as e:
                print(f"Warning: Could not insert doctor {doctor['doctor_id']}: {str(e)}")
                shard_conn.rollback()
            finally:
                shard_cursor.close()
                shard_conn.close()
        
        # Migrate patient data
        source_cursor.execute("SELECT * FROM patient")
        patients = source_cursor.fetchall()
        
        for patient in patients:
            shard_id = get_shard_id(patient['member_id'])
            shard_conn = get_shard_connection(shard_id, username, password, database)
            shard_cursor = shard_conn.cursor()
            
            try:
                shard_cursor.execute(f"""
                    INSERT INTO {get_shard_table_name('patient', shard_id)} 
                    (patient_id, blood_group, gender, address, member_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (patient['patient_id'], patient['blood_group'], patient['gender'],
                      patient['address'], patient['member_id']))
                shard_conn.commit()
            except Error as e:
                print(f"Warning: Could not insert patient {patient['patient_id']}: {str(e)}")
                shard_conn.rollback()
            finally:
                shard_cursor.close()
                shard_conn.close()
        
        # Migrate nonmedicalstaff data
        source_cursor.execute("SELECT * FROM nonmedicalstaff")
        staff = source_cursor.fetchall()
        
        for s in staff:
            shard_id = get_shard_id(s['member_id'])
            shard_conn = get_shard_connection(shard_id, username, password, database)
            shard_cursor = shard_conn.cursor()
            
            try:
                shard_cursor.execute(f"""
                    INSERT INTO {get_shard_table_name('nonmedicalstaff', shard_id)} 
                    (staff_id, role, salary, shift, member_id)
                    VALUES (%s, %s, %s, %s, %s)
                """, (s['staff_id'], s['role'], s['salary'], s['shift'], s['member_id']))
                shard_conn.commit()
            except Error as e:
                print(f"Warning: Could not insert staff {s['staff_id']}: {str(e)}")
                shard_conn.rollback()
            finally:
                shard_cursor.close()
                shard_conn.close()
        
        # Migrate member_group_mapping
        source_cursor.execute("SELECT * FROM member_group_mapping")
        mappings = source_cursor.fetchall()
        
        for mapping in mappings:
            shard_id = get_shard_id(mapping['member_id'])
            shard_conn = get_shard_connection(shard_id, username, password, database)
            shard_cursor = shard_conn.cursor()
            
            try:
                shard_cursor.execute(f"""
                    INSERT INTO {get_shard_table_name('member_group_mapping', shard_id)} 
                    (mapping_id, member_id, group_name, assigned_role)
                    VALUES (%s, %s, %s, %s)
                """, (mapping['mapping_id'], mapping['member_id'], mapping['group_name'],
                      mapping['assigned_role']))
                shard_conn.commit()
            except Error as e:
                shard_conn.rollback()
            finally:
                shard_cursor.close()
                shard_conn.close()
        
        # Migrate appointment data (routed by patient's member_id)
        source_cursor.execute("""
            SELECT a.*, p.member_id as patient_member_id 
            FROM appointment a 
            JOIN patient p ON a.patient_id = p.patient_id
        """)
        appointments = source_cursor.fetchall()
        
        for appt in appointments:
            shard_id = get_shard_id(appt['patient_member_id'])
            shard_conn = get_shard_connection(shard_id, username, password, database)
            shard_cursor = shard_conn.cursor()
            
            try:
                shard_cursor.execute(f"""
                    INSERT INTO {get_shard_table_name('appointment', shard_id)} 
                    (appointment_id, appointment_date, appointment_time, doctor_id, patient_id, slot_id, patient_member_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (appt['appointment_id'], appt['appointment_date'], appt['appointment_time'],
                      appt['doctor_id'], appt['patient_id'], appt['slot_id'], appt['patient_member_id']))
                shard_conn.commit()
            except Error as e:
                print(f"Warning: Could not insert appointment {appt['appointment_id']}: {str(e)}")
                shard_conn.rollback()
            finally:
                shard_cursor.close()
                shard_conn.close()
        
        print("✓ Data migration completed")
        
    finally:
        source_cursor.close()


def verify_sharding(username, password, database):
    """
    Verify that data is properly distributed across shards.
    
    Args:
        username: MySQL username
        password: MySQL password
        database: Database name
        
    Returns:
        Dictionary with shard statistics
    """
    stats = {}
    
    for shard_id in range(NUM_SHARDS):
        try:
            shard_conn = get_shard_connection(shard_id, username, password, database)
            shard_cursor = shard_conn.cursor()
            
            # Count records in each sharded table
            counts = {}
            tables = ['member', 'doctor', 'patient', 'nonmedicalstaff', 'users', 'appointment']
            
            for table in tables:
                try:
                    shard_cursor.execute(f"SELECT COUNT(*) as cnt FROM {get_shard_table_name(table, shard_id)}")
                    count = shard_cursor.fetchone()[0]
                    counts[table] = count
                except:
                    counts[table] = 0
            
            stats[f"shard_{shard_id}"] = counts
            shard_cursor.close()
            shard_conn.close()
        except Exception as e:
            print(f"Error verifying shard {shard_id}: {str(e)}")
    
    return stats
