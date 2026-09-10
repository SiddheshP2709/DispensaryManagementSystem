import datetime
from flask import Blueprint, jsonify, request
try:
    from ..db import get_db_connection, get_sharded_db_layer
    from ..auth import token_required
    from ..logger import log_action
except ImportError:
    from db import get_db_connection, get_sharded_db_layer
    from auth import token_required
    from logger import log_action

patient_bp = Blueprint('patient', __name__)


def _serialize_time_rows(rows, date_keys=None, time_keys=None):
    date_keys = date_keys or []
    time_keys = time_keys or []
    for row in rows:
        for key in date_keys:
            if row.get(key) and hasattr(row[key], 'isoformat'):
                row[key] = row[key].isoformat()
        for key in time_keys:
            if row.get(key) and hasattr(row[key], 'seconds'):
                total = row[key].seconds
                row[key] = f"{total//3600:02d}:{(total%3600)//60:02d}"


@patient_bp.route('/doctors', methods=['GET'])
@token_required
def get_doctors():
    sharded_db = get_sharded_db_layer()
    doctors = sharded_db.get_all_doctors()
    return jsonify({"doctors": doctors}), 200


@patient_bp.route('/slots/<int:doctor_id>', methods=['GET'])
@token_required
def get_slots(doctor_id):
    # For sharded architecture, return empty slots
    # In production, would query sharded slots table
    return jsonify({"slots": []}), 200


@patient_bp.route('/doctor/slots', methods=['GET'])
@token_required
def get_my_doctor_slots():
    if request.user.get('member_type') != 'Doctor':
        log_action(request.user['username'], "UNAUTHORIZED ACCESS ATTEMPT: Doctor slots")
        return jsonify({"error": "Access denied"}), 403

    # For sharded architecture, return empty slots
    return jsonify({"slots": []}), 200


@patient_bp.route('/doctor/appointments', methods=['GET'])
@token_required
def doctor_appointments():
    if request.user.get('member_type') != 'Doctor':
        log_action(request.user['username'], "UNAUTHORIZED ACCESS ATTEMPT: Doctor appointments")
        return jsonify({"error": "Access denied"}), 403

    selected_date = request.args.get('date') or datetime.date.today().isoformat()

    # For sharded architecture, return empty appointments
    return jsonify({"appointments": [], "date": selected_date}), 200


@patient_bp.route('/doctor/patients', methods=['GET'])
@token_required
def doctor_patients():
    if request.user.get('member_type') != 'Doctor':
        log_action(request.user['username'], "UNAUTHORIZED ACCESS ATTEMPT: Doctor patients")
        return jsonify({"error": "Access denied"}), 403

    # For sharded architecture, return empty patients list
    return jsonify({"patients": []}), 200


@patient_bp.route('/my_appointments', methods=['GET'])
@token_required
def my_appointments():
    """Get current user's appointments (for patients) with doctor names."""
    try:
        # Get user info from token
        member_id = request.user.get('member_id')
        member_type = request.user.get('member_type')
        
        if member_type != 'Patient':
            return jsonify({"error": "Only patients can view their appointments"}), 403
        
        sharded_db = get_sharded_db_layer()
        
        # Get patient_id from member_id
        patient_info = sharded_db.get_patient_by_member_id(member_id)
        if not patient_info:
            return jsonify({"appointments": []}), 200
        
        patient_id = patient_info.get('patient_id')
        
        # Get all appointments and filter for this patient
        from ..sharding import NUM_SHARDS, get_shard_connection, get_shard_table_name
        from ..config import get_shard_settings
        
        settings = get_shard_settings()
        appointments = []
        
        # Get appointments from all shards where this patient is the patient_id
        for shard_id in range(NUM_SHARDS):
            try:
                conn = get_shard_connection(shard_id, settings["user"], settings["password"], settings["database"])
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"""
                    SELECT 
                        a.appointment_id, a.appointment_date, a.appointment_time,
                        a.doctor_id, a.patient_id, a.slot_id
                    FROM {get_shard_table_name('appointment', shard_id)} a
                    WHERE a.patient_id = %s
                """, (patient_id,))
                shard_appointments = cursor.fetchall()
                appointments.extend(shard_appointments)
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Warning: Error fetching appointments from shard {shard_id}: {str(e)}")
        
        # Look up doctor names for each appointment
        for appt in appointments:
            if appt.get('doctor_id'):
                try:
                    # Search for doctor in all shards
                    for search_shard_id in range(NUM_SHARDS):
                        try:
                            search_conn = get_shard_connection(
                                search_shard_id,
                                settings["user"],
                                settings["password"],
                                settings["database"]
                            )
                            search_cursor = search_conn.cursor(dictionary=True)
                            search_cursor.execute(f"""
                                SELECT 
                                    d.doctor_id, d.member_id,
                                    m.name as doctor_name
                                FROM {get_shard_table_name('doctor', search_shard_id)} d
                                LEFT JOIN {get_shard_table_name('member', search_shard_id)} m ON d.member_id = m.member_id
                                WHERE d.doctor_id = %s
                            """, (appt['doctor_id'],))
                            doctor = search_cursor.fetchone()
                            search_cursor.close()
                            search_conn.close()
                            
                            if doctor and doctor.get('doctor_name'):
                                appt['doctor_name'] = doctor['doctor_name']
                                break
                        except:
                            pass
                    
                    if not appt.get('doctor_name'):
                        appt['doctor_name'] = f"Doctor ID {appt['doctor_id']}"
                except Exception as e:
                    print(f"Warning: Could not fetch doctor name for doctor_id {appt.get('doctor_id')}: {str(e)}")
                    appt['doctor_name'] = f"Doctor ID {appt['doctor_id']}"
        
        # Serialize dates and times
        from ..routes.appointment_routes import _serialize_appointments
        _serialize_appointments(appointments)
        
        return jsonify({"appointments": appointments}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch appointments: {str(e)}"}), 400
