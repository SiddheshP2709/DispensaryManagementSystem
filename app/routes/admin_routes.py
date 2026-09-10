import bcrypt
from flask import Blueprint, jsonify, request
try:
    from ..db import get_db_connection, get_sharded_db_layer
    from ..auth import admin_required
    from ..logger import log_action
    from ..validators import (
        ALLOWED_GENDERS,
        ALLOWED_MEMBER_TYPES,
        ALLOWED_ROLES,
        ALLOWED_SHIFTS,
        clean_string,
        validate_age,
        validate_email,
        validate_non_negative_int,
        validate_password,
        validate_phone,
        validate_username,
    )
except ImportError:
    from db import get_db_connection, get_sharded_db_layer
    from auth import admin_required
    from logger import log_action
    from validators import (
        ALLOWED_GENDERS,
        ALLOWED_MEMBER_TYPES,
        ALLOWED_ROLES,
        ALLOWED_SHIFTS,
        clean_string,
        validate_age,
        validate_email,
        validate_non_negative_int,
        validate_password,
        validate_phone,
        validate_username,
    )

admin_bp = Blueprint('admin', __name__)


def _group_name_for(member_type):
    return member_type + 's' if not member_type.endswith('s') else member_type


def _validate_member_payload(data):
    name = clean_string(data.get('name'))
    email = clean_string(data.get('email'))
    contact_no = clean_string(data.get('contact_no'))
    username = clean_string(data.get('username'))
    password = data.get('password')
    member_type = clean_string(data.get('member_type'))
    role = clean_string(data.get('role'))

    if not all([name, data.get('age'), email, contact_no, member_type, username, password, role]):
        return "Missing required fields"
    if not validate_age(data.get('age')):
        return "Age must be between 1 and 120"
    if not validate_email(email):
        return "Enter a valid email address"
    if not validate_phone(contact_no):
        return "Enter a valid contact number"
    if not validate_username(username):
        return "Username must be 3-30 characters and use only letters, numbers, or underscore"
    if not validate_password(password):
        return "Password must be at least 8 characters and contain letters and numbers"
    if member_type not in ALLOWED_MEMBER_TYPES:
        return "Invalid member type"
    if role not in ALLOWED_ROLES:
        return "Invalid system role"

    if member_type == 'Doctor':
        if not all([
            clean_string(data.get('specialization')),
            clean_string(data.get('qualification')),
            clean_string(data.get('shift')),
        ]):
            return "Doctor specialization, qualification, and shift are required"
        if data.get('shift') not in ALLOWED_SHIFTS:
            return "Doctor shift must be Morning, Evening, or Night"
        if not validate_non_negative_int(data.get('consultation_fee')):
            return "Consultation fee must be a non-negative number"
        if not validate_non_negative_int(data.get('salary')):
            return "Salary must be a non-negative number"

    if member_type == 'Patient':
        if clean_string(data.get('gender', 'Other')) not in ALLOWED_GENDERS:
            return "Patient gender must be Male, Female, or Other"
        if not clean_string(data.get('address')):
            return "Patient address is required"

    if member_type == 'Staff':
        if not clean_string(data.get('staff_role')):
            return "Staff role is required"
        if clean_string(data.get('shift')) not in ALLOWED_SHIFTS:
            return "Staff shift must be Morning, Evening, or Night"
        if not validate_non_negative_int(data.get('salary')):
            return "Salary must be a non-negative number"

    return None


def _insert_member_subtype(cursor, member_type, member_id, data):
    if member_type == 'Doctor':
        cursor.execute(
            """
            INSERT INTO doctor (specialization, qualification, consultation_fee, salary, shift, member_id)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                clean_string(data.get('specialization')),
                clean_string(data.get('qualification')),
                int(data.get('consultation_fee')),
                int(data.get('salary')),
                clean_string(data.get('shift')),
                member_id,
            )
        )
    elif member_type == 'Patient':
        cursor.execute(
            """
            INSERT INTO patient (blood_group, gender, address, member_id)
            VALUES (%s, %s, %s, %s)
            """,
            (
                clean_string(data.get('blood_group', 'Unknown')) or 'Unknown',
                clean_string(data.get('gender', 'Other')) or 'Other',
                clean_string(data.get('address')),
                member_id,
            )
        )
    elif member_type == 'Staff':
        cursor.execute(
            """
            INSERT INTO nonmedicalstaff (role, salary, shift, member_id)
            VALUES (%s, %s, %s, %s)
            """,
            (
                clean_string(data.get('staff_role')),
                int(data.get('salary')),
                clean_string(data.get('shift')),
                member_id,
            )
        )


@admin_bp.route('/add_member', methods=['POST'])
@admin_required
def add_member():
    data = request.get_json() or {}
    validation_error = _validate_member_payload(data)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    name = clean_string(data.get('name'))
    username = clean_string(data.get('username'))
    member_type = clean_string(data.get('member_type'))
    role = clean_string(data.get('role'))
    age = int(data.get('age'))
    email = clean_string(data.get('email'))
    contact_no = clean_string(data.get('contact_no'))
    password = data.get('password')

    # HYBRID: Insert to LOCAL DB first, then route sharded data to remote shards
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Step 1: Insert to LOCAL DB (member + users)
        cursor.execute(
            "INSERT INTO member (name, age, email, contact_no, image, member_type) VALUES (%s, %s, %s, %s, %s, %s)",
            (name, age, email, contact_no, '', member_type)
        )
        conn.commit()
        member_id = cursor.lastrowid
        
        # Insert user to LOCAL DB
        cursor.execute(
            "INSERT INTO users (member_id, username, password_hash, role) VALUES (%s, %s, %s, %s)",
            (member_id, username, password_hash, role)
        )
        conn.commit()
        
        # Step 2: Route sharded data to REMOTE SHARDS
        try:
            from ..sharding import get_shard_connection, get_shard_table_name, get_shard_id
            from ..config import get_shard_settings
        except ImportError:
            from sharding import get_shard_connection, get_shard_table_name, get_shard_id
            from config import get_shard_settings
        
        shard_id = get_shard_id(member_id)
        settings = get_shard_settings()
        shard_conn = get_shard_connection(shard_id, settings["user"], settings["password"], settings["database"])
        shard_cursor = shard_conn.cursor()
        
        # Insert member to shard
        shard_cursor.execute(f"""
            INSERT INTO {get_shard_table_name('member', shard_id)} 
            (member_id, name, age, email, contact_no, image, member_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (member_id, name, age, email, contact_no, '', member_type))
        shard_conn.commit()
        
        # Insert user to shard
        shard_cursor.execute(f"""
            INSERT INTO {get_shard_table_name('users', shard_id)} 
            (member_id, username, password_hash, role)
            VALUES (%s, %s, %s, %s)
        """, (member_id, username, password_hash, role))
        shard_conn.commit()
        
        # Add member-specific sharded data
        if member_type == 'Doctor':
            shard_cursor.execute(f"""
                INSERT INTO {get_shard_table_name('doctor', shard_id)} 
                (specialization, qualification, consultation_fee, salary, shift, member_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                clean_string(data.get('specialization')),
                clean_string(data.get('qualification')),
                int(data.get('consultation_fee')),
                int(data.get('salary')),
                clean_string(data.get('shift')),
                member_id
            ))
        elif member_type == 'Patient':
            shard_cursor.execute(f"""
                INSERT INTO {get_shard_table_name('patient', shard_id)} 
                (blood_group, gender, address, member_id)
                VALUES (%s, %s, %s, %s)
            """, (
                clean_string(data.get('blood_group', 'Unknown')) or 'Unknown',
                clean_string(data.get('gender', 'Other')) or 'Other',
                clean_string(data.get('address')),
                member_id
            ))
        elif member_type == 'Staff':
            shard_cursor.execute(f"""
                INSERT INTO {get_shard_table_name('nonmedicalstaff', shard_id)} 
                (role, salary, shift, member_id)
                VALUES (%s, %s, %s, %s)
            """, (
                clean_string(data.get('staff_role')),
                int(data.get('salary')),
                clean_string(data.get('shift')),
                member_id
            ))
        
        shard_conn.commit()
        shard_cursor.close()
        shard_conn.close()
        
        log_action(request.user['username'], f"CREATED MEMBER (username: {username}, type: {member_type}, role: {role})")
        return jsonify({"message": "Member created successfully (hybrid: local + sharded)", "member_id": member_id}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to create member: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/delete_member/<int:id>', methods=['DELETE'])
@admin_required
def delete_member(id):
    # HYBRID: Delete from LOCAL DB first, then from REMOTE SHARDS
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Step 1: Get member info from LOCAL DB
        cursor.execute("SELECT member_id, name, member_type FROM member WHERE member_id = %s", (id,))
        member = cursor.fetchone()
        if not member:
            return jsonify({"error": "Member not found"}), 404

        # Delete related appointments from LOCAL DB
        patient_id = None
        doctor_id = None
        if member['member_type'] == 'Patient':
            cursor.execute("SELECT patient_id FROM patient WHERE member_id = %s", (id,))
            patient = cursor.fetchone()
            patient_id = patient['patient_id'] if patient else None
        elif member['member_type'] == 'Doctor':
            cursor.execute("SELECT doctor_id FROM doctor WHERE member_id = %s", (id,))
            doctor = cursor.fetchone()
            doctor_id = doctor['doctor_id'] if doctor else None

        cursor2 = conn.cursor()
        if patient_id is not None:
            cursor2.execute("DELETE FROM appointment WHERE patient_id = %s", (patient_id,))
        if doctor_id is not None:
            cursor2.execute("DELETE FROM appointment WHERE doctor_id = %s", (doctor_id,))
        cursor.execute("DELETE FROM users WHERE member_id = %s", (id,))
        cursor.execute("DELETE FROM member WHERE member_id = %s", (id,))
        conn.commit()
        cursor2.close()
        
        # Step 2: Delete from REMOTE SHARDS
        try:
            from ..sharding import get_shard_connection, get_shard_table_name, get_shard_id
            from ..config import get_shard_settings
        except ImportError:
            from sharding import get_shard_connection, get_shard_table_name, get_shard_id
            from config import get_shard_settings
        
        shard_id = get_shard_id(id)
        settings = get_shard_settings()
        shard_conn = get_shard_connection(shard_id, settings["user"], settings["password"], settings["database"])
        shard_cursor = shard_conn.cursor()
        
        # Delete from shards
        shard_cursor.execute(f"DELETE FROM {get_shard_table_name('appointment', shard_id)} WHERE patient_id = %s", (patient_id,))
        shard_cursor.execute(f"DELETE FROM {get_shard_table_name('appointment', shard_id)} WHERE doctor_id = %s", (doctor_id,))
        shard_cursor.execute(f"DELETE FROM {get_shard_table_name('users', shard_id)} WHERE member_id = %s", (id,))
        shard_cursor.execute(f"DELETE FROM {get_shard_table_name('member', shard_id)} WHERE member_id = %s", (id,))
        shard_conn.commit()
        shard_cursor.close()
        shard_conn.close()
        
        log_action(request.user['username'], f"DELETED MEMBER {id} (name: {member['name']})")
        return jsonify({"message": f"Member {id} deleted from local and sharded DBs"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Deletion failed: {str(e)}"}), 400
    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/members', methods=['GET'])
@admin_required
def list_members():
    sharded_db = get_sharded_db_layer()
    members = sharded_db.get_all_members()
    return jsonify({"members": members}), 200
