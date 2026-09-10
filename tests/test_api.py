import requests

BASE_URL = "http://localhost:5000"

def test_api():
    session = requests.Session()
    
    # Try as JSON first
    login_data = {"username": "patient_1", "password": "password"}
    print(f"Logging in as {login_data['username']}...")
    try:
        r = session.post(f"{BASE_URL}/login", json=login_data)
        if r.status_code != 200:
            print(f"Login (JSON) failed: {r.status_code}")
            # Try as form-data
            r = session.post(f"{BASE_URL}/login", data=login_data)
            if r.status_code != 200:
                print(f"Login (Form) failed: {r.status_code}")
                return
        print("Login successful.")
    except Exception as e:
        print(f"Error during login: {e}")
        return

    # 2. GET /doctors
    print("\nVerifying /doctors...")
    try:
        r = session.get(f"{BASE_URL}/doctors")
        if r.status_code == 200:
            doctors = r.json()
            if doctors and len(doctors) > 0:
                doc = doctors[0]
                name = doc.get('name') or doc.get('doctor_name')
                print(f"Found {len(doctors)} doctors. First doctor: {name}")
                if name:
                    print("✅ Doctor name field is present.")
                else:
                    print("❌ Doctor name field is missing in /doctors response.")
                    print(f"Full object: {doc}")
            else:
                print("No doctors found.")
        else:
            print(f"Failed to get doctors: {r.status_code}")
    except Exception as e:
        print(f"Error getting doctors: {e}")

    # 3. GET /my_appointments
    print("\nVerifying /my_appointments...")
    try:
        r = session.get(f"{BASE_URL}/my_appointments")
        if r.status_code == 200:
            appointments = r.json()
            if appointments and len(appointments) > 0:
                print(f"Found {len(appointments)} appointments.")
                appt = appointments[0]
                doc_name = appt.get('doctor_name')
                pat_name = appt.get('patient_name')
                print(f"First appointment: Doctor={doc_name}, Patient={pat_name}")
                
                if doc_name and pat_name:
                    print("✅ doctor_name and patient_name are properly populated.")
                else:
                    missing = []
                    if not doc_name: missing.append("doctor_name")
                    if not pat_name: missing.append("patient_name")
                    print(f"❌ Missing fields in appointments: {', '.join(missing)}")
                    print(f"Full object: {appt}")
            else:
                print("No appointments found for this patient.")
        else:
            print(f"Failed to get appointments: {r.status_code}")
    except Exception as e:
        print(f"Error getting appointments: {e}")

if __name__ == '__main__':
    test_api()
