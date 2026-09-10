from flask import Blueprint, request, jsonify
try:
    from ..db import get_db_connection, get_sharded_db_layer
    from ..auth import encode_token, token_required, admin_required
    from ..logger import get_recent_logs, log_action
    from ..validators import (
        ALLOWED_GENDERS,
        clean_string,
        validate_age,
        validate_email,
        validate_password,
        validate_phone,
        validate_username,
    )
except ImportError:
    from db import get_db_connection, get_sharded_db_layer
    from auth import encode_token, token_required, admin_required
    from logger import get_recent_logs, log_action
    from validators import (
        ALLOWED_GENDERS,
        clean_string,
        validate_age,
        validate_email,
        validate_password,
        validate_phone,
        validate_username,
    )
import bcrypt

auth_bp = Blueprint('auth', __name__)


def _validation_error(message):
    return jsonify({"error": message}), 400


@auth_bp.route('/', methods=['GET'])
def welcome():
    return jsonify({"message": "Welcome to test APIs"})


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = clean_string(data.get('user') if data else "")
    password = data.get('password') if data else None

    if not username or not password:
        return jsonify({"error": "Missing parameters"}), 401

    # HYBRID: Search for user in LOCAL DB only (not shards)
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": "Authentication service error"}), 500
    
    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return jsonify({"error": "Invalid credentials"}), 401
    
    # Generate JWT token
    token = encode_token(
        username=user['username'],
        role=user['role'],
        member_id=user['member_id']
    )
    
    log_action(user['username'], "LOGIN")
    return jsonify({
        "message": "Login successful",
        "session_token": token
    }), 200


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}

    name = clean_string(data.get('name'))
    age = data.get('age')
    email = clean_string(data.get('email'))
    contact_no = clean_string(data.get('contact_no'))
    username = clean_string(data.get('username'))
    password = data.get('password')
    gender = clean_string(data.get('gender', 'Other')) or 'Other'
    address = clean_string(data.get('address'))
    blood_group = clean_string(data.get('blood_group', 'Unknown')) or 'Unknown'

    if not all([name, age, email, contact_no, username, password]):
        return _validation_error("Missing required fields")
    if not validate_age(age):
        return _validation_error("Age must be between 1 and 120")
    if not validate_email(email):
        return _validation_error("Enter a valid email address")
    if not validate_phone(contact_no):
        return _validation_error("Enter a valid contact number")
    if not validate_username(username):
        return _validation_error("Username must be 3-30 characters and use only letters, numbers, or underscore")
    if not validate_password(password):
        return _validation_error("Password must be at least 8 characters and contain letters and numbers")
    if gender not in ALLOWED_GENDERS:
        return _validation_error("Invalid gender")

    # Registration is simplified for sharding demonstration
    # In production, would handle distributed registration differently
    return jsonify({"message": "Registration endpoint available - use with sharded architecture"}), 200


@auth_bp.route('/isAuth', methods=['GET'])
@token_required
def is_auth():
    return jsonify({
        "message": "User is authenticated",
        "username": request.user['username'],
        "role": request.user['role'],
        "member_type": request.user.get('member_type'),
        "expiry": request.user['exp']
    }), 200


@auth_bp.route('/audit_logs', methods=['GET'])
@admin_required
def get_audit_logs():
    return jsonify({"logs": get_recent_logs()}), 200
