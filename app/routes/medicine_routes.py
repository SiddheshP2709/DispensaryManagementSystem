from flask import Blueprint, jsonify, request
try:
    from ..db import get_db_connection, get_sharded_db_layer
    from ..auth import token_required, admin_required
    from ..logger import log_action
except ImportError:
    from db import get_db_connection, get_sharded_db_layer
    from auth import token_required, admin_required
    from logger import log_action

medicine_bp = Blueprint('medicine', __name__)


# READ all medicines with inventory info (all authenticated users)
@medicine_bp.route('/medicines', methods=['GET'])
@token_required
def get_medicines():
    sharded_db = get_sharded_db_layer()
    try:
        medicines = sharded_db.get_all_medicines()
        return jsonify({"medicines": medicines}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch medicines: {str(e)}"}), 400


# READ single medicine
@medicine_bp.route('/medicines/<int:id>', methods=['GET'])
@token_required
def get_medicine(id):
    sharded_db = get_sharded_db_layer()
    try:
        medicines = sharded_db.get_all_medicines()
        medicine = next((m for m in medicines if m['medicine_id'] == id), None)
        if not medicine:
            return jsonify({"error": "Medicine not found"}), 404
        return jsonify({"medicine": medicine}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch medicine: {str(e)}"}), 400


# CREATE medicine + inventory entry (admin only)
@medicine_bp.route('/add_medicine', methods=['POST'])
@admin_required
def add_medicine():
    data = request.get_json()
    required = ['medicine_name', 'manufacturer', 'price', 'category',
                'quantity', 'manufacturing_date', 'expiry_date']
    if not all(k in data for k in required):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        from ..sharding import get_shard_connection, get_shard_table_name
        from ..config import get_shard_settings
        
        settings = get_shard_settings()
        # Write to shard 0 (medicines are replicated)
        conn = get_shard_connection(0, settings["user"], settings["password"], settings["database"])
        cursor = conn.cursor()
        
        # Insert medicine (replicated across all shards)
        cursor.execute(f"""
            INSERT INTO {get_shard_table_name('medicine', 0)} 
            (medicine_name, manufacturer, price, category)
            VALUES (%s, %s, %s, %s)
        """, (data['medicine_name'], data['manufacturer'], int(data['price']), data['category']))
        conn.commit()
        medicine_id = cursor.lastrowid
        
        # Insert inventory
        cursor.execute(f"""
            INSERT INTO {get_shard_table_name('inventory', 0)} 
            (manufacturing_date, expiry_date, quantity, medicine_id)
            VALUES (%s, %s, %s, %s)
        """, (data['manufacturing_date'], data['expiry_date'], int(data['quantity']), medicine_id))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        log_action(request.user['username'],
                   f"CREATED MEDICINE (name: {data['medicine_name']}, qty: {data['quantity']})")
        return jsonify({"message": "Medicine added successfully", "medicine_id": medicine_id}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to add medicine: {str(e)}"}), 400


# UPDATE medicine and/or inventory (admin only)
@medicine_bp.route('/update_medicine/<int:id>', methods=['PUT'])
@admin_required
def update_medicine(id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "No data provided"}), 400

    try:
        from ..sharding import get_shard_connection, get_shard_table_name
        from ..config import get_shard_settings
        
        settings = get_shard_settings()
        conn = get_shard_connection(0, settings["user"], settings["password"], settings["database"])
        cursor = conn.cursor()
        
        # Build update query dynamically
        allowed_fields = ['medicine_name', 'manufacturer', 'price', 'category']
        update_fields = {k: v for k, v in data.items() if k in allowed_fields}
        
        if update_fields:
            set_clause = ", ".join([f"{k} = %s" for k in update_fields.keys()])
            values = list(update_fields.values())
            values.append(id)
            
            cursor.execute(f"""
                UPDATE {get_shard_table_name('medicine', 0)}
                SET {set_clause}
                WHERE medicine_id = %s
            """, tuple(values))
            conn.commit()
        
        cursor.close()
        conn.close()
        
        log_action(request.user['username'], f"UPDATED MEDICINE {id}")
        return jsonify({"message": f"Medicine {id} updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Update failed: {str(e)}"}), 400


# DELETE medicine (admin only)
@medicine_bp.route('/delete_medicine/<int:id>', methods=['DELETE'])
@admin_required
def delete_medicine(id):
    try:
        from ..sharding import get_shard_connection, get_shard_table_name
        from ..config import get_shard_settings
        
        settings = get_shard_settings()
        conn = get_shard_connection(0, settings["user"], settings["password"], settings["database"])
        cursor = conn.cursor()
        
        # Delete inventory first (foreign key constraint)
        cursor.execute(f"""
            DELETE FROM {get_shard_table_name('inventory', 0)}
            WHERE medicine_id = %s
        """, (id,))
        conn.commit()
        
        # Delete medicine
        cursor.execute(f"""
            DELETE FROM {get_shard_table_name('medicine', 0)}
            WHERE medicine_id = %s
        """, (id,))
        conn.commit()
        
        cursor.close()
        conn.close()
        
        log_action(request.user['username'], f"DELETED MEDICINE {id}")
        return jsonify({"message": f"Medicine {id} deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Deletion failed: {str(e)}"}), 400
