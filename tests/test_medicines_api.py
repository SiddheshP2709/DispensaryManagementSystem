import json, requests, time

BASE_URL = "http://localhost:5000"

def test_medicines_api():
    username = "patient1"
    password = "Patient1pass"
    
    session = requests.Session()
    print(f"Logging in as {username}...")
    r = session.post(f"{BASE_URL}/login", json={"username": username, "password": password})
    
    if r.status_code == 200:
        print("✓ Login successful")
        
        print("\nFetching medicines...")
        r_meds = session.get(f"{BASE_URL}/medicines")
        if r_meds.status_code == 200:
            data = r_meds.json()
            meds = data.get('medicines', [])
            print(f"✓ Got {len(meds)} medicines")
            if meds:
                med = meds[0]
                print(f"\nFirst medicine:")
                print(f"  ID: {med.get('medicine_id')}")
                print(f"  Name: {med.get('medicine_name')}")
                print(f"  Quantity: {med.get('quantity')}")
                print(f"  Price: {med.get('price')}")
                print(f"  Expiry: {med.get('expiry_date')}")
        else:
            print(f"✗ Failed to fetch medicines: {r_meds.status_code}")
            print(f"  Response: {r_meds.text}")
    else:
        print(f"✗ Login failed: {r.status_code}")

if __name__ == "__main__":
    test_medicines_api()
