"""
Sharded Database Access Layer for Flask Application.

This module provides abstractions for accessing data across shards.
"""

import mysql.connector
from mysql.connector import Error
try:
    from .sharding import (
        get_shard_id, 
        get_shard_connection, 
        get_shard_table_name,
        NUM_SHARDS
    )
except ImportError:
    from sharding import (
        get_shard_id, 
        get_shard_connection, 
        get_shard_table_name,
        NUM_SHARDS
    )

class ShardedDBLayer:
    """
    Access layer for sharded database operations.
    Handles routing of queries to appropriate shards.
    """
    
    def __init__(self, username, password, database):
        self.username = username
        self.password = password
        self.database = database
    
    def get_member_by_id(self, member_id):
        """Get member by member_id from appropriate shard."""
        shard_id = get_shard_id(member_id)
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT * FROM {get_shard_table_name('member', shard_id)} 
                WHERE member_id = %s
            """, (member_id,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result
        except Error as e:
            raise Exception(f"Error fetching member {member_id}: {str(e)}")
    
    def get_all_members(self):
        """Get all members from all shards."""
        members = []
        for shard_id in range(NUM_SHARDS):
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"""
                    SELECT * FROM {get_shard_table_name('member', shard_id)}
                """)
                shard_members = cursor.fetchall()
                members.extend(shard_members)
                cursor.close()
                conn.close()
            except Error as e:
                print(f"Warning: Error fetching members from shard {shard_id}: {str(e)}")
        
        # Sort by member_id for consistency
        return sorted(members, key=lambda x: x['member_id'])
    
    def insert_member(self, member_data):
        """Insert member into appropriate shard based on member_id."""
        member_id = member_data.get('member_id')
        if not member_id:
            raise ValueError("member_id is required")
        
        shard_id = get_shard_id(member_id)
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {get_shard_table_name('member', shard_id)} 
                (member_id, name, age, email, contact_no, image, member_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                member_data['member_id'], member_data['name'], member_data['age'],
                member_data['email'], member_data['contact_no'], 
                member_data.get('image', ''), member_data.get('member_type', '')
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return member_id
        except Error as e:
            raise Exception(f"Error inserting member: {str(e)}")
    
    def get_doctor_by_id(self, doctor_id, member_id=None):
        """Get doctor - searches appropriate shard if member_id provided."""
        if member_id:
            shard_id = get_shard_id(member_id)
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"""
                    SELECT * FROM {get_shard_table_name('doctor', shard_id)} 
                    WHERE doctor_id = %s
                """, (doctor_id,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result
            except Error as e:
                raise Exception(f"Error fetching doctor {doctor_id}: {str(e)}")
        else:
            # Search all shards if member_id not provided
            for shard_id in range(NUM_SHARDS):
                try:
                    conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(f"""
                        SELECT * FROM {get_shard_table_name('doctor', shard_id)} 
                        WHERE doctor_id = %s
                    """, (doctor_id,))
                    result = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    if result:
                        return result
                except Error as e:
                    pass
            return None
    
    def get_all_doctors(self):
        """Get all doctors from all shards with doctor names."""
        doctors = []
        for shard_id in range(NUM_SHARDS):
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"""
                    SELECT 
                        d.doctor_id, d.member_id, d.specialization, d.qualification,
                        d.consultation_fee, d.salary, d.shift,
                        m.name as doctor_name, m.email, m.contact_no
                    FROM {get_shard_table_name('doctor', shard_id)} d
                    LEFT JOIN {get_shard_table_name('member', shard_id)} m ON d.member_id = m.member_id
                """)
                shard_doctors = cursor.fetchall()
                doctors.extend(shard_doctors)
                cursor.close()
                conn.close()
            except Error as e:
                print(f"Warning: Error fetching doctors from shard {shard_id}: {str(e)}")
        
        return sorted(doctors, key=lambda x: x['doctor_id'])
    
    def get_doctor_by_member_id(self, member_id):
        """Get doctor by member_id (for cross-shard lookups)."""
        doctor_shard_id = get_shard_id(member_id)
        try:
            conn = get_shard_connection(doctor_shard_id, self.username, self.password, self.database)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT 
                    d.doctor_id, d.member_id, d.specialization, d.qualification,
                    d.consultation_fee, d.salary, d.shift,
                    m.name as doctor_name, m.email, m.contact_no
                FROM {get_shard_table_name('doctor', doctor_shard_id)} d
                LEFT JOIN {get_shard_table_name('member', doctor_shard_id)} m ON d.member_id = m.member_id
                WHERE d.member_id = %s
            """, (member_id,))
            doctor = cursor.fetchone()
            cursor.close()
            conn.close()
            return doctor
        except Exception as e:
            print(f"Error fetching doctor by member_id {member_id}: {str(e)}")
            return None
    
    def get_doctor_by_member_id(self, member_id):
        """Get doctor by member_id (for cross-shard lookups)."""
        doctor_shard_id = get_shard_id(member_id)
        try:
            conn = get_shard_connection(doctor_shard_id, self.username, self.password, self.database)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT 
                    d.doctor_id, d.member_id, d.specialization, d.qualification,
                    d.consultation_fee, d.salary, d.shift,
                    m.name as doctor_name, m.email, m.contact_no
                FROM {get_shard_table_name('doctor', doctor_shard_id)} d
                LEFT JOIN {get_shard_table_name('member', doctor_shard_id)} m ON d.member_id = m.member_id
                WHERE d.member_id = %s
            """, (member_id,))
            doctor = cursor.fetchone()
            cursor.close()
            conn.close()
            return doctor
        except Exception as e:
            print(f"Error fetching doctor by member_id {member_id}: {str(e)}")
            return None
    
    def get_patient_by_member_id(self, member_id):
        """Get patient by member_id (for cross-shard lookups)."""
        patient_shard_id = get_shard_id(member_id)
        try:
            conn = get_shard_connection(patient_shard_id, self.username, self.password, self.database)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT 
                    p.patient_id, p.member_id, p.disease_history, p.allergies,
                    m.name as patient_name, m.email, m.contact_no
                FROM {get_shard_table_name('patient', patient_shard_id)} p
                LEFT JOIN {get_shard_table_name('member', patient_shard_id)} m ON p.member_id = m.member_id
                WHERE p.member_id = %s
            """, (member_id,))
            patient = cursor.fetchone()
            cursor.close()
            conn.close()
            return patient
        except Exception as e:
            print(f"Error fetching patient by member_id {member_id}: {str(e)}")
            return None
    
    def get_all_medicines(self):
        """Get all medicines with quantity from LOCAL DB + Shards."""
        medicines = []
        
        # Get from LOCAL DB (with inventory join)
        try:
            import mysql.connector
            from .config import get_db_settings
            
            db_settings = get_db_settings()
            local_conn = mysql.connector.connect(
                host=db_settings['host'],
                user=db_settings['user'],
                password=db_settings['password'],
                database=db_settings['database']
            )
            local_cursor = local_conn.cursor(dictionary=True)
            local_cursor.execute("""
                SELECT 
                    m.medicine_id, m.medicine_name, m.manufacturer, m.price, m.category,
                    COALESCE(SUM(i.quantity), 0) as quantity,
                    MAX(i.manufacturing_date) as manufacturing_date, 
                    MAX(i.expiry_date) as expiry_date
                FROM medicine m
                LEFT JOIN inventory i ON m.medicine_id = i.medicine_id
                GROUP BY m.medicine_id
            """)
            local_medicines = local_cursor.fetchall()
            medicines.extend(local_medicines)
            print(f"[DEBUG] Fetched {len(local_medicines)} medicines from LOCAL DB with inventory")
            local_cursor.close()
            local_conn.close()
        except Exception as e:
            print(f"Warning: Could not fetch medicines from LOCAL DB: {str(e)}")
        
        # Also get from Shard 0 (replicated)
        for shard_id in range(NUM_SHARDS):
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                table_name = get_shard_table_name('medicine', shard_id)
                
                # Only query from shard 0 (replicated)
                if shard_id == 0:
                    cursor.execute(f"""
                        SELECT 
                            m.medicine_id, m.medicine_name, m.manufacturer, m.price, m.category,
                            COALESCE(SUM(i.quantity), 0) as quantity,
                            MAX(i.manufacturing_date) as manufacturing_date, 
                            MAX(i.expiry_date) as expiry_date
                        FROM {table_name} m
                        LEFT JOIN {get_shard_table_name('inventory', shard_id)} i ON m.medicine_id = i.medicine_id
                        GROUP BY m.medicine_id
                    """)
                    shard_medicines = cursor.fetchall()
                    print(f"[DEBUG] Fetched {len(shard_medicines)} medicines from Shard 0 with inventory")
                    medicines.extend(shard_medicines)
                
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Warning: Could not fetch medicines from shard {shard_id}: {str(e)}")
        
        # Remove duplicates and sort
        seen = set()
        unique_medicines = []
        for med in medicines:
            med_id = med.get('medicine_id')
            if med_id not in seen:
                seen.add(med_id)
                unique_medicines.append(med)
        
        print(f"[DEBUG] Total unique medicines with quantity returned: {len(unique_medicines)}")
        return sorted(unique_medicines, key=lambda x: x['medicine_id'])
    
    def insert_doctor(self, doctor_data):
        """Insert doctor - routes to shard of member_id."""
        member_id = doctor_data['member_id']
        shard_id = get_shard_id(member_id)
        
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {get_shard_table_name('doctor', shard_id)} 
                (doctor_id, specialization, qualification, consultation_fee, salary, shift, member_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                doctor_data['doctor_id'], doctor_data['specialization'], doctor_data['qualification'],
                doctor_data['consultation_fee'], doctor_data['salary'], doctor_data['shift'], member_id
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return doctor_data['doctor_id']
        except Error as e:
            raise Exception(f"Error inserting doctor: {str(e)}")
    
    def get_patient_by_id(self, patient_id, member_id=None):
        """Get patient - routes to appropriate shard."""
        if member_id:
            shard_id = get_shard_id(member_id)
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"""
                    SELECT * FROM {get_shard_table_name('patient', shard_id)} 
                    WHERE patient_id = %s
                """, (patient_id,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result
            except Error as e:
                raise Exception(f"Error fetching patient {patient_id}: {str(e)}")
        else:
            # Search all shards
            for shard_id in range(NUM_SHARDS):
                try:
                    conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(f"""
                        SELECT * FROM {get_shard_table_name('patient', shard_id)} 
                        WHERE patient_id = %s
                    """, (patient_id,))
                    result = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    if result:
                        return result
                except Error as e:
                    pass
            return None
    
    def get_all_patients(self):
        """Get all patients from all shards."""
        patients = []
        for shard_id in range(NUM_SHARDS):
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"""
                    SELECT * FROM {get_shard_table_name('patient', shard_id)}
                """)
                shard_patients = cursor.fetchall()
                patients.extend(shard_patients)
                cursor.close()
                conn.close()
            except Error as e:
                print(f"Warning: Error fetching patients from shard {shard_id}: {str(e)}")
        
        return sorted(patients, key=lambda x: x['patient_id'])
    
    def insert_patient(self, patient_data):
        """Insert patient - routes to shard of member_id."""
        member_id = patient_data['member_id']
        shard_id = get_shard_id(member_id)
        
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {get_shard_table_name('patient', shard_id)} 
                (patient_id, blood_group, gender, address, member_id)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                patient_data['patient_id'], patient_data['blood_group'], 
                patient_data['gender'], patient_data['address'], member_id
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return patient_data['patient_id']
        except Error as e:
            raise Exception(f"Error inserting patient: {str(e)}")
    
    def get_appointment_by_id(self, appointment_id, patient_member_id=None):
        """Get appointment - routes based on patient's member_id."""
        if patient_member_id:
            shard_id = get_shard_id(patient_member_id)
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"""
                    SELECT * FROM {get_shard_table_name('appointment', shard_id)} 
                    WHERE appointment_id = %s
                """, (appointment_id,))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                return result
            except Error as e:
                raise Exception(f"Error fetching appointment {appointment_id}: {str(e)}")
        else:
            # Search all shards
            for shard_id in range(NUM_SHARDS):
                try:
                    conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(f"""
                        SELECT * FROM {get_shard_table_name('appointment', shard_id)} 
                        WHERE appointment_id = %s
                    """, (appointment_id,))
                    result = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    if result:
                        return result
                except Error as e:
                    pass
            return None
    
    def get_appointments_by_patient(self, patient_id, patient_member_id):
        """Get all appointments for a patient."""
        shard_id = get_shard_id(patient_member_id)
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT * FROM {get_shard_table_name('appointment', shard_id)} 
                WHERE patient_id = %s
            """, (patient_id,))
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Error as e:
            raise Exception(f"Error fetching appointments for patient {patient_id}: {str(e)}")
    
    def get_all_appointments(self):
        """Get all appointments from all shards."""
        appointments = []
        for shard_id in range(NUM_SHARDS):
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(f"""
                    SELECT * FROM {get_shard_table_name('appointment', shard_id)}
                """)
                shard_appts = cursor.fetchall()
                appointments.extend(shard_appts)
                cursor.close()
                conn.close()
            except Error as e:
                print(f"Warning: Error fetching appointments from shard {shard_id}: {str(e)}")
        
        return sorted(appointments, key=lambda x: x['appointment_id'])
    
    def insert_appointment(self, appointment_data):
        """Insert appointment - routes based on patient's member_id."""
        patient_member_id = appointment_data['patient_member_id']
        shard_id = get_shard_id(patient_member_id)
        
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {get_shard_table_name('appointment', shard_id)} 
                (appointment_id, appointment_date, appointment_time, doctor_id, patient_id, slot_id, patient_member_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                appointment_data['appointment_id'], appointment_data['appointment_date'],
                appointment_data['appointment_time'], appointment_data['doctor_id'],
                appointment_data['patient_id'], appointment_data['slot_id'], patient_member_id
            ))
            conn.commit()
            cursor.close()
            conn.close()
            return appointment_data['appointment_id']
        except Error as e:
            raise Exception(f"Error inserting appointment: {str(e)}")
    
    def get_doctors_by_shard(self, shard_id):
        """Get all doctors from a specific shard with member names."""
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT d.doctor_id, m.name, d.specialization, d.consultation_fee, d.shift, d.member_id
                FROM {get_shard_table_name('doctor', shard_id)} d
                JOIN {get_shard_table_name('member', shard_id)} m ON d.member_id = m.member_id
                ORDER BY m.name
            """)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Error as e:
            print(f"Warning: Error fetching doctors from shard {shard_id}: {str(e)}")
            return []
    
    def get_appointments_by_doctor_shard(self, doctor_id, shard_id):
        """Get appointments for doctor from specific shard."""
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(f"""
                SELECT * FROM {get_shard_table_name('appointment', shard_id)} 
                WHERE doctor_id = %s
            """, (doctor_id,))
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Error as e:
            print(f"Warning: Error fetching appointments from shard {shard_id}: {str(e)}")
            return []
    
    def check_appointment_conflict(self, doctor_id, appointment_date, slot_id, exclude_id=None):
        """Check for appointment conflicts across all shards."""
        for shard_id in range(NUM_SHARDS):
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                query = f"""
                    SELECT appointment_id FROM {get_shard_table_name('appointment', shard_id)}
                    WHERE doctor_id = %s AND appointment_date = %s AND slot_id = %s
                """
                params = [doctor_id, appointment_date, slot_id]
                if exclude_id is not None:
                    query += " AND appointment_id <> %s"
                    params.append(exclude_id)
                cursor.execute(query, tuple(params))
                result = cursor.fetchone()
                cursor.close()
                conn.close()
                if result:
                    return True
            except Error as e:
                print(f"Warning: Error checking conflict in shard {shard_id}: {str(e)}")
        return False
    
    def update_member(self, member_id, update_data):
        """Update member in appropriate shard."""
        shard_id = get_shard_id(member_id)
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor()
            
            # Build dynamic update query
            set_clause = ", ".join([f"{k} = %s" for k in update_data.keys()])
            values = list(update_data.values())
            values.append(member_id)
            
            cursor.execute(f"""
                UPDATE {get_shard_table_name('member', shard_id)} 
                SET {set_clause}
                WHERE member_id = %s
            """, tuple(values))
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Error as e:
            raise Exception(f"Error updating member {member_id}: {str(e)}")
    
    def execute_on_shard(self, member_id, query, params=None):
        """Execute custom query on appropriate shard for member."""
        shard_id = get_shard_id(member_id)
        try:
            conn = get_shard_connection(shard_id, self.username, self.password, self.database)
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            return results
        except Error as e:
            raise Exception(f"Error executing query on shard {shard_id}: {str(e)}")
    
    def execute_on_all_shards(self, query, params=None):
        """Execute query on all shards and aggregate results."""
        results = []
        for shard_id in range(NUM_SHARDS):
            try:
                conn = get_shard_connection(shard_id, self.username, self.password, self.database)
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, params or ())
                shard_results = cursor.fetchall()
                results.extend(shard_results)
                cursor.close()
                conn.close()
            except Error as e:
                print(f"Warning: Error executing query on shard {shard_id}: {str(e)}")
        return results

# Global instance
_sharded_db = None

def get_sharded_db(username, password, database):
    """Get or create global sharded database access layer."""
    global _sharded_db
    if _sharded_db is None:
        _sharded_db = ShardedDBLayer(username, password, database)
    return _sharded_db
